from django import forms
from .models import MaterielEntre


class MaterielEntreForm(forms.ModelForm):
    class Meta:
        model = MaterielEntre
        fields = "__all__"

        widgets = {
            "id_Materiel": forms.Select(attrs={"class": "form-select"}),
            "id_MaterielSort": forms.Select(attrs={"class": "form-select"}),
            "Nb_Entre": forms.NumberInput(attrs={
                "class": "form-control",
                "min": 1,
            }),
        }