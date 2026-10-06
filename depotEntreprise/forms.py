from django import forms

from .models import DepotSoc


class DepotSocForm(forms.ModelForm):

    class Meta:

        model = DepotSoc

        fields = [
            "montant",
            "date",
        ]

        widgets = {

            "montant": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Montant du dépôt",
                    "min": "0",
                    "step": "0.01",
                }
            ),

            "date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
        }

        labels = {
            "montant": "Montant",
            "date": "Date du dépôt",
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["date"].input_formats = [
            "%Y-%m-%d"
        ]

    def clean_montant(self):

        montant = self.cleaned_data.get("montant")

        if montant is None:
            raise forms.ValidationError(
                "Le montant est obligatoire."
            )

        if montant <= 0:
            raise forms.ValidationError(
                "Le montant doit être supérieur à zéro."
            )

        return montant