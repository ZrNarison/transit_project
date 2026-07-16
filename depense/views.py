from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from .models import Depense


class DepenseForm(forms.ModelForm):
    class Meta:
        model = Depense
        fields = ['titre', 'montant', 'description']
        widgets = {
            'titre': forms.TextInput(attrs={'class': 'form-control'}),
            'montant': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }


def depense_list(request):
    queryset = Depense.objects.all()
    titre = request.GET.get('titre', '').strip()
    montant = request.GET.get('montant', '').strip()

    if titre:
        queryset = queryset.filter(titre__icontains=titre)
    if montant:
        queryset = queryset.filter(montant__icontains=montant)

    depenses = queryset
    return render(request, 'depense/list.html', {'depenses': depenses, 'titre': titre, 'montant': montant})


def depense_add(request):
    if request.method == 'POST':
        form = DepenseForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dépense ajoutée avec succès.')
            return redirect('depense:depense_list')
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
        messages.error(request, 'Impossible de modifier la dépense. Vérifiez les informations.')
    else:
        form = DepenseForm(instance=depense)
    return render(request, 'depense/form.html', {'form': form, 'action': 'Modifier'})


def depense_delete(request, id):
    depense = get_object_or_404(Depense, id=id)
    if request.method == 'POST':
        depense.delete()
        messages.success(request, 'Dépense supprimée avec succès.')
        return redirect('depense:depense_list')
    messages.info(request, 'Veuillez confirmer la suppression depuis la liste.')
    return redirect('depense:depense_list')
