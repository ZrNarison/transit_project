from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponseForbidden
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from clients.models import Client
from audit.utils import enregistrer_action
from avanceclient.models import (
    AvanceClient,
    UtilisationAvanceClient,
    RemboursementAvanceClient,
)
from avances.models import Avance
from depot.models import Distribution
from logs.utils import enregistrer_log
from retours.models import Retour
from decimal import Decimal, InvalidOperation
from .forms import ProduitForm
from .models import HistoriqueProduit, PaiementProduit, Produit
from django.core.paginator import Paginator
from users.decorators import session_login_required

@transaction.atomic
def valider_paiement(request):

    from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

    if request.method != "POST":
        return redirect("produit:p_produit_liste")

    # --------------------------------------------------
    # 1. AUTORISATION
    # --------------------------------------------------
    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "SuperviseurMica":
        messages.error(
            request,
            "Vous n'êtes pas autorisé à valider les paiements Mica.",
        )
        return redirect("produit:p_produit_liste")

    # --------------------------------------------------
    # 2. VALIDATION DU MODE ET DES PRODUITS SÉLECTIONNÉS
    # --------------------------------------------------
    remboursement = request.POST.get("remboursement", "AUCUN")

    if remboursement not in ("AUCUN", "PARTIEL", "TOTAL"):
        messages.error(request, "Mode d'opération invalide.")
        return redirect("produit:p_produit_liste")

    ids_bruts = request.POST.getlist("produits")

    try:
        ids = []

        for valeur in ids_bruts:
            identifiant = int(valeur)

            if identifiant <= 0:
                raise ValueError

            ids.append(identifiant)

    except (ValueError, TypeError):
        messages.error(request, "Sélection de produits invalide.")
        return redirect("produit:p_produit_liste")

    # Éliminer les doublons sans modifier l'ordre.
    ids = list(dict.fromkeys(ids))

    # Les trois modes exigent une sélection.
    if not ids:
        messages.warning(
            request,
            "Sélectionnez au moins un produit pour cette opération.",
        )
        return redirect("produit:p_produit_liste")

    zero = Decimal("0")
    montant_retour_demande = zero

    if remboursement == "PARTIEL":
        try:
            montant_retour_demande = Decimal(
                request.POST.get("montant_retour", "").strip()
            )

            if (
                not montant_retour_demande.is_finite()
                or montant_retour_demande <= zero
                or montant_retour_demande
                != montant_retour_demande.to_integral_value()
            ):
                raise InvalidOperation

        except (InvalidOperation, ValueError, TypeError):
            messages.error(
                request,
                "Le remboursement partiel doit être un montant entier "
                "strictement supérieur à zéro.",
            )
            return redirect("produit:p_produit_liste")

    # --------------------------------------------------
    # 3. VERROUILLER LES PRODUITS ET VÉRIFIER LA SÉLECTION
    # --------------------------------------------------
    produits = list(
        Produit.objects.select_for_update()
        .filter(id__in=ids, paye=False)
        .select_related("client", "vehicule")
        .order_by("id")
    )

    if len(produits) != len(ids):
        messages.warning(
            request,
            "Certains produits sélectionnés sont inexistants, déjà payés "
            "ou indisponibles. Actualisez la liste et réessayez.",
        )
        return redirect("produit:p_produit_liste")

    client_ids = {produit.client_id for produit in produits}

    # Un remboursement doit concerner un seul client.
    if remboursement != "AUCUN" and (
        len(client_ids) != 1 or None in client_ids
    ):
        messages.warning(
            request,
            "Pour un remboursement, sélectionnez uniquement des produits "
            "appartenant à un seul client.",
        )
        return redirect("produit:p_produit_liste")

    # --------------------------------------------------
    # 4. CHARGER ET VERROUILLER LES AVANCES SÉLECTIONNÉES
    # --------------------------------------------------
    avances = list(
        AvanceClient.objects.select_for_update()
        .filter(client_id__in=client_ids)
        .order_by("date", "id")
    )

    avances_par_client = {}

    for avance in avances:
        avances_par_client.setdefault(
            avance.client_id, []
        ).append(avance)

    # --------------------------------------------------
    # 5. TRAITEMENT INDÉPENDANT DES REMBOURSEMENTS
    # --------------------------------------------------
    if remboursement in ("PARTIEL", "TOTAL"):
        client_id = next(iter(client_ids))

        avances_disponibles = [
            (avance, avance.reste)
            for avance in avances_par_client.get(client_id, [])
            if avance.reste > zero
        ]

        disponible_total = sum(
            (solde for _, solde in avances_disponibles),
            zero,
        )

        if disponible_total <= zero:
            messages.warning(
                request,
                "Ce client ne possède aucune avance disponible à rembourser. Aucun remboursement n'a été enregistré.",
            )
            return redirect("produit:p_produit_liste")

        if remboursement == "TOTAL":
            montant_retour_demande = disponible_total

        if montant_retour_demande > disponible_total:
            messages.warning(
                request,
                f"Remboursement refusé : {montant_retour_demande:,.0f} Ar "
                f"demandés, mais seulement {disponible_total:,.0f} Ar "
                "sont disponibles.",
            )
            return redirect("produit:p_produit_liste")

        # Répartir le remboursement dans l'ordre chronologique.
        allocations = []
        reste_a_rembourser = montant_retour_demande

        for avance, solde in avances_disponibles:
            if reste_a_rembourser <= zero:
                break

            montant_allocation = min(solde, reste_a_rembourser)

            if montant_allocation > zero:
                allocations.append((avance, montant_allocation))
                reste_a_rembourser -= montant_allocation

        if reste_a_rembourser != zero or not allocations:
            messages.error(
                request,
                "Le remboursement n'a pas pu être préparé. Aucune écriture n'a été enregistrée.",
            )
            return redirect("produit:p_produit_liste")

        # Enregistrer le remboursement et marquer les produits sélectionnés
        # comme payés après la validation PARTIEL ou TOTAL.
        try:
            with transaction.atomic():
                for avance, montant_allocation in allocations:
                    avance.refresh_from_db()

                    solde_reel = avance.reste

                    if (
                        montant_allocation <= zero
                        or montant_allocation > solde_reel
                    ):
                        raise InvalidOperation(
                            "Le solde réel de l'avance ne permet plus ce remboursement."
                        )

                    
                    # Conserver l'écriture de retour existante.
                    Retour.objects.create(
                        client=avance.client,
                        montant=montant_allocation,
                        motif=(
                            "Remboursement partiel d'avance client Mica"
                            if remboursement == "PARTIEL"
                            else "Remboursement total d'avance client Mica"
                        ),
                        enregistrer_par_id=user_id,
                    )

                    # Enregistrer l'événement d'historique affiché dans avanceclient/list.html.
                    RemboursementAvanceClient.objects.create(
                        avance=avance,
                        type_remboursement=remboursement,
                        montant=montant_allocation,
                    )

                    # Mettre à jour le solde remboursé une seule fois.
                    avance.montant_retour += montant_allocation
                    avance.save(update_fields=["montant_retour"])


                    enregistrer_log(
                        f"Remboursement {remboursement} : avance "
                        f"{avance.id}, client {client_id}, "
                        f"montant {montant_allocation} Ar.",
                        "INFO",
                        "Retour",
                    )

                # Changement demandé : les produits sélectionnés passent
                # à l'état « Payé » après validation PARTIEL ou TOTAL.
                date_validation = timezone.now()
                for produit in produits:
                    # Déduction du remboursement sur le montant net du produit.
                    produit.montant_deduction_avance = montant_retour_demande

                    produit.paye = True
                    produit.date_paiement = date_validation

                    produit.save(
                        update_fields=[
                            "montant_deduction_avance",
                            "paye",
                            "date_paiement",
                        ]
                    )

                    enregistrer_action(
                        request,
                        "UPDATE",
                        "Produit",
                        produit.id,
                        ancienne={"paye": False},
                        nouvelle={
                            "paye": True,
                            "date_paiement": str(date_validation),
                        },
                        description=(
                            f"Statut produit passé à Payé après validation "
                            f"{remboursement} du remboursement Mica"
                        ),
                    )

                    enregistrer_log(
                        f"Produit {produit.id} marqué Payé après validation "
                        f"{remboursement}.",
                        "INFO",
                        "Produit",
                    )

        except InvalidOperation:
            messages.error(
                request,
                "Remboursement annulé : le solde réel d'une avance ne permet plus l'opération. Aucune écriture de cette tentative n'a été conservée.",
            )
            return redirect("produit:p_produit_liste")

        client = produits[0].client

        messages.success(
            request,
            f"Remboursement {remboursement.lower()} enregistré pour "
            f"{client.nom} : {montant_retour_demande:,.0f} Ar. "
            "Les produits sélectionnés sont maintenant marqués Payé.",
        )
        return redirect("produit:p_produit_liste")

    # --------------------------------------------------
    # 6. PAIEMENT NORMAL : CHARGER LES DISTRIBUTIONS
    # --------------------------------------------------
    distributions = list(
        Distribution.objects.select_for_update()
        .select_related("depot")
        .order_by("depot__date", "id")
    )

    soldes_avances = {
        avance.id: avance.reste
        for avance in avances
    }

    soldes_distributions = {
        distribution.id: distribution.solde
        for distribution in distributions
    }

    plans_paiement = []
    produits_non_payes = []

    # --------------------------------------------------
    # 7. SIMULER LE FINANCEMENT DES PRODUITS
    # --------------------------------------------------
    for produit in produits:
        try:
            montant_brut = Decimal(str(produit.montant_net))

            if not montant_brut.is_finite() or montant_brut < zero:
                raise InvalidOperation

            montant_total = montant_brut.quantize(
                Decimal("1"),
                rounding=ROUND_HALF_UP,
            )

        except (InvalidOperation, ValueError, TypeError):
            messages.error(
                request,
                f"Montant net invalide pour le produit {produit.id}. Aucun paiement n'a été enregistré.",
            )
            return redirect("produit:p_produit_liste")

        reste = montant_total
        montant_avance = zero
        montant_distribution = zero

        avances_temporaires = soldes_avances.copy()
        distributions_temporaires = soldes_distributions.copy()

        utilisations_avances = []
        paiements_distributions = []

        # 7A. NE PAS UTILISER LES AVANCES DU CLIENT
        # Les avances du client restent inchangées.
        # Le paiement sera financé uniquement par les distributions.
        utilisations_avances = []
        montant_avance = zero

        # 7B. DISTRIBUTIONS, PAR ORDRE CHRONOLOGIQUE
        if reste > zero:
            for distribution in distributions:
                disponible = distributions_temporaires[distribution.id]

                if disponible <= zero:
                    continue

                paiement = min(disponible, reste)

                if paiement > zero:
                    paiements_distributions.append(
                        (distribution, paiement)
                    )
                    distributions_temporaires[distribution.id] -= paiement
                    montant_distribution += paiement
                    reste -= paiement

                if reste <= zero:
                    break

        # 7C. FINANCEMENT INSUFFISANT : NE PAS CONSOMMER LES SOLDES
        if reste > zero:
            produits_non_payes.append((produit.id, reste))
            continue

        # Confirmer la simulation seulement si le produit
        # est entièrement finançable.
        soldes_avances = avances_temporaires
        soldes_distributions = distributions_temporaires

        
        plans_paiement.append(
            {
                "produit": produit,
                "montant_total": montant_total,
                "montant_avance": montant_avance,
                "montant_distribution": montant_distribution,
                "utilisations_avances": utilisations_avances,
                "paiements_distributions": paiements_distributions,
            }
        )

    # --------------------------------------------------
    # 8. ENREGISTRER LES PAIEMENTS ATOMIQUEMENT
    # --------------------------------------------------
    try:
        with transaction.atomic():
            for plan in plans_paiement:
                produit = plan["produit"]

                ancienne = {
                    "paye": produit.paye,
                    "montant_net": str(plan["montant_total"]),
                }

                # Enregistrer les prélèvements sur les avances.
                for avance, utilisation in plan["utilisations_avances"]:
                    avance.refresh_from_db()

                    if utilisation > avance.reste:
                        raise InvalidOperation(
                            "Le solde réel d'une avance a changé."
                        )

                    UtilisationAvanceClient.objects.create(
                        avance=avance,
                        produit=produit,
                        montant=utilisation,
                    )

                    avance.montant_utilise += utilisation
                    avance.save(update_fields=["montant_utilise"])

                # Enregistrer les paiements financés par les distributions.
                for distribution, paiement in plan[
                    "paiements_distributions"
                ]:
                    distribution.refresh_from_db()

                    if paiement > distribution.solde:
                        raise InvalidOperation(
                            "Le solde réel d'une distribution a changé."
                        )

                    PaiementProduit.objects.create(
                        distribution=distribution,
                        produit=produit,
                        montant=paiement,
                    )

                produit.paye = True
                produit.date_paiement = timezone.now()
                produit.save(update_fields=["paye", "date_paiement"])

                enregistrer_action(
                    request,
                    "UPDATE",
                    "Produit",
                    produit.id,
                    ancienne=ancienne,
                    nouvelle={
                        "paye": True,
                        "montant_net": str(plan["montant_total"]),
                        "avance": str(plan["montant_avance"]),
                        "distribution": str(plan["montant_distribution"]),
                        "date_paiement": str(produit.date_paiement),
                    },
                    description="Validation paiement produit",
                )

                enregistrer_log(
                    f"Produit {produit.id} payé",
                    "INFO",
                    "Produit",
                )

    except InvalidOperation:
        messages.warning(
            request,
            "Validation annulée : un solde réel ne permet plus l'opération. Aucune écriture de cette tentative n'a été conservée. Actualisez la liste puis réessayez.",
        )
        return redirect("produit:p_produit_liste")

    # --------------------------------------------------
    # 9. PRODUITS INSUFFISAMMENT FINANCÉS
    # --------------------------------------------------
    for produit_id, reste in produits_non_payes:
        messages.warning(
            request,
            f"Produit {produit_id} non payé : reste {reste:,.0f} Ar.",
        )

        enregistrer_log(
            f"Produit {produit_id} incomplet, reste {reste} Ar",
            "WARNING",
            "Produit",
        )

    # --------------------------------------------------
    # 10. RÉSULTAT
    # --------------------------------------------------
    if produits_non_payes:
        if plans_paiement:
            messages.warning(
                request,
                "Validation partielle : certains produits restent impayés. Vérifiez les montants restants.",
            )
        else:
            messages.warning(
                request,
                "Aucun produit n'a été entièrement payé. Vérifiez les montants restants.",
            )

    elif plans_paiement:
        messages.success(
            request,
            "Validation paiement terminée avec succès.",
        )

    else:
        messages.warning(
            request,
            "Aucun paiement n'a été enregistré.",
        )

    return redirect("produit:p_produit_liste")


