from django import forms

from .models import h_Recette


class h_RecetteForm(forms.ModelForm):

    class Meta:

        model = h_Recette

        fields = [
            "montant",
            "type_virement",
            "date",
            "source",
        ]

        widgets = {

            "montant": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Montant de la recette",
                    "min": "0",
                    "step": "0.01",
                }
            ),

            "type_virement": forms.Select(
                attrs={
                    "class": "form-control",
                    "pardefaut": "Espece",
                }
            ),

            "date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "source": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Source de la recette",
                }
            ),
        }

        labels = {
            "montant": "Montant",
            "type_virement": "Type de virement",
            "date": "Date",
            "source": "Source",
        }

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["date"].input_formats = [
            "%Y-%m-%d"
        ]
