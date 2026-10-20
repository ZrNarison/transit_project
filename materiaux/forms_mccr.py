
from django import forms

from .models import MateriauMCCR, MouvementMateriauMCCR


class MateriauxMCCRForm(forms.ModelForm):
    class Meta:
        model = MateriauMCCR
        fields = ["nom", "unite", "actif"]

        widgets = {
            "nom": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nom du matériau",
            }),
            "unite": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ex. kg, m³, sac",
            }),
            "actif": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }



class MouvementMateriauMCCRForm(forms.ModelForm):

    class Meta:
        model = MouvementMateriauMCCR

        fields = [
            "materiau",
            "type_mouvement",
            "quantite",
            "prix_unitaire",
            "motif",
            "date_mouvement",
            "observation",
        ]

        widgets = {
            "materiau": forms.Select(attrs={
                "class": "form-select",
            }),
            "type_mouvement": forms.Select(attrs={
                "class": "form-select",
            }),
            "quantite": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0.01",
                "step": "0.01",
                "required": True,
            }),
            "prix_unitaire": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0.01",
                "step": "0.01",
                "required": True,
                "placeholder": "Prix d'achat ou de vente en Ar",
            }),
            "motif": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Motif du mouvement",
            }),
            "date_mouvement": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
                "required": True,
            }),
            "observation": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["quantite"].required = True
        self.fields["prix_unitaire"].required = True

        materiaux = MateriauMCCR.objects.filter(
            actif=True
        ).order_by("nom")

        # Autoriser la modification d'un mouvement même si
        # son matériau a été désactivé.
        if self.instance and self.instance.pk:
            materiaux = (
                materiaux
                | MateriauMCCR.objects.filter(
                    pk=self.instance.materiau_id
                )
            ).distinct()

        self.fields["materiau"].queryset = materiaux

    def clean_prix_unitaire(self):
        prix = self.cleaned_data.get("prix_unitaire")

        if prix is None or prix <= 0:
            raise forms.ValidationError(
                "Le prix unitaire est obligatoire et doit "
                "être supérieur à zéro."
            )

        return prix

    def clean_quantite(self):
        quantite = self.cleaned_data.get("quantite")

        if quantite is None or quantite <= 0:
            raise forms.ValidationError(
                "La quantité doit être supérieure à zéro."
            )

        return quantite
