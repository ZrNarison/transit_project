from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django.forms import inlineformset_factory
from django.db import transaction
from .models import Depot, Distribution
from django.db.models import Sum
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
# LISTE
# ===============================
def depot_list(request):

    depots = Depot.objects.prefetch_related(
        "distributions__distributeur"
    )

    personnels = Personnel.objects.all()

    personnel = request.GET.get("personnel")
    date_debut = request.GET.get("date_debut")
    date_fin = request.GET.get("date_fin")

    if personnel:
        depots = depots.filter(
            distributions__distributeur_id=personnel
        ).distinct()

    if date_debut:
        depots = depots.filter(date__gte=date_debut)

    if date_fin:
        depots = depots.filter(date__lte=date_fin)

    # Total des dépôts
    total_montant = depots.aggregate(
        total=Sum("montantG")
    )["total"] or 0

    # Total distribué au personnel sélectionné
    total_personnel = 0

    if personnel:
        total_personnel = Distribution.objects.filter(
            distributeur_id=personnel
        )

        if date_debut:
            total_personnel = total_personnel.filter(
                depot__date__gte=date_debut
            )

        if date_fin:
            total_personnel = total_personnel.filter(
                depot__date__lte=date_fin
            )

        total_personnel = total_personnel.aggregate(
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
        },
    )

# ====================
# AJOUT
#=====
@transaction.atomic
def depot_add(request):
    if request.method == "POST":

        form = DepotForm(request.POST)

        formset = DistributionFormSet(
            request.POST
        )


        if form.is_valid() and formset.is_valid():
            depot = form.save()
            total = 0

            distributions = formset.save(
                commit=False
            )


            for distribution in distributions:

                total += distribution.montant



            if total > depot.montantG:

                messages.error(
                    request,
                    "Le total distribué dépasse le dépôt."
                )

                depot.delete()


            else:

                for distribution in distributions:

                    distribution.depot = depot
                    distribution.save()


                messages.success(
                    request,
                    "Dépôt enregistré avec succès."
                )


                return redirect(
                    'depot:depot_list'
                )


    else:
        form = DepotForm()
        formset = DistributionFormSet()
    return render(
        request,
        'depot/form.html',
        {
            'form': form,
            'formset': formset,
            'action': 'Ajouter'
        }
    )

#========================
#MODIFICATION
#=
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
            total = 0

            distributions = formset.save(
                commit=False
            )

            for distribution in distributions:
                total += distribution.montant
            if total > form.cleaned_data['montantG']:
                messages.error(
                    request,
                    "Le total distribué dépasse le montant du dépôt."
                )
            else:
                depot = form.save()
                # supprimer les lignes cochées
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
                    'depot:depot_list'
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
        'depot/form.html',
        {
            'form': form,
            'formset': formset,
            'action': 'Modifier'
        }
    )



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
        'depot:depot_list'
    )