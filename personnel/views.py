from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.core.paginator import Paginator
from django.contrib import messages

from .models import Personnel
from .forms import PersonnelForm

from audit.utils import enregistrer_action



# =========================
# LISTE PERSONNEL
# =========================

def personnel_list(request):

    queryset = (
        Personnel.objects
        .select_related("categorie")
        .all()
        .order_by("nom", "prenom")
    )


    nom = request.GET.get("nom", "").strip()
    prenom = request.GET.get("prenom", "").strip()
    fonction = request.GET.get("fonction", "").strip()
    categorie = request.GET.get("categorie", "").strip()



    if nom:
        queryset = queryset.filter(
            nom__icontains=nom
        )


    if prenom:
        queryset = queryset.filter(
            prenom__icontains=prenom
        )


    if fonction:
        queryset = queryset.filter(
            fonction__icontains=fonction
        )


    if categorie:
        queryset = queryset.filter(
            categorie__nom__icontains=categorie
        )


    paginator = Paginator(
        queryset,
        12
    )


    page_number = request.GET.get(
        "page"
    )


    page_obj = paginator.get_page(
        page_number
    )


    return render(
        request,
        "personnel/list.html",
        {
            "personnels": page_obj,
            "page_obj": page_obj,

            "nom": nom,
            "prenom": prenom,
            "fonction": fonction,
            "categorie": categorie,
        }
    )



# =========================
# AJOUT
# =========================

def personnel_add(request):

    form = PersonnelForm(
        request.POST or None,
        request.FILES or None
    )


    if request.method == "POST":

        if form.is_valid():

            personnel = form.save()


            enregistrer_action(
                request,
                "CREATE",
                "Personnel",
                personnel.id,
                nouvelle={
                    "nom": personnel.nom,
                    "prenom": personnel.prenom,
                    "fonction": personnel.fonction,
                    "categorie": str(personnel.categorie)
                },
                description="Ajout d'un personnel"
            )


            messages.success(
                request,
                "Personnel ajouté avec succès."
            )


            return redirect(
                "personnel:personnel_list"
            )


    return render(
        request,
        "personnel/form.html",
        {
            "form": form,
            "action": "Ajouter"
        }
    )



# =========================
# DETAIL
# =========================

def personnel_detail(request, id):

    personnel = get_object_or_404(
        Personnel.objects.select_related(
            "categorie"
        ),
        id=id
    )


    return render(
        request,
        "personnel/detail.html",
        {
            "personnel": personnel
        }
    )



# =========================
# MODIFICATION
# =========================

def personnel_edit(request, id):

    personnel = get_object_or_404(
        Personnel,
        id=id
    )


    ancienne = {
        "nom": personnel.nom,
        "prenom": personnel.prenom,
        "fonction": personnel.fonction,
        "categorie": str(personnel.categorie)
    }


    form = PersonnelForm(
        request.POST or None,
        request.FILES or None,
        instance=personnel
    )


    if request.method == "POST":

        if form.is_valid():

            personnel = form.save()


            enregistrer_action(
                request,
                "UPDATE",
                "Personnel",
                personnel.id,
                ancienne=ancienne,
                nouvelle={
                    "nom": personnel.nom,
                    "prenom": personnel.prenom,
                    "fonction": personnel.fonction,
                    "categorie": str(personnel.categorie)
                },
                description="Modification d'un personnel"
            )


            messages.success(
                request,
                "Personnel modifié avec succès."
            )


            return redirect(
                "personnel:personnel_list"
            )


    return render(
        request,
        "personnel/form.html",
        {
            "form": form,
            "action": "Modifier"
        }
    )



# =========================
# SUPPRESSION
# =========================

def personnel_delete(request, id):

    personnel = get_object_or_404(
        Personnel,
        id=id
    )


    ancienne = {
        "nom": personnel.nom,
        "prenom": personnel.prenom,
        "fonction": personnel.fonction,
        "categorie": str(personnel.categorie)
    }



    if request.method == "POST":


        enregistrer_action(
            request,
            "DELETE",
            "Personnel",
            personnel.id,
            ancienne=ancienne,
            description="Suppression d'un personnel"
        )


        personnel.delete()


        messages.success(
            request,
            "Personnel supprimé avec succès."
        )


        return redirect(
            "personnel:personnel_list"
        )


    return render(
        request,
        "personnel/confirm_delete.html",
        {
            "personnel": personnel
        }
    )