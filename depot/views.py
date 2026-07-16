from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from .models import Depot


class DepotForm(forms.ModelForm):
    class Meta:
        model = Depot
        fields = ['nom', 'montant', 'description']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'montant': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


def depot_list(request):
    queryset = Depot.objects.all()
    nom = request.GET.get('nom', '').strip()
    montant = request.GET.get('montant', '').strip()

    if nom:
        queryset = queryset.filter(nom__icontains=nom)
    if montant:
        queryset = queryset.filter(montant__icontains=montant)

    depots = queryset
    return render(request, 'depot/list.html', {'depots': depots, 'nom': nom, 'montant': montant})


def depot_add(request):
    if request.method == 'POST':
        form = DepotForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dépôt ajouté avec succès.')
            return redirect('depot:depot_list')
        messages.error(request, 'Impossible d’ajouter le dépôt. Vérifiez les informations.')
    else:
        form = DepotForm()
    return render(request, 'depot/form.html', {'form': form, 'action': 'Ajouter'})


def depot_edit(request, id):
    depot = get_object_or_404(Depot, id=id)
    if request.method == 'POST':
        form = DepotForm(request.POST, instance=depot)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dépôt modifié avec succès.')
            return redirect('depot:depot_list')
        messages.error(request, 'Impossible de modifier le dépôt. Vérifiez les informations.')
    else:
        form = DepotForm(instance=depot)
    return render(request, 'depot/form.html', {'form': form, 'action': 'Modifier'})


def depot_delete(request, id):
    depot = get_object_or_404(Depot, id=id)
    if request.method == 'POST':
        depot.delete()
        messages.success(request, 'Dépôt supprimé avec succès.')
        return redirect('depot:depot_list')
    messages.info(request, 'Veuillez confirmer la suppression depuis la liste.')
    return redirect('depot:depot_list')
