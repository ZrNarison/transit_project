from django import forms
from .models import h_Categorie


class h_CategorieForm(forms.ModelForm):

    class Meta:

        model = h_Categorie

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