# ============================================================
# REMBOURSEMENT INDEPENDANT DES AVANCES CLIENT MICA
# ============================================================
@transaction.atomic
def rembourser_avance(request):

    from decimal import InvalidOperation

    if request.method not in ("GET", "POST"):
        return redirect("produit:p_produit_liste")

    user_id = request.session.get("user_id")
    role = request.session.get("role")

    if not user_id or role != "SuperviseurMica":
        messages.error(
            request,
            "Vous n'êtes pas autorisé à rembourser les avances Mica.",
        )
        return redirect("produit:p_produit_liste")

    clients = Client.objects.order_by("nom", "prenom", "id")

    if request.method == "GET":
        return render(
            request,
            "produit/remboursement_avance.html",
            {"clients": clients},
        )

    # --------------------------------------------------------
    # 1. VALIDER LE CLIENT ET LE MODE DE REMBOURSEMENT
    # --------------------------------------------------------
    try:
        client_id = int(request.POST.get("client_id", ""))
        if client_id <= 0:
            raise ValueError
    except (ValueError, TypeError):
        messages.error(request, "Veuillez sélectionner un client valide.")
        return redirect("produit:rembourser_avance")

    client = get_object_or_404(Client, pk=client_id)
    mode = request.POST.get("remboursement", "")

    if mode not in ("PARTIEL", "TOTAL"):
        messages.error(request, "Mode de remboursement invalide.")
        return redirect("produit:rembourser_avance")

    zero = Decimal("0")
    montant_demande = zero

    if mode == "PARTIEL":
        try:
            montant_demande = Decimal(
                request.POST.get("montant_retour", "").strip()
            )

            if (
                not montant_demande.is_finite()
                or montant_demande <= zero
                or montant_demande
                != montant_demande.to_integral_value()
            ):
                raise InvalidOperation

        except (InvalidOperation, ValueError, TypeError):
            messages.error(
                request,
                "Le remboursement partiel doit être un montant entier "
                "strictement supérieur à zéro.",
            )
            return redirect("produit:rembourser_avance")

    # --------------------------------------------------------
    # 2. VERROUILLER LES AVANCES DU CLIENT
    # --------------------------------------------------------
    avances = list(
        AvanceClient.objects.select_for_update()
        .filter(client_id=client.id)
        .order_by("date", "id")
    )

    avances_disponibles = [
        (avance, avance.reste)
        for avance in avances
        if avance.reste > zero
    ]

    disponible_total = sum(
        (solde for _, solde in avances_disponibles),
        zero,
    )

    if disponible_total <= zero:
        messages.warning(
            request,
            f"Le client {client.nom} ne possède aucune avance disponible "
            "à rembourser.",
        )
        return redirect("produit:rembourser_avance")

    if mode == "TOTAL":
        montant_demande = disponible_total

    if montant_demande > disponible_total:
        messages.warning(
            request,
            f"Remboursement refusé : le montant demandé "
            f"({montant_demande:,.0f} Ar) dépasse le solde disponible "
            f"({disponible_total:,.0f} Ar).",
        )
        return redirect("produit:rembourser_avance")

    # --------------------------------------------------------
    # 3. REPARTIR LE REMBOURSEMENT CHRONOLOGIQUEMENT
    # --------------------------------------------------------
    allocations = []
    reste_a_rembourser = montant_demande

    for avance, solde in avances_disponibles:
        if reste_a_rembourser <= zero:
            break

        montant_allocation = min(solde, reste_a_rembourser)

        if montant_allocation > zero:
            allocations.append((avance, montant_allocation))
            reste_a_rembourser -= montant_allocation

    if reste_a_rembourser != zero or not allocations:
        messages.error(
            request,
            "Le remboursement n'a pas pu être préparé. "
            "Aucune écriture n'a été enregistrée.",
        )
        return redirect("produit:rembourser_avance")

    # --------------------------------------------------------
    # 4. ENREGISTRER LES RETOURS ET METTRE A JOUR LES AVANCES
    # --------------------------------------------------------
    try:
        for avance, montant_allocation in allocations:
            # Vérification supplémentaire avant chaque écriture.
            avance.refresh_from_db()

            if (
                montant_allocation <= zero
                or montant_allocation > avance.reste
            ):
                raise InvalidOperation(
                    "Le solde disponible de l'avance a changé."
                )

            
            Retour.objects.create(
                client=client,
                montant=montant_allocation,
                motif="Remboursement indépendant d'avance client Mica",
                enregistrer_par_id=user_id,
            )

            RemboursementAvanceClient.objects.create(
                avance=avance,
                type_remboursement=mode,
                montant=montant_allocation,
            )

            avance.montant_retour += montant_allocation
            avance.save(update_fields=["montant_retour"])


        enregistrer_log(
            f"Remboursement indépendant d'avance Mica : client "
            f"{client.nom} (ID {client.id}), montant "
            f"{montant_demande} Ar, mode {mode}.",
            "INFO",
            "Retour",
        )

    except InvalidOperation:
        # L'exception annule toutes les écritures de cette transaction.
        messages.error(
            request,
            "Le remboursement a été annulé car le solde réel "
            "ne permet plus cette opération.",
        )
        return redirect("produit:rembourser_avance")

    messages.success(
        request,
        f"Remboursement de {montant_demande:,.0f} Ar enregistré "
        f"pour {client.nom}. "
        f"Solde d'avance restant : "
        f"{disponible_total - montant_demande:,.0f} Ar.",
    )

    return redirect("produit:p_produit_liste")

