from decimal import Decimal

from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.db.models import Sum
from django.contrib import messages
from django.core.paginator import Paginator
from django.utils import timezone

from .models import Depense
from .forms import DepenseForm

from depot.models import Distribution
from personnel.models import Personnel
from users.models import AppUser

from audit.utils import enregistrer_action



# ==========================================
# LISTE
# ==========================================

def depense_list(request):

    queryset = Depense.objects.select_related(
        "distribution",
        "enregistre_par"
    ).all()


    titre = request.GET.get(
        "titre",
        ""
    ).strip()


    montant = request.GET.get(
        "montant",
        ""
    ).strip()



    if titre:

        queryset = queryset.filter(
            titre__icontains=titre
        )


    if montant:

        queryset = queryset.filter(
            montant__icontains=montant
        )



    paginator = Paginator(
        queryset,
        10
    )


    page_obj = paginator.get_page(
        request.GET.get("page")
    )



    return render(
        request,
        "depense/list.html",
        {
            "depenses": page_obj,
            "page_obj": page_obj,
            "titre": titre,
            "montant": montant
        }
    )



# ==========================================
# AJOUT
# ==========================================

def depense_add(request):

    if request.method == "POST":

        form = DepenseForm(
            request.POST
        )


        if form.is_valid():

            depense = form.save(
                commit=False
            )


            # =========================
            # Utilisateur connecté
            # =========================

            user_id = request.session.get(
                "user_id"
            )


            if user_id:

                try:

                    depense.enregistre_par = AppUser.objects.get(
                        id=user_id
                    )

                except AppUser.DoesNotExist:

                    depense.enregistre_par = None



            date_depense = timezone.now().date()



            # =========================
            # GEGE
            # =========================

            gege = Personnel.objects.get(
                id=1
            )



            distributions = Distribution.objects.filter(

                distributeur=gege,

                depot__date__lte=date_depense

            ).order_by(
                "depot__date"
            )



            montant_restant = depense.montant



            for distribution in distributions:


                deja_depense = distribution.depenses.aggregate(
                    total=Sum("montant")
                )["total"] or Decimal("0")



                disponible = (
                    distribution.montant
                    -
                    deja_depense
                )



                if disponible <= 0:

                    continue



                if montant_restant <= disponible:


                    depense.distribution = distribution

                    depense.montant = montant_restant

                    depense.save()


                    montant_restant = Decimal("0")

                    break



                else:


                    depense.distribution = distribution

                    depense.montant = disponible

                    depense.save()


                    montant_restant -= disponible




            if montant_restant > 0:


                messages.error(
                    request,
                    "Montant disponible insuffisant."
                )


                return redirect(
                    "depense:depense_add"
                )



            # =========================
            # AUDIT CREATE
            # =========================

            enregistrer_action(
                request,
                action="CREATE",
                table="Depense",
                objet_id=depense.id,
                nouvelle={
                    "titre": depense.titre,
                    "montant": str(depense.montant),
                    "description": depense.description
                },

                description="Création d'une dépense"

            )



            messages.success(
                request,
                "Dépense enregistrée avec succès."
            )


            return redirect(
                "depense:depense_list"
            )



    else:

        form = DepenseForm()



    return render(
        request,
        "depense/form.html",
        {
            "form": form
        }
    )



# ==========================================
# MODIFICATION
# ==========================================

def depense_edit(request, id):

    depense = get_object_or_404(
        Depense,
        id=id
    )


    user_id = request.session.get(
        "user_id"
    )


    if not user_id or depense.enregistre_par_id != int(user_id):

        messages.error(
            request,
            "Vous ne pouvez pas modifier cette dépense."
        )


        return redirect(
            "depense:depense_list"
        )



    ancienne = {

        "titre": depense.titre,

        "montant": str(depense.montant),

        "description": depense.description

    }



    if request.method == "POST":


        form = DepenseForm(
            request.POST,
            instance=depense
        )


        if form.is_valid():


            depense = form.save()



            nouvelle = {

                "titre": depense.titre,

                "montant": str(depense.montant),

                "description": depense.description

            }



            enregistrer_action(
                request,

                action="CREATE",

                table="Depense",

                objet_id=depense.id,

                nouvelle={
                    "titre": depense.titre,
                    "montant": str(depense.montant),
                    "description": depense.description
                },

                description="Création d'une dépense"
            )



            messages.success(
                request,
                "Dépense modifiée avec succès."
            )


            return redirect(
                "depense:depense_list"
            )



    else:


        form = DepenseForm(
            instance=depense
        )



    return render(

        request,

        "depense/form.html",

        {

            "form": form,

            "action": "Modifier"

        }

    )



# ==========================================
# SUPPRESSION
# ==========================================

def depense_delete(request, id):

    depense = get_object_or_404(
        Depense,
        id=id
    )



    user_id = request.session.get(
        "user_id"
    )



    if not user_id or depense.enregistre_par_id != int(user_id):

        messages.error(
            request,
            "Vous ne pouvez pas supprimer cette dépense."
        )


        return redirect(
            "depense:depense_list"
        )



    if request.method == "POST":



        ancienne = {

            "titre": depense.titre,

            "montant": str(depense.montant),

            "description": depense.description

        }

        depense.delete()

        enregistrer_action(
        
                    request,
        
                    action="DELETE",
        
                    module="Dépense",
        
                    objet_id=depense.id,
        
                    ancienne=ancienne,
        
                    nouvelle=None,
        
                    description="Suppression d'une dépense"
        
                )

        messages.success(

            request,

            "Dépense supprimée avec succès."

        )



    return redirect(
        "depense:depense_list"
    )