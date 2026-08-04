from django import forms
from .models import Personnel
from categorie.models import Categorie


class PersonnelForm(forms.ModelForm):

    class Meta:
        model = Personnel
        fields = [
            "nom",
            "prenom",
            "adresse",
            "telephone",
            "fonction",
            "psalaire",
            "debutContrat",
            "categorie",
            "photo",
        ]

        widgets = {

            "nom": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nom",
                }
            ),

            "prenom": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Prénom",
                }
            ),

            "adresse": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 2,
                    "placeholder": "Adresse",
                    "style": "resize:none;",
                }
            ),

            "telephone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "0340100001",
                    "maxlength": "10",
                    "pattern": "[0-9]{10}",
                }
            ),

            "fonction": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Fonction",
                }
            ),

            "psalaire": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Salaire",
                    "step": "0.01",
                }
            ),

            "debutContrat": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "categorie": forms.Select(
                attrs={
                    "class": "form-control",
                }
            ),

            "photo": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                }
            ),
        }


    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Liste déroulante des catégories
        self.fields["categorie"].queryset = (
            Categorie.objects.all().order_by("nom")
        )

        # Tous les champs en Bootstrap
        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "form-control"
            })


    def clean_nom(self):
        nom = self.cleaned_data.get("nom")
        if nom:
            return nom.upper()
        return nom


    def clean_prenom(self):
        prenom = self.cleaned_data.get("prenom")
        if prenom:
            return prenom.title()
        return prenom


    def clean_telephone(self):
        telephone = self.cleaned_data.get("telephone")

        if telephone and not telephone.isdigit():
            raise forms.ValidationError(
                "Le téléphone doit contenir uniquement des chiffres."
            )

        if telephone and len(telephone) != 10:
            raise forms.ValidationError(
                "Le numéro doit contenir exactement 10 chiffres."
            )

        return telephone