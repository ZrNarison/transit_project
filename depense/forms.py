from django import forms

from depot.models import Depot
from .models import Depense


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

            total_depot_amount = Depot.objects.aggregate(total=Sum('montant'))['total'] or 0
            qs = Depense.objects.filter(depot=depot)
            if self.instance and self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            total_depenses_for_depot = qs.aggregate(total=Sum('montant'))['total'] or 0

            remaining = total_depot_amount - total_depenses_for_depot
            if montant > remaining:
                try:
                    remaining_display = f"{int(remaining):,}"
                except Exception:
                    remaining_display = str(remaining)
                msg = f"Dépense disponible est de {remaining_display} Ar"
                self.add_error('montant', msg)
        return cleaned
