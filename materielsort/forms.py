from django import forms
from .models import MaterielSort


class MaterielSortForm(forms.ModelForm):
    class Meta:
        model = MaterielSort
        fields = "__all__"

        widgets = {
            "id_Materiel": forms.Select(attrs={"class": "form-select"}),
            "Nb_MatSort": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1,
            }),
        }