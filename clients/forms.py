from django import forms
from .models import Client


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = "__all__"

        widgets = {
            "nom": forms.TextInput(attrs={"class": "form-control","placeholder": "Nom du client"}),
            "prenom": forms.TextInput(attrs={"class": "form-control","placeholder": "Prénom du client"}),

            "date_naissance": forms.DateInput(attrs={
                "class": "form-control",
                "placeholder": "Date de naissance",
                "type": "date"
            }),

            "lieu_naissance": forms.TextInput(attrs={"class": "form-control","placeholder": "Lieu de naissance"}),

            "cin": forms.TextInput(attrs={"class": "form-control","placeholder": "Numéro de la carte d'identité"}),

            "nom_pere": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nom du père"}),

            "nom_mere": forms.TextInput(attrs={"class": "form-control",
            "placeholder": "Nom de la mère"}),

            "contact": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Numéro téléphone",
                "maxlength": "10"
            }),

            "adresse": forms.Textarea(attrs={
                "class": "form-control","placeholder": "Tapez ici l'adresse du client",
                "rows": 2
            }),
        }