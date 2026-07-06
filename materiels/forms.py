from django import forms
from .models import Materiels


class MaterielsForm(forms.ModelForm):

    class Meta:
        model = Materiels
        fields = "__all__"

        widgets = {

            "nom": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nom du matériel"
                }
            ),

            "type": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Type"
                }
            ),

            "categorie": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Catégorie"
                }
            ),
        }