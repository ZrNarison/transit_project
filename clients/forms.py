from django import forms
from django.forms import inlineformset_factory

from .models import Client
from contactclient.models import ContactClient
from comptebancaire.models import CompteBancaire


# =========================
# FORM CLIENT
# =========================
class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = "__all__"

        widgets = {
            "nom": forms.TextInput(attrs={"class": "form-control"}),
            "prenom": forms.TextInput(attrs={"class": "form-control"}),
            "date_naissance": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date"
            }),
            "lieu_naissance": forms.TextInput(attrs={"class": "form-control"}),
            "nom_pere": forms.TextInput(attrs={"class": "form-control"}),
            "nom_mere": forms.TextInput(attrs={"class": "form-control"}),
            "adresse": forms.Textarea(attrs={"class": "form-control", "rows": 2}),
            "telephone": forms.TextInput(attrs={"class": "form-control"}),
        }


# =========================
# FORMSET CONTACT CLIENT
# =========================
ContactFormSet = inlineformset_factory(
    Client,
    ContactClient,
    fields=("numero", "titulaire", "principal"),
    extra=1,
    can_delete=True
)


# =========================
# FORMSET COMPTE BANCAIRE
# =========================
CompteFormSet = inlineformset_factory(
    Client,
    CompteBancaire,
    fields=("nom_banque", "numero_compte", "principal"),
    extra=1,
    can_delete=True
)