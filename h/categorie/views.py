from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib import messages

from .models import h_Categorie
from .forms import h_CategorieForm

from audit.utils import enregistrer_action


# ============================================================
# LISTE DES CATÉGORIES
# ============================================================

def h_categorie_liste(request):

    categories = (
        h_Categorie.objects
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
        "h/categorie/list.html",
        {
            "categories": categories,
            "nom": nom,
        }
    )


# ============================================================
# AJOUT D'UNE CATÉGORIE
# ============================================================

def h_categorie_add(request):

    form = h_CategorieForm(
        request.POST or None
    )

    if request.method == "POST" and form.is_valid():

        categorie = form.save()

        # ----------------------------------------------------
        # AUDIT : CRÉATION
        # ----------------------------------------------------

        enregistrer_action(
            request,
            action="CREATE",
            table="Categorie",
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
            "categorie:h_categorie_liste"
        )

    return render(
        request,
        "h/categorie/form.html",
        {
            "form": form,
            "titre": "Ajouter une catégorie"
        }
    )


# ============================================================
# MODIFICATION D'UNE CATÉGORIE
# ============================================================

def h_categorie_edit(request, id):

    categorie = get_object_or_404(
        h_Categorie,
        id=id
    )

    # --------------------------------------------------------
    # Anciennes valeurs
    # --------------------------------------------------------

    ancienne = {
        "nom": categorie.nom,
        "description": categorie.description
    }

    form = h_CategorieForm(
        request.POST or None,
        instance=categorie
    )

    if request.method == "POST" and form.is_valid():

        categorie = form.save()

        # ----------------------------------------------------
        # Nouvelles valeurs
        # ----------------------------------------------------

        nouvelle = {
            "nom": categorie.nom,
            "description": categorie.description
        }

        # ----------------------------------------------------
        # AUDIT : MODIFICATION
        # ----------------------------------------------------

        enregistrer_action(
            request,
            action="UPDATE",
            table="Categorie",
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
            "h_categorie:h_categorie_liste"
        )

    return render(
        request,
        "h/categorie/form.html",
        {
            "form": form,
            "titre": "Modifier une catégorie"
        }
    )


# ============================================================
# SUPPRESSION D'UNE CATÉGORIE
# ============================================================

def h_categorie_delete(request, id):

    categorie = get_object_or_404(
        h_Categorie,
        id=id
    )

    if request.method == "POST":

        # ----------------------------------------------------
        # Sauvegarder les anciennes valeurs
        # AVANT suppression
        # ----------------------------------------------------

        ancienne = {
            "nom": categorie.nom,
            "description": categorie.description
        }

        objet_id = categorie.id

        # ----------------------------------------------------
        # Suppression
        # ----------------------------------------------------

        categorie.delete()

        # ----------------------------------------------------
        # AUDIT : SUPPRESSION
        # ----------------------------------------------------

        enregistrer_action(
            request,
            action="DELETE",
            table="Categorie",
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
            "h_categorie:h_categorie_liste"
        )

    return render(
        request,
        "h/categorie/confirm_delete.html",
        {
            "categorie": categorie
        }
    )