# =========================
# LISTE PRODUITS
# =========================
@session_login_required
def produit_list(request):
    queryset = Produit.objects.select_related(
        "client",
        "vehicule",
    ).order_by("-created_at")

    client = request.GET.get("client", "").strip()
    source = request.GET.get("source", "").strip()
    vehicule = request.GET.get("vehicule", "").strip()

    if client:
        queryset = queryset.filter(
            client__nom__icontains=client,
        )

    if source:
        queryset = queryset.filter(
            source__icontains=source,
        )

    if vehicule:
        queryset = queryset.filter(
            vehicule__num_vehicule__icontains=vehicule,
        )

    # Pagination : 20 produits par page.
    paginator = Paginator(queryset, 20)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Clients disponibles pour les remboursements depuis le formulaire
    # de validation de paiement, même si aucun produit n'est sélectionné.
    clients_remboursement = Client.objects.order_by(
        "nom",
        "prenom",
        "id",
    )

    return render(
        request,
        "produit/list.html",
        {
            "produits": page_obj,
            "page_obj": page_obj,
            "client": client,
            "source": source,
            "vehicule": vehicule,
            "clients_remboursement": clients_remboursement,
        },
    )


# =========================
# AJOUT
# =========================
@session_login_required
def produit_add(request):
    form = ProduitForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        produit = form.save()

        # Audit et historique
        enregistrer_action(
            request,
            "CREATE",
            "Produit",
            produit.id,
            nouvelle={
                "montant": str(produit.montant),
                "client": str(produit.client),
                "source": produit.source,
            },
            description="Création d'un produit",
        )

        messages.success(request, "Produit ajouté.")

        return redirect("produit:p_produit_add")

    return render(request, "produit/form.html", {"form": form, "action": "Ajouter"})


