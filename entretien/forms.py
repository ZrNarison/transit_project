from django import forms
from .models import Entretien


class EntretienForm(forms.ModelForm):

    class Meta:
        model = Entretien

        fields = [
            "num_vehicule",
            "piece_acheter",
            "nombre",
            "prix_du_piece",
            "observation",
        ]

        widgets = {

            "num_vehicule": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ex: 1234 TAB"
                }
            ),

            "piece_acheter": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nom de la pièce"
                }
            ),

            "nombre": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": 1
                }
            ),

            "prix_du_piece": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "placeholder": "Prix"
                }
            ),

            "observation": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Observation..."
                }
            ),
        }