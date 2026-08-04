from django.shortcuts import (
    render,
    get_object_or_404,
    redirect
)

from django.contrib import messages

from .models import Categorie
from .forms import CategorieForm




def categorie_liste(request):

    queryset = Categorie.objects.all()

    nom = request.GET.get('nom', '').strip()

    if nom:
        queryset = queryset.filter(
            nom__icontains=nom
        )

    return render(
        request,
        "categorie/list.html",
        {
            "categories": queryset,
            "nom": nom,
        }
    )



# ==========================
# AJOUT CATEGORIE
# ==========================

def categorie_add(request):

    form = CategorieForm(
        request.POST or None
    )

    if request.method == "POST" and form.is_valid():

        form.save()

        messages.success(
            request,
            "Catégorie ajoutée avec succès."
        )

        return redirect(
            "categorie:categorie_liste"
        )

    return render(
        request,
        "categorie/form.html",
        {
            "form": form
        }
    )



# ==========================
# MODIFICATION CATEGORIE
# ==========================

def categorie_edit(request, id):

    categorie = get_object_or_404(
        Categorie,
        id=id
    )

    form = CategorieForm(
        request.POST or None,
        instance=categorie
    )

    if request.method == "POST" and form.is_valid():

        form.save()

        messages.success(
            request,
            "Catégorie modifiée avec succès."
        )

        return redirect(
            "categorie:categorie_liste"
        )

    return render(
        request,
        "categorie/form.html",
        {
            "form": form
        }
    )



# ==========================
# SUPPRESSION CATEGORIE
# ==========================

def categorie_delete(request, id):

    categorie = get_object_or_404(
        Categorie,
        id=id
    )

    if request.method == "POST":

        categorie.delete()

        messages.success(
            request,
            "Catégorie supprimée avec succès."
        )

        return redirect(
            "categorie:categorie_liste"
        )

    return render(
        request,
        "categorie/confirm_delete.html",
        {
            "categorie": categorie
        }
    )