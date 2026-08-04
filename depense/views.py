from decimal import Decimal
from django.shortcuts import (render, redirect,get_object_or_404)
from django.db.models import Sum
from django.contrib import messages
from .models import Depense
from .forms import DepenseForm
from depot.models import Distribution
from personnel.models import Personnel
from users.models import AppUser
from django.utils import timezone
from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404

from .forms import DepenseForm
from .models import Depense


def depense_list(request):

    queryset = Depense.objects.select_related(
        'distribution',
        'enregistre_par'
    ).all()


    titre = request.GET.get(
        'titre',
        ''
    ).strip()


    montant = request.GET.get(
        'montant',
        ''
    ).strip()



    if titre:

        queryset = queryset.filter(
            titre__icontains=titre
        )


    if montant:

        queryset = queryset.filter(
            montant__icontains=montant
        )


    return render(
        request,
        'depense/list.html',
        {
            'depenses': queryset,
            'titre': titre,
            'montant': montant
        }
    )

def depense_add(request):

    if request.method == "POST":

        form = DepenseForm(request.POST)


        if form.is_valid():

            depense = form.save(commit=False)


            # ==========================
            # Enregistreur connecté
            # ==========================

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



            # ==========================
            # Date de la dépense
            # ==========================

            date_depense = timezone.now().date()



            # ==========================
            # GEGE
            # ==========================

            gege = Personnel.objects.get(
                id=1
            )



            # ==========================
            # Distribution disponible
            # avant la date dépense
            # ==========================

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



                # ==========================
                # Cas normal
                # ==========================

                if montant_restant <= disponible:


                    depense.distribution = distribution

                    depense.montant = montant_restant

                    depense.save()


                    montant_restant = Decimal("0")

                    break



                # ==========================
                # Dépasse une distribution
                # ==========================

                else:


                    depense.distribution = distribution

                    depense.montant = disponible

                    depense.save()



                    montant_restant -= disponible



            # ==========================
            # Pas assez d'argent
            # ==========================

            if montant_restant > 0:


                messages.error(
                    request,
                    "GEGE n'a pas le montant disponible."
                )


                return redirect(
                    "depense:depense_add"
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


def depense_edit(request, id):

    depense = get_object_or_404(
        Depense,
        id=id
    )


    if request.method == "POST":

        form = DepenseForm(
            request.POST,
            instance=depense
        )


        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Dépense modifiée avec succès."
            )

            return redirect(
                'depense:depense_list'
            )


    else:

        form = DepenseForm(
            instance=depense
        )


    return render(
        request,
        'depense/form.html',
        {
            'form': form,
            'action': 'Modifier'
        }
    )



def depense_delete(request, id):

    depense = get_object_or_404(
        Depense,
        id=id
    )


    if request.method == "POST":

        depense.delete()

        messages.success(
            request,
            "Dépense supprimée avec succès."
        )


    return redirect(
        'depense:depense_list'
    )