# =========================
# MODIFICATION
# =========================
@session_login_required
@transaction.atomic
def produit_edit(request, pk):
    produit = get_object_or_404(
        Produit.objects.select_for_update(),
        pk=pk,
    )

    utilisateur = utilisateur_session(request)
    role = utilisateur["role"]
    user_id = utilisateur["id"]

    # Seul l'enregistreur peut modifier son produit.
    # Le produit doit encore être impayé.
    if (
        not user_id
        or str(produit.enregistre_par_id) != str(user_id)
        or produit.paye
        or role not in ("UserMica", "SuperviseurMica")
    ):
        messages.error(
            request,
            "Modification refusée : vous n'êtes pas autorisé "
            "à modifier ce produit ou il est déjà payé.",
        )
        return redirect("produit:p_produit_liste")

    anciennes_valeurs = instantane_produit(produit)

    form = ProduitForm(
        request.POST or None,
        request.FILES or None,
        instance=produit,
    )

    if request.method == "POST" and form.is_valid():
        # Enregistrer les nouvelles valeurs.
        produit_modifie = form.save()

        nouvelles_valeurs = instantane_produit(produit_modifie)

        # L'historique est créé uniquement après validation
        # du formulaire, dans la même transaction.
        HistoriqueProduit.objects.create(
            produit_id_original=produit_modifie.pk,
            action="MODIFICATION",
            anciennes_valeurs=anciennes_valeurs,
            nouvelles_valeurs=nouvelles_valeurs,
            acteur_id=int(user_id),
            acteur_username=utilisateur["username"],
        )

        enregistrer_action(
            request,
            "UPDATE",
            "Produit",
            produit_modifie.pk,
            ancienne=anciennes_valeurs,
            nouvelle=nouvelles_valeurs,
            description="Modification validée avec historique",
        )

        messages.success(
            request,
            "Produit modifié. L'historique a été enregistré.",
        )
        return redirect("produit:p_produit_liste")

    return render(
        request,
        "produit/form.html",
        {
            "form": form,
            "action": "Modifier",
            "produit": produit,
        },
    )


