from decimal import Decimal
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)
from avanceclient.models import (
    AvanceClient,
    UtilisationAvanceClient
)
from avances.models import Avance
from avanceclient.models import AvanceClient
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator
from .models import Produit, PaiementProduit
from .forms import ProduitForm
from retours.models import Retour
from depot.models import Distribution
from audit.utils import enregistrer_action
from logs.utils import enregistrer_log



# =========================
# LISTE PRODUITS
# =========================

def produit_list(request):
    queryset = (
        Produit.objects
        .select_related("client","vehicule")
        .order_by("-created_at")
    )

    client = request.GET.get("client",""
                             ).strip()

    source = request.GET.get(
        "source",
        ""
    ).strip()

    vehicule = request.GET.get("vehicule",""
                               ).strip()

    if client:
        queryset = queryset.filter(
            client__nom__icontains=client
        )

    if source:
        queryset = queryset.filter(
            source__icontains=source
        )


    if vehicule:
        queryset = queryset.filter(
            vehicule__num_vehicule__icontains=vehicule
        )
    #20 enregistrement par gage
    paginator = Paginator(
        queryset,
        20
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
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
        }
    )



# =========================
# AJOUT
# =========================
def produit_add(request):
    form = ProduitForm(
        request.POST or None,
        request.FILES or None
    )

    if request.method == "POST" and form.is_valid():
        produit = form.save()

        #Audit et historique
        enregistrer_action(
            request,
            "CREATE",
            "Produit",
            produit.id,
            nouvelle={
                "montant": str(produit.montant),
                "client": str(produit.client),
                "source": produit.source
            },
            description="Création d'un produit"
        )

        messages.success(
            request,
            "Produit ajouté."
        )

        return redirect(
            "produit:p_produit_add"
        )

    return render(
        request,
        "produit/form.html",
        {
            "form": form,
            "action": "Ajouter"
        }
    )


# =========================
# MODIFICATION
# =========================

def produit_edit(request, pk):
    produit = get_object_or_404(
        Produit,
        pk=pk
    )

    ancienne = str(produit)
    form = ProduitForm(
        request.POST or None,
        request.FILES or None,
        instance=produit
    )

    if request.method == "POST" and form.is_valid():
        produit = form.save()

        enregistrer_action(
            request,
            "UPDATE",
            "Produit",
            produit.id,
            ancienne=ancienne,
            nouvelle=str(produit),
            description="Modification d'un produit"
        )
        messages.success(
            request,
            "Produit modifié."
        )


        return redirect(
            "produit:p_produit_liste"
        )

    return render(
        request,
        "produit/form.html",
        {
            "form": form,
            "action": "Modifier"
        }
    )


# =========================
# SUPPRESSION
# =========================
def produit_delete(request, pk):
    produit = get_object_or_404(
        Produit,
        pk=pk
    )

    if request.method == "POST":

        enregistrer_action(
            request,
            "DELETE",
            "Produit",
            produit.id,
            ancienne=str(produit),
            description="Suppression d'un produit"
        )

        produit.delete()

        messages.success(
            request,
            "Produit supprimé."
        )


        return redirect(
            "produit:p_produit_liste"
        )

    return render(
        request,
        "produit/delete.html",
        {
            "produit": produit
        }
    )

