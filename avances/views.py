from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.db.models import Q
from django.contrib import messages

from .forms import AvanceForm
from .models import Avance

from users.models import AppUser

from audit.utils import enregistrer_action



# ==========================================
# AJOUT
# ==========================================

def avance_add(request):

    if request.method == "POST":

        form = AvanceForm(request.POST)

        if form.is_valid():

            avance = form.save(commit=False)


            user_id = request.session.get(
                "user_id"
            )


            if user_id:

                try:

                    avance.enregistre_par = AppUser.objects.get(
                        id=user_id
                    )

                except AppUser.DoesNotExist:

                    avance.enregistre_par = None



            avance.save()



            enregistrer_action(
                request,
                "CREATE",
                "Avance",
                avance.id,
                nouvelle={
                    "personnel": str(avance.personnel),
                    "montant": str(avance.montantAv),
                    "motif": avance.motifAv,
                    "type": avance.typeAv
                },
                description="Création d'une avance personnel"
            )



            messages.success(
                request,
                "Avance enregistrée avec succès."
            )


            return redirect(
                "avances:avance_list"
            )


    else:

        form = AvanceForm()



    return render(
        request,
        "avances/form.html",
        {
            "form": form
        }
    )





# ==========================================
# LISTE
# ==========================================

def avance_list(request):

    avances = Avance.objects.select_related(
        "personnel",
        "distribution",
        "enregistre_par"
    ).all()



    recherche = request.GET.get(
        "personnel",
        ""
    ).strip()



    date = request.GET.get(
        "date",
        ""
    ).strip()



    if recherche:

        avances = avances.filter(

            Q(personnel__nom__icontains=recherche)

            |

            Q(personnel__prenom__icontains=recherche)

        )



    if date:

        avances = avances.filter(
            dateAv__date=date
        )



    return render(
        request,
        "avances/list.html",
        {
            "avances": avances,
            "personnel": recherche,
            "date": date
        }
    )





# ==========================================
# DETAIL
# ==========================================

def avance_detail(request, id):

    avance = get_object_or_404(
        Avance,
        id=id
    )


    enregistrer_action(
        request,
        "VIEW",
        "Avance",
        id,
        description="Consultation détail avance personnel"
    )



    return render(
        request,
        "avances/detail.html",
        {
            "avance": avance
        }
    )





# ==========================================
# MODIFICATION
# ==========================================

def avance_edit(request, id):

    avance = get_object_or_404(
        Avance,
        id=id
    )


    user_id = request.session.get(
        "user_id"
    )



    if not user_id or avance.enregistre_par_id != int(user_id):

        messages.error(
            request,
            "Vous ne pouvez pas modifier cette avance."
        )

        return redirect(
            "avances:avance_list"
        )



    ancienne = {

        "personnel": str(avance.personnel),

        "montant": str(avance.montantAv),

        "motif": avance.motifAv,

        "type": avance.typeAv

    }



    if request.method == "POST":


        form = AvanceForm(
            request.POST,
            instance=avance
        )


        if form.is_valid():


            avance_modifiee = form.save()



            nouvelle = {

                "personnel": str(avance_modifiee.personnel),

                "montant": str(avance_modifiee.montantAv),

                "motif": avance_modifiee.motifAv,

                "type": avance_modifiee.typeAv

            }



            enregistrer_action(
                request,
                "UPDATE",
                "Avance",
                id,
                ancienne=ancienne,
                nouvelle=nouvelle,
                description="Modification d'une avance personnel"
            )



            messages.success(
                request,
                "Avance modifiée avec succès."
            )


            return redirect(
                "avances:avance_list"
            )



    else:

        form = AvanceForm(
            instance=avance
        )



    return render(
        request,
        "avances/form.html",
        {
            "form": form
        }
    )






# ==========================================
# SUPPRESSION
# ==========================================

def avance_delete(request, id):


    avance = get_object_or_404(
        Avance,
        id=id
    )


    user_id = request.session.get(
        "user_id"
    )



    if not user_id or avance.enregistre_par_id != int(user_id):

        messages.error(
            request,
            "Vous ne pouvez pas supprimer cette avance."
        )

        return redirect(
            "avances:avance_list"
        )



    ancienne = {

        "personnel": str(avance.personnel),

        "montant": str(avance.montantAv),

        "motif": avance.motifAv,

        "type": avance.typeAv

    }



    if request.method == "POST":


        enregistrer_action(
            request,
            "DELETE",
            "Avance",
            id,
            ancienne=ancienne,
            description="Suppression d'une avance personnel"
        )



        avance.delete()



        messages.success(
            request,
            "Avance supprimée avec succès."
        )



    return redirect(
        "avances:avance_list"
    )