# =========================
# SUPPRESSION AVEC HISTORIQUE
# =========================
@session_login_required
@transaction.atomic
def produit_delete(request, pk):
    # La suppression doit obligatoirement venir du formulaire POST.
    if request.method != "POST":
        messages.error(
            request,
            "Suppression refusée : veuillez confirmer la demande "
            "depuis la liste des produits.",
        )
        return redirect("produit:p_produit_liste")

    produit = get_object_or_404(
        Produit.objects.select_for_update(),
        pk=pk,
    )

    utilisateur = utilisateur_session(request)
    role = utilisateur["role"]
    user_id = utilisateur["id"]

    # Vérifier les droits de l'utilisateur.
    est_enregistreur = user_id is not None and str(produit.enregistre_par_id) == str(
        user_id
    )

    # Le SuperviseurMica peut supprimer.
    # Le UserMica peut supprimer uniquement son propre produit impayé.
    autorise = role == "SuperviseurMica" or (
        role == "UserMica" and est_enregistreur and not produit.paye
    )

    if not autorise:
        messages.error(
            request,
            "Suppression refusée : vous ne disposez pas " "des droits nécessaires.",
        )
        return redirect("produit:p_produit_liste")

    # Protection supplémentaire : un produit payé ne peut pas être supprimé.
    if produit.paye:
        messages.error(
            request,
            "Suppression impossible : le paiement de ce produit " "a déjà été validé.",
        )
        return redirect("produit:p_produit_liste")

    # Sauvegarder toutes les valeurs avant suppression.
    anciennes_valeurs = instantane_produit(produit)

    # Conserver une trace indépendante du produit supprimé.
    HistoriqueProduit.objects.create(
        produit_id_original=produit.pk,
        action="SUPPRESSION",
        anciennes_valeurs=anciennes_valeurs,
        nouvelles_valeurs={},
        acteur_id=int(user_id) if user_id else None,
        acteur_username=utilisateur["username"],
    )

    # Enregistrer la suppression dans le journal existant.
    enregistrer_action(
        request,
        "DELETE",
        "Produit",
        produit.pk,
        ancienne=anciennes_valeurs,
        description="Suppression validée avec historique",
    )

    # Supprimer le produit après sauvegarde de l'historique.
    produit.delete()

    messages.success(
        request,
        f"Le produit n° {pk} a été supprimé avec succès. "
        "Son historique est conservé.",
    )

    # Retour à la liste avec notification.
    return redirect("produit:p_produit_liste")


