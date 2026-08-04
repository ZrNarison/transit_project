from django import forms
from personnel.models import Personnel
from .models import Salaire


class SalaireForm(forms.ModelForm):

    class Meta:
        model = Salaire

        fields = [
            "personnel",
            "montant",
        ]

        widgets = {

            "personnel": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),

            "montant": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "placeholder": "Montant salaire"
                }
            ),
        }


    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)


        self.fields["personnel"].queryset = (
            Personnel.objects
            .order_by(
                "nom",
                "prenom"
            )
        )


        self.fields["personnel"].empty_label = (
            "Sélectionner un personnel"
        )