from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404

from .forms import DepenseForm
from .models import Depense


def depense_list(request):
    queryset = Depense.objects.all()
    titre = request.GET.get('titre', '').strip()
    montant = request.GET.get('montant', '').strip()

    if titre:
        queryset = queryset.filter(titre__icontains=titre)
    if montant:
        queryset = queryset.filter(montant__icontains=montant)

    paginator = Paginator(queryset, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    query_params = request.GET.copy()
    query_params.pop('page', None)
    return render(request, 'depense/list.html', {'depenses': page_obj.object_list, 'page_obj': page_obj, 'query_params': query_params.urlencode(), 'titre': titre, 'montant': montant})


def depense_add(request):
    if request.method == 'POST':
        form = DepenseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dépense ajoutée avec succès.')
            return redirect('depense:depense_list')
        # If montant field has a specific error (surplus), surface it as a notification
        montant_errors = form.errors.get('montant')
        if montant_errors:
            messages.error(request, montant_errors[0])
        else:
            messages.error(request, 'Impossible d’ajouter la dépense. Vérifiez les informations.')
    else:
        form = DepenseForm()
    return render(request, 'depense/form.html', {'form': form, 'action': 'Ajouter'})


def depense_edit(request, id):
    depense = get_object_or_404(Depense, id=id)
    if request.method == 'POST':
        form = DepenseForm(request.POST, instance=depense)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dépense modifiée avec succès.')
            return redirect('depense:depense_list')
        montant_errors = form.errors.get('montant')
        if montant_errors:
            messages.error(request, montant_errors[0])
        else:
            messages.error(request, 'Impossible de modifier la dépense. Vérifiez les informations.')
    else:
        form = DepenseForm(instance=depense)
    return render(request, 'depense/form.html', {'form': form, 'action': 'Modifier'})


def depense_delete(request, id):
    depense = Depense.objects.filter(id=id).first()
    if depense is None:
        messages.warning(request, 'Cette dépense n’existe plus.')
        return redirect('depense:depense_list')

    if request.method == 'POST':
        depense.delete()
        messages.success(request, 'Dépense supprimée avec succès.')
        return redirect('depense:depense_list')

    messages.info(request, 'Veuillez confirmer la suppression depuis la liste.')
    return redirect('depense:depense_list')
