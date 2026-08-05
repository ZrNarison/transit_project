from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib import messages
from django.db.models import Q

from .models import Retour
from .forms import RetourForm

from audit.utils import enregistrer_action



# ==========================================
# LISTE
# ==========================================
def retour_list(request):

    queryset = Retour.objects.all()

    montant = request.GET.get("montant", "").strip()

    if montant:
        queryset = queryset.filter(
            montant__icontains=montant
        )

    context = {
        "retours": queryset,
        "montant": montant,
    }

    return render(
        request,
        "retours/list.html",
        context
    )



# ==========================================
# DETAIL
# ==========================================
def retour_detail(request, id):

    retour = get_object_or_404(
        Retour,
        id=id
    )

    return render(
        request,
        "retours/detail.html",
        {
            "retour": retour
        }
    )



# ==========================================
# AJOUT
# ==========================================
def retour_add(request):

    if request.method == "POST":

        form = RetourForm(request.POST)

        if form.is_valid():

            retour = form.save(commit=False)

            user_id = request.session.get("user_id")

            if user_id:
                from users.models import AppUser
                retour.enregistrer_par = AppUser.objects.get(
                    id=user_id
                )

            retour.save()


            enregistrer_action(
                request,
                "CREATE",
                "Retour",
                retour.id,
                nouvelle={
                    "montant": str(retour.montant)
                },
                description="Création d'un retour"
            )


            messages.success(
                request,
                "Retour enregistré avec succès."
            )

            return redirect(
                "retours:retour_list"
            )

    else:
        form = RetourForm()


    return render(
        request,
        "retours/form.html",
        {
            "form": form,
            "action": "Ajouter"
        }
    )



# ==========================================
# MODIFICATION
# ==========================================
def retour_edit(request, id):

    retour = get_object_or_404(
        Retour,
        id=id
    )


    ancienne = str(retour)


    if request.method == "POST":

        form = RetourForm(
            request.POST,
            instance=retour
        )

        if form.is_valid():

            retour = form.save()


            enregistrer_action(
                request,
                "UPDATE",
                "Retour",
                retour.id,
                ancienne=ancienne,
                nouvelle=str(retour),
                description="Modification d'un retour"
            )


            messages.success(
                request,
                "Retour modifié avec succès."
            )

            return redirect(
                "retours:retour_list"
            )

    else:

        form = RetourForm(
            instance=retour
        )

    return render(
        request,
        "retours/form.html",
        {
            "form": form,
            "action": "Modifier"
        }
    )



# ==========================================
# SUPPRESSION
# ==========================================
def retour_delete(request, id):

    retour = get_object_or_404(
        Retour,
        id=id
    )


    if request.method == "POST":


        enregistrer_action(
            request,
            "DELETE",
            "Retour",
            retour.id,
            ancienne=str(retour),
            description="Suppression d'un retour"
        )


        retour.delete()


        messages.success(
            request,
            "Retour supprimé avec succès."
        )

        return redirect(
            "retours:retour_list"
        )


    return render(
        request,
        "retours/confirm.html",
        {
            "retour": retour
        }
    )