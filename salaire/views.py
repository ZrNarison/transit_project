from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib import messages

from django.db.models import Q

from django.core.paginator import Paginator

from .models import Salaire
from .forms import SalaireForm

from audit.utils import enregistrer_action



# ==========================
# LISTE
# ==========================

def salaire_list(request):

    queryset = (
        Salaire.objects
        .select_related(
            "personnel"
        )
        .order_by(
            "-id"
        )
    )


    personnel = request.GET.get(
        "personnel",
        ""
    ).strip()


    montant = request.GET.get(
        "montant",
        ""
    ).strip()



    if personnel:

        queryset = queryset.filter(

            Q(personnel__nom__icontains=personnel)
            |
            Q(personnel__prenom__icontains=personnel)

        )


    if montant:

        queryset = queryset.filter(
            montant__icontains=montant
        )



    paginator = Paginator(
        queryset,
        10
    )


    page_number = request.GET.get(
        "page"
    )


    page_obj = paginator.get_page(
        page_number
    )



    return render(

        request,

        "salaire/list.html",

        {

            "salaires": page_obj,

            "page_obj": page_obj,

            "personnel": personnel,

            "montant": montant,

        }

    )





# ==========================
# AJOUT
# ==========================

def salaire_add(request):


    if request.method == "POST":


        form = SalaireForm(
            request.POST
        )


        if form.is_valid():


            salaire = form.save()


            enregistrer_action(
                request,
                "CREATE",
                "Salaire",
                salaire.id,
                nouvelle={
                    "personnel": str(salaire.personnel),
                    "montant": str(salaire.montant)
                },
                description="Création d'un salaire"
            )


            messages.success(
                request,
                "Salaire ajouté avec succès."
            )


            return redirect(
                "salaire:salaire_list"
            )



        messages.error(

            request,

            "Veuillez corriger les erreurs."

        )


    else:


        form = SalaireForm()



    return render(

        request,

        "salaire/form.html",

        {

            "form": form,

            "action": "Ajouter"

        }

    )





# ==========================
# MODIFICATION
# ==========================

def salaire_edit(request, id):


    salaire = get_object_or_404(
        Salaire,
        id=id
    )


    ancienne = str(salaire)



    if request.method == "POST":


        form = SalaireForm(

            request.POST,

            instance=salaire

        )


        if form.is_valid():


            salaire = form.save()


            enregistrer_action(
                request,
                "UPDATE",
                "Salaire",
                salaire.id,
                ancienne=ancienne,
                nouvelle=str(salaire),
                description="Modification d'un salaire"
            )


            messages.success(

                request,

                "Salaire modifié avec succès."

            )


            return redirect(

                "salaire:salaire_list"

            )


    else:


        form = SalaireForm(
            instance=salaire
        )



    return render(

        request,

        "salaire/form.html",

        {

            "form": form,

            "action": "Modifier"

        }

    )





# ==========================
# SUPPRESSION
# ==========================

def salaire_delete(request, id):


    salaire = get_object_or_404(
        Salaire,
        id=id
    )


    if request.method == "POST":


        enregistrer_action(
            request,
            "DELETE",
            "Salaire",
            salaire.id,
            ancienne=str(salaire),
            description="Suppression d'un salaire"
        )


        salaire.delete()


        messages.success(

            request,

            "Salaire supprimé avec succès."

        )


    return redirect(

        "salaire:salaire_list"

    )