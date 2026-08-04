from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.forms import inlineformset_factory
from django.db import transaction
from django.db.models import Sum

from .models import Depot, Distribution
from .forms import DepotForm, DistributionForm
from personnel.models import Personnel


DistributionFormSet = inlineformset_factory(
    Depot,
    Distribution,
    form=DistributionForm,
    extra=2,
    can_delete=True
)


# =====================================================
# LISTE DES DEPOTS
# =====================================================

def depot_list(request):

    depots = Depot.objects.prefetch_related(
        "distributions__distributeur"
    )

    personnels = Personnel.objects.all()

    personnel = request.GET.get("personnel")
    date_debut = request.GET.get("date_debut")
    date_fin = request.GET.get("date_fin")


    # Correction valeur None
    if personnel in ["", "None"]:
        personnel = None

    if date_debut in ["", "None"]:
        date_debut = None

    if date_fin in ["", "None"]:
        date_fin = None



    if personnel:

        depots = depots.filter(
            distributions__distributeur_id=personnel
        ).distinct()



    if date_debut:

        depots = depots.filter(
            date__gte=date_debut
        )


    if date_fin:

        depots = depots.filter(
            date__lte=date_fin
        )



    # Total dépôt

    total_montant = depots.aggregate(
        total=Sum("montantG")
    )["total"] or 0



    # Total distribution

    distributions = Distribution.objects.all()


    if personnel:

        distributions = distributions.filter(
            distributeur_id=personnel
        )


    if date_debut:

        distributions = distributions.filter(
            depot__date__gte=date_debut
        )


    if date_fin:

        distributions = distributions.filter(
            depot__date__lte=date_fin
        )



    total_personnel = distributions.aggregate(
        total=Sum("montant")
    )["total"] or 0



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



    # Protection None

    if personnel in ["", "None"]:
        personnel = None


    if date_debut in ["", "None"]:
        date_debut = None


    if date_fin in ["", "None"]:
        date_fin = None



    if personnel:

        depots = depots.filter(
            distributions__distributeur_id=personnel
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

        form = DepotForm(request.POST)

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
                d.montant for d in distributions
            )



            if total > depot.montantG:

                messages.error(
                    request,
                    "Le total distribué dépasse le dépôt."
                )


            else:

                depot.save()


                for distribution in distributions:

                    distribution.depot = depot
                    distribution.save()



                messages.success(
                    request,
                    "Dépôt enregistré avec succès."
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

            distributions = formset.save(
                commit=False
            )


            total = sum(
                d.montant for d in distributions
            )



            if total > form.cleaned_data["montantG"]:

                messages.error(
                    request,
                    "Le total distribué dépasse le montant du dépôt."
                )


            else:

                depot = form.save()



                for obj in formset.deleted_objects:

                    obj.delete()



                for distribution in distributions:

                    distribution.depot = depot
                    distribution.save()



                messages.success(
                    request,
                    "Dépôt modifié avec succès."
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


        messages.success(
            request,
            "Dépôt supprimé avec succès."
        )


    return redirect(
        "depot:depot_list"
    )