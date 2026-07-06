from django import forms
from .models import Materiels


class MaterielsForm(forms.ModelForm):

    class Meta:
        model = Materiels
        fields = [
            "nom",
            "typeMat",
            "catMat",
            "stock_initial"
        ]

        widgets = {
            "nom": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nom du matériel"
            }),

            "typeMat": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Type matériel"
            }),

            "catMat": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Catégorie"
            }),

            "stock_initial": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Stock initial"
            }),
        }