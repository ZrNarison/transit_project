from django import forms
from .models import Retour


class RetourForm(forms.ModelForm):

    class Meta:
        model = Retour

        fields = [
            "montant",
        ]

        widgets = {

            "montant": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Montant du retour"
                }
            ),

        }

        labels = {

            "montant": "Montant",

        }