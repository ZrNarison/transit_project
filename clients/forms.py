from django import forms

from .models import Client


class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = "__all__"

        widgets = {
            "nom": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nom du client"}
            ),
            "prenom": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Prénom du client"}
            ),
            "date_naissance": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Date de naissance",
                    "type": "date",
                }
            ),
            "lieu_naissance": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Lieu de naissance"}
            ),
            "cin": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "maxlength": "12",
                    "placeholder": "Numéro Carte d'identité National",
                    "pattern": "[0-9]{12}",
                    # et que la 6e soit 1 soit 2 , unique pour clé
                    "inputmode": "numeric",
                }
            ),
            "nom_pere": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nom du père"}
            ),
            "nom_mere": forms.TextInput(
                attrs={"class": "form-control", "placeholder": "Nom de la mère"}
            ),
            "contact": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "maxlength": "10",
                    "placeholder": "034 01 000 01",
                    "pattern": "[0-9]{10}",
                    "inputmode": "numeric",
                }
            ),
            "adresse": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Tapez ici l'adresse du client",
                    "rows": 2,
                }
            ),
        }

        def clean_cin(self):
                cin = self.cleaned_data.get("cin", "").strip()
        
                if len(cin) < 6 or cin[5] not in ("1", "2"):
                    raise forms.ValidationError("Le 6e chiffre du CIN doit être 1 ou 2.")
        
                return cin
