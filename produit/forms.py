from django import forms
from .models import Produit


class ProduitForm(forms.ModelForm):

    class Meta:
        model = Produit
        fields = [
            "client",
            "vehicule",
            "source",
            "type_produit",
            "montant",
            "quantite",
            "pourcentage",
            "photo",
        ]

        widgets = {
            "client": forms.Select(attrs={"class": "form-control"}),
            "vehicule": forms.Select(attrs={"class": "form-control"}),
            "source": forms.TextInput(attrs={"class": "form-control","placeholder": "Tapez ici la lieu de provenance de la marchandise"}),

            "type_reglement": forms.Select(attrs={
    "class": "form-control"
}),

            "montant": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "En nombre",
                "maxlength": "4"
            }),

            "quantite": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "En nombre"
            }),

            "pourcentage": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder" : "En nombre",
                "maxlength": "1"
            }),

            "photo": forms.ClearableFileInput(attrs={
                "class": "form-control"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        for field in self.fields.values():
            field.widget.attrs.update({
                "class": "form-control"
            })