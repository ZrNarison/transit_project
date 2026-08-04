from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib import messages

from .models import Categorie
from .forms import CategorieForm



def categorie_liste(request):

    categories = (
        Categorie.objects
        .all()
        .order_by("nom")
    )


    nom = request.GET.get(
        "nom",
        ""
    ).strip()


    if nom:

        categories = categories.filter(
            nom__icontains=nom
        )


    return render(
        request,
        "categorie/list.html",
        {
            "categories": categories,
            "nom": nom,
        }
    )



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
            "form": form,
            "titre": "Ajouter une catégorie"
        }
    )



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
            "form": form,
            "titre": "Modifier une catégorie"
        }
    )



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