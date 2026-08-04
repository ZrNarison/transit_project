from django.shortcuts import render, redirect, get_object_or_404
from .models import Produit
from .forms import ProduitForm
from django.utils import timezone
from django.shortcuts import redirect
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from .models import Produit, PaiementProduit
from depot.models import Distribution


def produit_list(request):
    queryset = Produit.objects.select_related('client', 'vehicule').all()
    client = request.GET.get('client', '').strip()
    source = request.GET.get('source', '').strip()
    vehicule = request.GET.get('vehicule', '').strip()

    if client:
        queryset = queryset.filter(
            client__nom__icontains=client
        )
    if source:
        queryset = queryset.filter(source__icontains=source)
    if vehicule:
        queryset = queryset.filter(vehicule__num_vehicule__icontains=vehicule)

    return render(request, "produit/list.html", {
        "produits": queryset,
        "client": client,
        "source": source,
        "vehicule": vehicule,
    })

@transaction.atomic
def valider_paiement(request):

    if request.method == "POST":

        ids = request.POST.getlist("produits")

        if not ids:
            messages.warning(
                request,
                "Aucun produit sélectionné."
            )
            return redirect("produit:p_produit_liste")


        produits = Produit.objects.filter(
            id__in=ids,
            paye=False
        ).order_by("created_at")


        # Anciennes distributions en premier
        distributions = Distribution.objects.all().order_by(
            "depot__date",
            "id"
        )


        for produit in produits:

            reste_a_payer = produit.montant_net


            for distribution in distributions:


                solde = distribution.solde


                # Distribution vide
                if solde <= 0:
                    continue


                paiement = min(
                    solde,
                    reste_a_payer
                )


                # Enregistrement de la liaison
                PaiementProduit.objects.create(
                    distribution=distribution,
                    produit=produit,
                    montant=paiement
                )


                reste_a_payer -= paiement


                # Produit entièrement payé
                if reste_a_payer <= 0:

                    produit.paye = True
                    produit.date_paiement = timezone.now()
                    produit.save()

                    break


            # Si aucun dépôt ne suffit
            if reste_a_payer > 0:

                messages.warning(
                    request,
                    f"Solde insuffisant pour payer le produit {produit.id}. "
                    f"Reste : {reste_a_payer} Ar"
                )


        messages.success(
            request,
            "Paiement effectué avec répartition automatique."
        )


    return redirect("produit:p_produit_liste")

def produit_add(request):
    if request.method == "POST":
        form = ProduitForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("produit:p_produit_liste")
    else:
        form = ProduitForm()

    return render(request, "produit/form.html", {"form": form})


def produit_edit(request, pk):
    produit = get_object_or_404(Produit, pk=pk)

    if request.method == "POST":
        form = ProduitForm(request.POST, request.FILES, instance=produit)
        if form.is_valid():
            form.save()
            return redirect("produit:p_produit_liste")
    else:
        form = ProduitForm(instance=produit)

    return render(request, "produit/form.html", {"form": form})


def produit_delete(request, pk):
    produit = get_object_or_404(Produit, pk=pk)

    if request.method == "POST":
        produit.delete()
        return redirect("produit:p_produit_liste")

    return render(request, "produit/delete.html", {"produit": produit})