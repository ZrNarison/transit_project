from django import forms
from .models import Depense


class DepenseForm(forms.ModelForm):

    class Meta:

        model = Depense

        fields = [
            "titre",
            "montant",
            "description",
        ]

        widgets = {

            "titre": forms.TextInput(
                attrs={
                    "class": "form-select"
                }
            ),

            "montant": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "1"
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3
                }
            ),
        }