from django.shortcuts import render, redirect, get_object_or_404
from .models import Produit
from .forms import ProduitForm
from django.utils import timezone


def produit_list(request):
    produits = Produit.objects.all()
    return render(request, "produit/list.html", {"produits": produits})

def valider_paiement(request):

    if request.method == "POST":

        ids = request.POST.getlist("produits")

        produits = Produit.objects.filter(id__in=ids)

        for p in produits:
            p.paye = True
            p.date_paiement = timezone.now()
            p.save()

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