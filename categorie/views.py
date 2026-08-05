from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib import messages

from .models import Categorie
from .forms import CategorieForm

from audit.utils import enregistrer_action



# =====================================
# LISTE
# =====================================
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



# =====================================
# AJOUT
# =====================================
def categorie_add(request):

    form = CategorieForm(
        request.POST or None
    )


    if request.method == "POST" and form.is_valid():

        categorie = form.save()


        enregistrer_action(
            request,
            action="CREATE",
            module="Categorie",
            objet_id=categorie.id,
            ancienne=None,
            nouvelle={
                "nom": categorie.nom,
                "description": categorie.description
            },
            description="Création d'une catégorie"
        )


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



# =====================================
# MODIFICATION
# =====================================
def categorie_edit(request, id):

    categorie = get_object_or_404(
        Categorie,
        id=id
    )


    ancienne = {
        "nom": categorie.nom,
        "description": categorie.description
    }


    form = CategorieForm(
        request.POST or None,
        instance=categorie
    )


    if request.method == "POST" and form.is_valid():

        categorie = form.save()


        nouvelle = {
            "nom": categorie.nom,
            "description": categorie.description
        }


        enregistrer_action(
            request,
            action="UPDATE",
            module="Categorie",
            objet_id=categorie.id,
            ancienne=ancienne,
            nouvelle=nouvelle,
            description="Modification d'une catégorie"
        )


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



# =====================================
# SUPPRESSION
# =====================================
def categorie_delete(request, id):

    categorie = get_object_or_404(
        Categorie,
        id=id
    )


    if request.method == "POST":


        ancienne = {
            "nom": categorie.nom,
            "description": categorie.description
        }


        objet_id = categorie.id


        categorie.delete()


        enregistrer_action(
            request,
            action="DELETE",
            module="Categorie",
            objet_id=objet_id,
            ancienne=ancienne,
            nouvelle=None,
            description="Suppression d'une catégorie"
        )


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