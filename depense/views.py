from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from .models import Depense
from .forms import DepenseForm



def depense_list(request):

    queryset = Depense.objects.select_related(
        'depot'
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

        form = DepenseForm(
            request.POST
        )


        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Dépense ajoutée avec succès."
            )

            return redirect(
                'depense:depense_list'
            )


    else:

        form = DepenseForm()



    return render(
        request,
        'depense/form.html',
        {
            'form': form,
            'action': 'Ajouter'
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