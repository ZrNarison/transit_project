from django import forms
from .models import Transentrant

class TransentrantForm(forms.ModelForm):
    class Meta:
        model = Transentrant
        fields = "__all__"

        widgets = {
            "id_client": forms.Select(attrs={"class": "form-control"}),
            "Chauf_Ent": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Chauffeur"
            }),
            "NumVeh_Ent": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Numéro véhicule"
            }),
            "NumPermis_Ent": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Numéro permis"
            }),
            "adresse": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
                "style": "resize:none;"
            }),
            "telephone": forms.TextInput(attrs={
                "class": "form-control",
                "maxlength": "10"
            }),
            "photo": forms.ClearableFileInput(attrs={
                "class": "form-control"
            }),
        }