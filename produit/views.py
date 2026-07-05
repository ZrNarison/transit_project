from django.db.models import Q
from django.shortcuts import render, redirect,get_object_or_404
from .models import Produit
from .forms import ProduitForm
from django.utils import timezone


def p_produit_list(request):
    produits = Produit.objects.all()

    client = request.GET.get("client", "")
    nom = request.GET.get("nom", "")
    source = request.GET.get("source", "")

    if client:
        produits = produits.filter(
            Q(id_client__nom__icontains=client) |
            Q(id_client__prenom__icontains=client)
        )

    if nom:
        produits = produits.filter(
            Nom_Prod__icontains=nom
        )

    if source:
        produits = produits.filter(
            Source_Prod__icontains=source
        )

    context = {
        "produits": produits,
        "client": client,
        "nom": nom,
        "source": source,
    }

    return render(request, "produit/list.html", context)


def p_produit_add(request):
    if request.method == "POST":
        form = ProduitForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("produit:p_produit_liste")
    else:
        form = ProduitForm()

    return render(request, "produit/form.html", {"form": form})


def p_produit_edit(request, id):

    produit = get_object_or_404(
        Produit,
        id=id
    )

    if request.method == "POST":

        form = ProduitForm(
            request.POST,
            request.FILES,
            instance=produit
        )

        if form.is_valid():
            form.save()

            return redirect(
                "produit:p_produit_liste"
            )

    else:
        form = ProduitForm(
            instance=produit
        )

    return render(
        request,
        "produit/form.html",
        {
            "form": form
        }
    )


def p_produit_delete(request, id):

    produit = get_object_or_404(
        Produit,
        id=id
    )

    if request.method == "POST":

        produit.delete()

        return redirect(
            "produit:p_produit_liste"
        )

    return render(
        request,
        "produit/confirm_delete.html",
        {
            "produit": produit
        }
    )

def valider_paiement(request):
    if request.method == "POST":

        ids = request.POST.getlist("produits")

        produits = Produit.objects.filter(id__in=ids)

        for produit in produits:

            produit.paye = True
            produit.date_paiement = timezone.now()

            produit.save()

    return redirect("produit:p_produit_liste")