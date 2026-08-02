from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from .models import Depot


class DepotForm(forms.ModelForm):
    class Meta:
        model = Depot
        fields = ['nom', 'montant', 'personnel_1', 'personnel_2', 'part_1', 'part_2', 'description']
        widgets = {
            'nom': forms.TextInput(attrs={'class': 'form-control'}),
            'montant': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'personnel_1': forms.Select(attrs={'class': 'form-select'}),
            'personnel_2': forms.Select(attrs={'class': 'form-select'}),
            'part_1': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'part_2': forms.NumberInput(attrs={'class': 'form-control', 'min': '0'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def clean(self):
        cleaned_data = super().clean()
        montant = cleaned_data.get('montant')
        part_1 = cleaned_data.get('part_1')
        part_2 = cleaned_data.get('part_2')
        personnel_1 = cleaned_data.get('personnel_1')
        personnel_2 = cleaned_data.get('personnel_2')

        if montant is None:
            return cleaned_data

        has_part_1 = part_1 is not None and part_1 > 0
        has_part_2 = part_2 is not None and part_2 > 0

        if has_part_1 and not has_part_2 and personnel_1 and not personnel_2:
            if part_1 != montant:
                raise forms.ValidationError('Pour un seul personnel, corrigez la répartition : le montant attribué doit être exactement égal au montant du dépôt.')
            return cleaned_data

        if has_part_2 and not has_part_1 and personnel_2 and not personnel_1:
            if part_2 != montant:
                raise forms.ValidationError('Pour un seul personnel, corrigez la répartition : le montant attribué doit être exactement égal au montant du dépôt.')
            return cleaned_data

        if personnel_1 and personnel_2 and personnel_1 == personnel_2:
            cleaned_data['personnel_2'] = None

        if part_1 is not None and part_2 is not None:
            if part_1 + part_2 > montant:
                raise forms.ValidationError('La somme des montants répartis dépasse le montant du dépôt. Réduisez les parts ou corrigez le montant total.')
            if part_1 + part_2 < montant:
                raise forms.ValidationError('La somme des montants répartis est inférieure au montant du dépôt. Augmentez les parts ou corrigez le montant total.')

        return cleaned_data


def depot_list(request):
    queryset = Depot.objects.all()
    nom = request.GET.get('nom', '').strip()
    montant = request.GET.get('montant', '').strip()

    if nom:
        queryset = queryset.filter(nom__icontains=nom)
    if montant:
        queryset = queryset.filter(montant__icontains=montant)

    paginator = Paginator(queryset, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return render(request, 'depot/list.html', {'depots': page_obj.object_list, 'page_obj': page_obj, 'nom': nom, 'montant': montant})


def depot_add(request):
    if request.method == 'POST':
        form = DepotForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Dépôt ajouté avec succès.')
            return redirect('depot:depot_list')

        error_messages = []
        for field, errors in form.errors.items():
            if field == '__all__':
                error_messages.extend(errors)
            else:
                error_messages.extend([f"{field}: {error}" for error in errors])

        if error_messages:
            messages.error(request, 'Erreur de validation : ' + ' | '.join(error_messages))
        else:
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

        error_messages = []
        for field, errors in form.errors.items():
            if field == '__all__':
                error_messages.extend(errors)
            else:
                error_messages.extend([f"{field}: {error}" for error in errors])

        if error_messages:
            messages.error(request, 'Erreur de validation : ' + ' | '.join(error_messages))
        else:
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
