from django import forms
from .models import Produit


class ProduitForm(forms.ModelForm):

    class Meta:
        model = Produit
        fields = [
            'id_client',
            'Nom_Prod',
            'Source_Prod',
            'Type_Pro',
            'Montant_Pro',
            'Qte_Pro',
            'Pourcentage_Pro',
            'photo'
        ]

        widgets = {
            "id_client": forms.Select(attrs={
                "class": "form-control"
            }),

            "Nom_Prod": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nom du produit"
            }),

            "Source_Prod": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Source du produit"
            }),

            "Type_Pro": forms.Select(attrs={
                "class": "form-control"
            }),

            "Montant_Pro": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Montant"
            }),

            "Qte_Pro": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Quantité"
            }),

            "Pourcentage_Pro": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Pourcentage"
            }),

            "photo": forms.ClearableFileInput(attrs={
                "class": "form-control"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")