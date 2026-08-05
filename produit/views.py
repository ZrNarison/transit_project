from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from django.core.paginator import Paginator

from .models import Produit, PaiementProduit
from .forms import ProduitForm

from depot.models import Distribution

from audit.utils import enregistrer_action



# =========================
# LISTE PRODUITS
# =========================

def produit_list(request):

    queryset = (
        Produit.objects
        .select_related(
            "client",
            "vehicule"
        )
        .order_by(
            "-created_at"
        )
    )


    client = request.GET.get(
        "client",
        ""
    ).strip()


    source = request.GET.get(
        "source",
        ""
    ).strip()


    vehicule = request.GET.get(
        "vehicule",
        ""
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
# VALIDATION PAIEMENT
# =========================


@transaction.atomic
def valider_paiement(request):

    if request.method != "POST":

        return redirect(
            "produit:p_produit_liste"
        )


    ids = request.POST.getlist(
        "produits"
    )


    if not ids:

        messages.warning(
            request,
            "Aucun produit sélectionné."
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
        .order_by(
            "created_at"
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



    total_non_paye = 0



    for produit in produits:


        reste = produit.montant_net



        for distribution in distributions:


            disponible = distribution.solde



            if disponible <= 0:

                continue



            montant = min(
                disponible,
                reste
            )



            PaiementProduit.objects.create(

                distribution=distribution,

                produit=produit,

                montant=montant

            )


            reste -= montant



            if reste <= 0:

                produit.paye = True

                produit.date_paiement = timezone.now()

                produit.save()


                enregistrer_action(
                    request,
                    "UPDATE",
                    "Produit",
                    produit.id,
                    nouvelle={
                        "paiement": str(produit.montant_net),
                        "date_paiement": str(produit.date_paiement)
                    },
                    description="Validation paiement produit"
                )


                break



        if reste > 0:

            total_non_paye += reste


            messages.warning(
                request,
                f"Produit {produit.id} : reste {reste} Ar"
            )



    if total_non_paye == 0:

        messages.success(
            request,
            "Paiement validé avec répartition automatique."
        )



    return redirect(
        "produit:p_produit_liste"
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
            "produit:p_produit_liste"
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