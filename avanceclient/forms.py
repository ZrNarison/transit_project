from django import forms
from decimal import Decimal

from .models import AvanceClient
from clients.models import Client


class AvanceClientForm(forms.ModelForm):

    class Meta:

        model = AvanceClient

        fields = [
            "client",
            "montant",
            "type_avance",
            "motif",
        ]


        widgets = {

            "client": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),


            "montant": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Montant de l'avance",
                    "min": "0"
                }
            ),


            "type_avance": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),


            "motif": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Motif de l'avance"
                }
            ),

        }



    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)


        self.fields["client"].queryset = (
            Client.objects
            .all()
            .order_by("nom", "prenom")
        )


        for field in self.fields.values():

            field.widget.attrs.setdefault(
                "class",
                "form-control"
            )



    def clean_montant(self):

        montant = self.cleaned_data.get(
            "montant"
        )


        if montant is None:

            raise forms.ValidationError(
                "Le montant est obligatoire."
            )


        if montant <= Decimal("0"):

            raise forms.ValidationError(
                "Le montant doit être supérieur à zéro."
            )


        return montant