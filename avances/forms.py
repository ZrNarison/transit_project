from django import forms
from .models import Avance


class AvanceForm(forms.ModelForm):

    class Meta:
        model = Avance
        fields = ['id_client', 'motifAv', 'montantAv', 'typeAv']

        widgets = {
            "id_client": forms.Select(attrs={
                "class": "form-control"
            }),

            "motifAv": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Motif de l'avance"
            }),

            "montantAv": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Montant"
            }),

            "typeAv": forms.Select(attrs={
                "class": "form-control"
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Bootstrap uniforme
        for field in self.fields.values():
            field.widget.attrs.setdefault("class", "form-control")