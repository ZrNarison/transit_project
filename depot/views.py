from decimal import Decimal

from django.contrib import messages
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)
from django.forms import inlineformset_factory
from django.db import transaction
from django.db.models import Sum
from .models import Depot, Distribution
from .forms import DepotForm, DistributionForm
from personnel.models import Personnel

# =====================================================
# FORMSET DISTRIBUTION
# =====================================================

DistributionFormSet = inlineformset_factory(
    Depot,
    Distribution,
    form=DistributionForm,
    extra=2,
    can_delete=True
)
from audit.utils import enregistrer_action



# =====================================================
# LISTE DEPOTS
# =====================================================

def depot_list(request):

    depots = (
        Depot.objects
        .prefetch_related(
            "distributions__distributeur"
        )
        .order_by("-date")
    )


    personnels = Personnel.objects.all()


    personnel = request.GET.get(
        "personnel"
    )

    date_debut = request.GET.get(
        "date_debut"
    )

    date_fin = request.GET.get(
        "date_fin"
    )



    if personnel in ("", None):

        personnel = None


    if date_debut in ("", None):

        date_debut = None


    if date_fin in ("", None):

        date_fin = None




    # Filtre personnel

    if personnel:

        depots = depots.filter(
            distributions__distributeur_id=personnel
        ).distinct()



    # Filtre dates

    if date_debut:

        depots = depots.filter(
            date__gte=date_debut
        )


    if date_fin:

        depots = depots.filter(
            date__lte=date_fin
        )




    total_montant = (
        depots.aggregate(
            total=Sum("montantG")
        )["total"]
        or Decimal("0")
    )



    total_personnel = (
        Distribution.objects
        .filter(
            depot__in=depots
        )
        .aggregate(
            total=Sum("montant")
        )["total"]
        or Decimal("0")
    )



    return render(
        request,
        "depot/list.html",
        {
            "depots": depots,
            "personnels": personnels,
            "personnel": personnel,
            "date_debut": date_debut,
            "date_fin": date_fin,

            "total_montant": total_montant,
            "total_personnel": total_personnel,
        }
    )





# =====================================================
# IMPRESSION
# =====================================================

def depot_print(request):

    depots = Depot.objects.prefetch_related(
        "distributions__distributeur"
    )


    personnel = request.GET.get("personnel")
    date_debut = request.GET.get("date_debut")
    date_fin = request.GET.get("date_fin")


    # Correction None venant du template
    if personnel in ["", "None", None]:
        personnel = None

    if date_debut in ["", "None", None]:
        date_debut = None

    if date_fin in ["", "None", None]:
        date_fin = None



    if personnel:

        depots = depots.filter(
            distributions__distributeur_id=int(personnel)
        ).distinct()



    if date_debut:

        depots = depots.filter(
            date__gte=date_debut
        )



    if date_fin:

        depots = depots.filter(
            date__lte=date_fin
        )



    total_montant = depots.aggregate(
        total=Sum("montantG")
    )["total"] or 0



    total_distribution = Distribution.objects.filter(
        depot__in=depots
    ).aggregate(
        total=Sum("montant")
    )["total"] or 0



    return render(
        request,
        "depot/print.html",
        {
            "depots": depots,
            "date_debut": date_debut,
            "date_fin": date_fin,
            "total_montant": total_montant,
            "total_distribution": total_distribution,
        }
    )
# =====================================================
# AJOUT
# =====================================================

@transaction.atomic
def depot_add(request):


    if request.method == "POST":

        form = DepotForm(
            request.POST
        )

        formset = DistributionFormSet(
            request.POST
        )



        if form.is_valid() and formset.is_valid():


            depot = form.save(
                commit=False
            )


            distributions = formset.save(
                commit=False
            )


            total = sum(
                d.montant
                for d in distributions
            )



            if total > depot.montantG:


                messages.error(
                    request,
                    "La distribution dépasse le montant du dépôt."
                )


            else:

                depot.save()



                for distribution in distributions:

                    distribution.depot = depot
                    distribution.save()

                enregistrer_action(
                                    request,
                                    "CREATE",
                                    "Depot",
                                    depot.id,
                                    nouvelle={
                                        "montant": str(depot.montantG),
                                        "date": str(depot.date)
                                    },
                                    description="Création d'un dépôt"
                                )

                enregistrer_action(
                                    request,
                                    "CREATE",
                                    "Depot",
                                    depot.id,
                                    nouvelle={
                                        "montant": str(depot.montantG),
                                        "date": str(depot.date)
                                    },
                                    description="Création d'un dépôt"
                                )
                messages.success(
                    request,
                    "Dépôt ajouté avec succès."
                )


                return redirect(
                    "depot:depot_list"
                )



    else:

        form = DepotForm()

        formset = DistributionFormSet()



    return render(
        request,
        "depot/form.html",
        {
            "form": form,
            "formset": formset,
            "action": "Ajouter"
        }
    )





# =====================================================
# MODIFICATION
# =====================================================

@transaction.atomic
def depot_edit(request, id):

    depot = get_object_or_404(
        Depot,
        id=id
    )



    if request.method == "POST":


        form = DepotForm(
            request.POST,
            instance=depot
        )


        formset = DistributionFormSet(
            request.POST,
            instance=depot
        )



        if form.is_valid() and formset.is_valid():


            depot = form.save()



            for obj in formset.deleted_objects:

                obj.delete()



            distributions = formset.save(
                commit=False
            )



            for distribution in distributions:

                distribution.depot = depot
                distribution.save()

                enregistrer_action(
                                    request,
                                    "UPDATE",
                                    "Depot",
                                    depot.id,
                                    nouvelle={
                                        "montant": str(depot.montantG),
                                        "date": str(depot.date)
                                    },
                                    description="Modification d'un dépôt"
                                )

            messages.success(
                request,
                "Dépôt modifié."
            )


            return redirect(
                "depot:depot_list"
            )



    else:

        form = DepotForm(
            instance=depot
        )


        formset = DistributionFormSet(
            instance=depot
        )



    return render(
        request,
        "depot/form.html",
        {
            "form": form,
            "formset": formset,
            "action": "Modifier"
        }
    )





# =====================================================
# SUPPRESSION
# =====================================================

def depot_delete(request, id):

    depot = get_object_or_404(
        Depot,
        id=id
    )


    if request.method == "POST":


        depot.delete()
        enregistrer_action(
    request,
    "DELETE",
    "Depot",
    depot.id,
    ancienne={
        "montant": str(depot.montantG),
        "date": str(depot.date)
    },
    description="Suppression d'un dépôt"
)

        messages.success(
            request,
            "Dépôt supprimé avec succès."
        )


    return redirect(
        "depot:depot_list"
    )