@session_login_required
def instantane_produit(produit):
    """
    Capture les valeurs du produit en JSON,
    y compris les clés étrangères, le paiement et la photo.
    """
    valeurs = {}

    for champ in produit._meta.concrete_fields:
        nom = champ.name
        valeur = getattr(produit, champ.attname)

        if valeur is None:
            valeurs[nom] = None
        elif hasattr(valeur, "isoformat"):
            valeurs[nom] = valeur.isoformat()
        elif champ.is_relation:
            valeurs[nom] = str(valeur)
        else:
            valeurs[nom] = str(valeur)

    return valeurs


def utilisateur_session(request):
    return {
        "id": request.session.get("user_id"),
        "username": request.session.get("username", ""),
        "role": request.session.get("role", ""),
    }

@session_login_required
@transaction.atomic
def historique_produits(request):
    utilisateur = utilisateur_session(request)
    role = utilisateur["role"]

    # Accès réservé à l'administration Mica.
    if role not in ("Admin", "SuperviseurMica", "UserMica"):
        messages.error(
            request,
            "Vous n'êtes pas autorisé à consulter cet historique.",
        )
        return redirect("produit:p_produit_liste")

    historiques = HistoriqueProduit.objects.all()

    # Filtrer par identifiant du produit.
    produit_id = request.GET.get("produit_id", "").strip()

    if produit_id.isdigit():
        historiques = historiques.filter(produit_id_original=int(produit_id))
    elif produit_id:
        messages.warning(
            request,
            "L'identifiant du produit doit être numérique.",
        )
        produit_id = ""

    # Filtrer par action.
    action = request.GET.get("action", "").strip()

    if action in ("MODIFICATION", "SUPPRESSION"):
        historiques = historiques.filter(action=action)
    else:
        action = ""

    # Pagination.
    paginator = Paginator(historiques, 25)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "produit/historique.html",
        {
            "historiques": page_obj,
            "page_obj": page_obj,
            "produit_id": produit_id,
            "action": action,
            "role": role,
        },
    )
