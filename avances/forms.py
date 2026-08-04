from django import forms
from personnel.models import Personnel
from clients.models import Client
from .models import Avance


class AvanceForm(forms.ModelForm):

    class Meta:
        model = Avance

        fields = [
            'personnel',
            'client',
            'motifAv',
            'montantAv',
            'typeAv'
        ]

        widgets = {

            "personnel": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),

            "client": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),

            "motifAv": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Motif de l'avance"
                }
            ),

            "montantAv": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Montant"
                }
            ),

            "typeAv": forms.Select(
                attrs={
                    "class": "form-control"
                }
            ),
        }


    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["personnel"].queryset = Personnel.objects.all()
        self.fields["client"].queryset = Client.objects.all()

        for field in self.fields.values():
            field.widget.attrs.setdefault(
                "class",
                "form-control"
            )