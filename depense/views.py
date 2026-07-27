from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from .models import Depense
from depot.models import Depot


class DepenseForm(forms.ModelForm):
    class Meta:
        model = Depense
        fields = ['titre', 'depot', 'montant', 'description']
        widgets = {
            'titre': forms.TextInput(attrs={'class': 'form-control'}),
            'depot': forms.Select(attrs={'class': 'form-select'}),
            'montant': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['depot'].queryset = Depot.objects.order_by('nom')
        self.fields['depot'].required = True

    def clean(self):
        cleaned = super().clean()
        depot = cleaned.get('depot')
        montant = cleaned.get('montant')
        if depot and montant is not None:
            from django.db.models import Sum
            qs = Depense.objects.filter(depot=depot)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            total = qs.aggregate(total=Sum('montant'))['total'] or 0
            remaining = depot.montant - total
            if montant > remaining:
                # Simple, clear message showing only remaining available amount
                try:
                    remaining_display = f"{int(remaining):,}"
                except Exception:
                    remaining_display = str(remaining)
                msg = f"Dépense disponible est de {remaining_display} Ar"
                self.add_error('montant', msg)
        return cleaned


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
    depense = get_object_or_404(Depense, id=id)
    if request.method == 'POST':
        depense.delete()
        messages.success(request, 'Dépense supprimée avec succès.')
        return redirect('depense:depense_list')
    messages.info(request, 'Veuillez confirmer la suppression depuis la liste.')
    return redirect('depense:depense_list')