#====================
# VALIDATION PAIEMENT
#====================
@transaction.atomic
def valider_paiement(request):

    if request.method != "POST":
        return redirect("produit:p_produit_liste")

    ids = request.POST.getlist("produits")
    remboursement = request.POST.get(
        "remboursement",
        "AUCUN"
    )
    montant_retour_demande = Decimal(
        request.POST.get("montant_retour", "0") or "0"
    )

    if not ids:
        messages.warning(
            request,
            "Aucun produit sélectionné."
        )
        return redirect("produit:p_produit_liste")

    user_id = request.session.get("user_id")

    produits = (
        Produit.objects
        .filter(
            id__in=ids,
            paye=False
        )
        .select_related(
            "client",
            "vehicule"
        )
    )

    distributions = (
        Distribution.objects
        .select_related("depot")
        .order_by(
            "depot__date",
            "id"
        )
    )

    avances_courantes = {}
    produits_payes = 0
    produits_non_payes = []

    if remboursement != "AUCUN":
        client_ids = set(
            produits
            .values_list("client_id", flat=True)
        )

        if len(client_ids) > 1:
            messages.warning(
                request,
                "Le remboursement ne peut être appliqué qu'à un seul client à la fois."
            )
            return redirect("produit:p_produit_liste")

        for client_id in client_ids:
            avances_client = (
                AvanceClient.objects
                .filter(client_id=client_id)
                .order_by("date", "id")
            )

            avance_courante = None
            for avance in avances_client:
                if avance.reste > 0:
                    avance_courante = avance
                    break

            if avance_courante is None:
                messages.warning(
                    request,
                    "Aucune avance en cours disponible pour remboursement pour ce client."
                )
                return redirect("produit:p_produit_liste")

            if remboursement == "PARTIEL":
                if montant_retour_demande <= 0:
                    messages.warning(
                        request,
                        "Merci de saisir un montant de remboursement partiel supérieur à 0."
                    )
                    return redirect("produit:p_produit_liste")

                if montant_retour_demande > avance_courante.reste:
                    messages.warning(
                        request,
                        "Le montant de remboursement partiel dépasse le reste de l'avance en cours pour ce client."
                    )
                    return redirect("produit:p_produit_liste")

            avances_courantes[client_id] = avance_courante

    clients_to_refund = set()
    any_product_paid = False
    any_product_incomplete = False

    for produit in produits:
        montant_total = produit.montant_net
        reste = montant_total

        ancienne = {
            "paye": produit.paye,
            "montant_net": str(montant_total)
        }

        montant_avance = Decimal("0")
        montant_distribution = Decimal("0")

        # =========================================
        # 1 - CALCUL DU PAIEMENT SANS ENREGISTRER
        # =========================================
        avances = (
            AvanceClient.objects
            .filter(
                client=produit.client
            )
            .order_by(
                "date",
                "id"
            )
        )

        avance_usages = []
        distribution_payments = []

        for avance in avances:
            disponible = avance.reste
            if disponible <= 0:
                continue

            utilisation = min(
                disponible,
                reste
            )

            if utilisation > 0:
                avance_usages.append((avance, utilisation))
                montant_avance += utilisation
                reste -= utilisation

            if reste <= 0:
                break

        # =========================================
        # 2 - COMPLEMENT DISTRIBUTION SANS ENREGISTRER
        # =========================================
        if reste > 0:
            for distribution in distributions:
                disponible = distribution.solde
                if disponible <= 0:
                    continue

                paiement = min(
                    disponible,
                    reste
                )

                if paiement <= 0:
                    continue

                distribution_payments.append((distribution, paiement))
                montant_distribution += paiement
                reste -= paiement

                if reste <= 0:
                    break

        # =========================================
        # 3 - VERIFICATION ET ET ENREGISTREMENT
        # =========================================
        total_paye = montant_avance + montant_distribution
        if total_paye < montant_total:
            messages.warning(
                request,
                f"Produit {produit.id} reste {reste} Ar"
            )
            enregistrer_log(
                f"Produit {produit.id} incomplet reste {reste} Ar",
                "WARNING",
                "Produit"
            )
            produits_non_payes.append(produit.id)
            any_product_incomplete = True
            continue

        for avance, utilisation in avance_usages:
            UtilisationAvanceClient.objects.create(
                avance=avance,
                produit=produit,
                montant=utilisation
            )
            avance.montant_utilise += utilisation
            avance.save()

        for distribution, paiement in distribution_payments:
            PaiementProduit.objects.create(
                distribution=distribution,
                produit=produit,
                montant=paiement
            )

        produit.paye = True
        produit.date_paiement = timezone.now()
        produit.save()
        clients_to_refund.add(produit.client)
        any_product_paid = True

        # =========================================
        # 5 - AUDIT
        # =========================================
        enregistrer_action(
            request,
            "UPDATE",
            "Produit",
            produit.id,
            ancienne=ancienne,
            nouvelle={
                "paye": True,
                "montant_net": str(montant_total),
                "avance": str(montant_avance),
                "distribution": str(montant_distribution),
                "date_paiement": str(produit.date_paiement)
            },
            description=
            "Validation paiement produit"
        )

        enregistrer_log(
            f"Produit {produit.id} payé",
            "INFO",
            "Produit"
        )

    # =========================================
    # 6 - REMBOURSEMENT AVANCE CLIENT
    # =========================================
    if remboursement != "AUCUN" and clients_to_refund:
        if remboursement == "PARTIEL" and len(clients_to_refund) != 1:
            messages.warning(
                request,
                "Le remboursement partiel ne peut être appliqué qu'à un seul client à la fois."
            )
        else:
            for client in clients_to_refund:
                avance_courante = avances_courantes.get(client.id)

                if not avance_courante or avance_courante.reste <= 0:
                    messages.warning(
                        request,
                        f"Aucune avance en cours disponible pour remboursement pour le client {client}."
                    )
                    continue

                if remboursement == "TOTAL":
                    montant_retour = avance_courante.reste
                else:
                    montant_retour = montant_retour_demande
                    if montant_retour <= 0:
                        messages.warning(
                            request,
                            "Veuillez saisir un montant de remboursement partiel supérieur à 0."
                        )
                        continue
                    if montant_retour > avance_courante.reste:
                        messages.warning(
                            request,
                            f"Le montant de remboursement partiel ({montant_retour} Ar) dépasse le reste de l'avance en cours ({avance_courante.reste} Ar) pour le client {client}."
                        )
                        continue

                retour = Retour.objects.create(
                    client=client,
                    montant=montant_retour,
                    motif=
                    "Remboursement avance client après paiement produit",
                    enregistrer_par_id=user_id
                )

                avance_courante.montant_retour += montant_retour
                avance_courante.save()

                enregistrer_log(
                    f"Retour créé ID {retour.id} montant {montant_retour} Ar",
                    "INFO",
                    "Retour"
                )

    if any_product_incomplete:
        if any_product_paid:
            messages.warning(
                request,
                "Validation partielle : certains produits restent impayés. Vérifiez les montants restants."
            )
        else:
            messages.warning(
                request,
                "Aucun produit n'a été entièrement payé. Vérifiez les montants restants."
            )
    else:
        messages.success(
            request,
            "Validation paiement terminée avec succès."
        )

    return redirect(
        "produit:p_produit_liste"
    )