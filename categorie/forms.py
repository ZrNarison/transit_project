from django import forms
from .models import Categorie


class CategorieForm(forms.ModelForm):

    class Meta:
        model = Categorie
        fields = [
            "nom",
            "description"
        ]

        widgets = {

            "nom": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nom catégorie"
                }
            ),

            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Description",
                    "rows": 3,
                    "style": "resize:none;"
                }
            ),
        }