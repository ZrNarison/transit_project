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

        return redirect(
            "produit:p_produit_liste"
        )

    user_id = request.session.get(
        "user_id"
    )

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

    for produit in produits:
        montant_net = produit.montant_net
        reste = montant_net
        avance_utilisee = Decimal("0")
        distribution_utilisee = Decimal("0")

        # ======================================
        # 1 - AVANCE CLIENT
        # ======================================

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

        for avance in avances:
            disponible = avance.reste
            if disponible <= 0:
                continue

            utilisation = min(
                disponible,
                reste
            )

            UtilisationAvanceClient.objects.create(
                avance=avance,
                produit=produit,
                montant=utilisation
            )

            avance.montant_utilise += utilisation
            avance.save()
            avance_utilisee += utilisation
            reste -= utilisation

            if reste <= 0:
                break


        # ======================================
        # 2 - DISTRIBUTION
        # ======================================

        if reste > 0:

            distributions = (
                Distribution.objects
                .select_related(
                    "depot"
                )
                .order_by(
                    "depot__date",
                    "id"
                )
            )


            for distribution in distributions:
                disponible = distribution.solde

                if disponible <= 0:
                    continue

                paiement = min(
                    disponible,
                    reste
                )

                PaiementProduit.objects.create(
                    distribution=distribution,
                    produit=produit,
                    montant=paiement
                )

                distribution_utilisee += paiement
                reste -= paiement

                if reste <= 0:
                    break


        # ======================================
        # 3 - PRODUIT VALIDE
        # ======================================

        produit.paye = True
        produit.date_paiement = timezone.now()
        produit.save()


        # ======================================
        # 4 - REMBOURSEMENT AVANCE
        # ======================================
        #PAS DE REMBOURSEMENT
        if remboursement != "AUCUN":
            avances_retour = (
                AvanceClient.objects
                .filter(
                    client=produit.client
                )
                .order_by(
                    "date",
                    "id"
                )
            )

            disponible_total = sum(
                a.reste
                for a in avances_retour
            )

            montant_retour = Decimal("0")

            if remboursement == "TOTAL":
                montant_retour = disponible_total

            #REMBOURSEMENT PARTIEL
            elif remboursement == "PARTIEL":

                montant_retour = min(
                    montant_retour_demande,
                    disponible_total
                )

            if montant_retour > 0:
                Retour.objects.create(
                    client=produit.client,
                    montant=montant_retour,
                    motif=
                    "Remboursement avance client après validation paiement",
                    enregistrer_par_id=user_id
                )
                reste_retour = montant_retour

                for avance in avances_retour:
                    disponible = avance.reste
                    if disponible <= 0:
                        continue

                    retrait = min(
                        disponible,
                        reste_retour
                    )

                    avance.montant_retour += retrait
                    avance.save()

                    reste_retour -= retrait
                    if reste_retour <= 0:
                        break
        # ======================================
        # 5 - LOG
        # ======================================
        enregistrer_log(
            f"Produit {produit.id} validé paiement",
            "INFO",
            "Produit"
        )

    messages.success(
        request,
        "Paiement validé avec succès."
    )

    return redirect(
        "produit:p_produit_liste"
    )

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

    #IDENTIFICATION DE L'ENREGISTREUR
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

    for produit in produits:
        montant_total = produit.montant_net
        reste = montant_total

        ancienne = {
            "paye": produit.paye,
            "montant": str(montant_total)
        }


        # ==============================
        # 1 - AVANCE CLIENT
        # ==============================
        avance_utilisee = Decimal("0")
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

        for avance in avances:
            disponible = avance.reste
            if disponible <= 0:
                continue

            utilisation = min(
                disponible,
                reste
            )

            UtilisationAvanceClient.objects.create(
                avance=avance,
                produit=produit,
                montant=utilisation
            )

            avance.montant_utilise += utilisation
            avance.save()

            reste -= utilisation
            avance_utilisee += utilisation

            if reste <= 0:
                break


        # ==============================
        # 2 - DISTRIBUTION
        # ==============================
        distribution_utilisee = Decimal("0")
        if reste > 0:
            distributions = (
                Distribution.objects
                .select_related("depot")
                .order_by(
                    "depot__date",
                    "id"
                )
            )

            for distribution in distributions:
                disponible = distribution.solde
                if disponible <= 0:
                    continue

                paiement = min(
                    disponible,
                    reste
                )

                PaiementProduit.objects.create(
                    distribution=distribution,
                    produit=produit,
                    montant=paiement
                )

                reste -= paiement
                distribution_utilisee += paiement

                if reste <= 0:
                    break

        # ==============================
        # 3 - VERIFICATION COMPLETE
        # ==============================
        if reste > 0:
            messages.warning(
                request,
                f"Produit {produit.id} non payé. Reste : {reste} Ar"
            )

            enregistrer_log(
                f"Produit {produit.id} incomplet reste {reste}",
                "WARNING",
                "Produit"
            )
            continue

        # ==============================
        # 4 - PRODUIT PAYE
        # ==============================

        produit.paye = True
        produit.date_paiement = timezone.now()
        produit.save()

        # ==============================
        # 5 - REMBOURSEMENT AVANCE
        # ==============================
        if remboursement != "AUCUN":
            avances_retour = (
                AvanceClient.objects
                .filter(
                    client=produit.client
                )
                .order_by(
                    "date",
                    "id"
                )
            )

            disponible_total = sum(
                a.reste
                for a in avances_retour
            )

            if remboursement == "TOTAL":
                montant_retour = disponible_total

            else:
                montant_retour = min(
                    montant_retour_demande,
                    disponible_total
                )


            if montant_retour > 0:
                retour = Retour.objects.create(
                    client=produit.client,
                    montant=montant_retour,
                    motif=
                    "Remboursement avance client après paiement produit",
                    enregistrer_par_id=user_id
                )

                reste_retour = montant_retour

                for avance in avances_retour:
                    disponible = avance.reste

                    if disponible <= 0:
                        continue

                    retrait = min(
                        disponible,
                        reste_retour
                    )

                    avance.montant_retour += retrait
                    avance.save()

                    reste_retour -= retrait

                    if reste_retour <= 0:
                        break

        # ==============================
        # 6 - AUDIT
        # ==============================

        enregistrer_action(
            request,
            "UPDATE",
            "Produit",
            produit.id,
            ancienne=ancienne,
            nouvelle={
                "paye": True,
                "avance": str(avance_utilisee),
                "distribution": str(distribution_utilisee)
            },

            description=
            "Validation paiement produit"
        )


        enregistrer_log(
            f"Produit {produit.id} payé",
            "INFO",
            "Produit"
        )



    messages.success(
        request,
        "Validation paiement terminée."
    )


    return redirect(
        "produit:p_produit_liste"
    )

    if request.method != "POST":

        return redirect(
            "produit:p_produit_liste"
        )


    ids = request.POST.getlist(
        "produits"
    )


    remboursement = request.POST.get(
        "remboursement",
        "AUCUN"
    )


    montant_retour_demande = Decimal(
        request.POST.get(
            "montant_retour",
            "0"
        )
        or "0"
    )


    user_id = request.session.get(
        "user_id"
    )


    if not ids:

        messages.warning(
            request,
            "Aucun produit sélectionné."
        )

        enregistrer_log(
            "Validation paiement sans produit",
            "WARNING",
            "Produit"
        )

        return redirect(
            "produit:p_produit_liste"
        )



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
        .select_related(
            "depot"
        )
        .order_by(
            "depot__date",
            "id"
        )
    )



    for produit in produits:


        montant_total = produit.montant_net

        reste = montant_total


        ancienne = {

            "paye": produit.paye,

            "montant_net":
                str(montant_total)

        }



        montant_avance = Decimal("0")

        montant_distribution = Decimal("0")



        # =========================================
        # 1 - UTILISATION AVANCE CLIENT
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


        for avance in avances:


            disponible = avance.reste


            if disponible <= 0:

                continue



            utilisation = min(
                disponible,
                reste
            )


            UtilisationAvanceClient.objects.create(

                avance=avance,

                produit=produit,

                montant=utilisation

            )


            avance.montant_utilise += utilisation

            avance.save()



            montant_avance += utilisation

            reste -= utilisation



            if reste <= 0:

                break



        # =========================================
        # 2 - COMPLEMENT DISTRIBUTION
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



                PaiementProduit.objects.create(

                    distribution=distribution,

                    produit=produit,

                    montant=paiement

                )


                montant_distribution += paiement


                reste -= paiement



                if reste <= 0:

                    break



        # =========================================
        # 3 - VALIDATION ETAT PRODUIT
        # =========================================


        total_paye = (
            montant_avance
            +
            montant_distribution
        )



        if total_paye >= montant_total:


            produit.paye = True

            produit.date_paiement = timezone.now()

            produit.save()



        else:


            enregistrer_log(

                f"Produit {produit.id} incomplet "
                f"reste {reste} Ar",

                "WARNING",

                "Produit"

            )


            messages.warning(

                request,

                f"Produit {produit.id} reste {reste} Ar"

            )


            continue



        # =========================================
        # 4 - REMBOURSEMENT AVANCE CLIENT
        # =========================================


        if remboursement != "AUCUN":


            avances_retour = (
                AvanceClient.objects
                .filter(
                    client=produit.client
                )
                .order_by(
                    "date",
                    "id"
                )
            )



            disponible_total = sum(

                a.reste

                for a in avances_retour

            )



            if remboursement == "TOTAL":

                montant_retour = disponible_total


            elif remboursement == "PARTIEL":

                montant_retour = min(

                    montant_retour_demande,

                    disponible_total

                )


            else:

                montant_retour = Decimal("0")



            if montant_retour > 0:


                retour = Retour.objects.create(

                    client=produit.client,

                    montant=montant_retour,

                    motif=
                    "Remboursement avance client après paiement",

                    enregistrer_par_id=user_id

                )



                reste_retour = montant_retour



                for avance in avances_retour:


                    disponible = avance.reste


                    if disponible <= 0:

                        continue



                    retrait = min(

                        disponible,

                        reste_retour

                    )



                    avance.montant_retour += retrait

                    avance.save()



                    reste_retour -= retrait



                    if reste_retour <= 0:

                        break



                enregistrer_log(

                    f"Retour créé ID {retour.id} "
                    f"montant {montant_retour} Ar",

                    "INFO",

                    "Retour"

                )



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

                "montant_net":
                    str(montant_total),

                "avance":
                    str(montant_avance),

                "distribution":
                    str(montant_distribution),

                "date_paiement":
                    str(produit.date_paiement)

            },

            description=
            "Validation paiement produit"

        )



        enregistrer_log(

            f"Produit {produit.id} payé",

            "INFO",

            "Produit"

        )



    messages.success(

        request,

        "Validation paiement terminée avec succès."

    )


    return redirect(
        "produit:p_produit_liste"
    )