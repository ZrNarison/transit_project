from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from personnel.models import Personnel
from .models import Salaire


class SalaireForm(forms.ModelForm):
    class Meta:
        model = Salaire
        fields = ['personnel', 'montant']
        widgets = {
            'personnel': forms.Select(attrs={'class': 'form-select'}),
            'montant': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['personnel'].queryset = Personnel.objects.order_by('nom', 'prenom')
        self.fields['personnel'].required = False
        self.fields['personnel'].empty_label = 'Journey'


from django.db.models import Q


def salaire_list(request):
    queryset = Salaire.objects.all()
    personnel = request.GET.get('personnel', '').strip()
    montant = request.GET.get('montant', '').strip()
    if personnel:
        queryset = queryset.filter(
            Q(personnel__nom__icontains=personnel) |
            Q(personnel__prenom__icontains=personnel)
        )
    if montant:
        queryset = queryset.filter(montant__icontains=montant)
    salaires = queryset
    return render(request, 'salaire/list.html', {'salaires': salaires, 'personnel': personnel, 'montant': montant})


def salaire_add(request):
    if request.method == 'POST':
        form = SalaireForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Salaire ajouté avec succès.')
            return redirect('salaire:salaire_list')
        messages.error(request, 'Impossible d’ajouter le salaire. Vérifiez les informations.')
    else:
        form = SalaireForm()
    return render(request, 'salaire/form.html', {'form': form, 'action': 'Ajouter'})


def salaire_edit(request, id):
    salaire = get_object_or_404(Salaire, id=id)
    if request.method == 'POST':
        form = SalaireForm(request.POST, instance=salaire)
        if form.is_valid():
            form.save()
            messages.success(request, 'Salaire modifié avec succès.')
            return redirect('salaire:salaire_list')
        messages.error(request, 'Impossible de modifier le salaire. Vérifiez les informations.')
    else:
        form = SalaireForm(instance=salaire)
    return render(request, 'salaire/form.html', {'form': form, 'action': 'Modifier'})


def salaire_delete(request, id):
    salaire = get_object_or_404(Salaire, id=id)
    if request.method == 'POST':
        salaire.delete()
        messages.success(request, 'Salaire supprimé avec succès.')
        return redirect('salaire:salaire_list')
    messages.info(request, 'Veuillez confirmer la suppression depuis la liste.')
    return redirect('salaire:salaire_list')
