from django import forms
from django.utils import timezone

from .models import Depense


class DepenseForm(forms.ModelForm):

    class Meta:
        model = Depense

        fields = [
            "titre",
            "montant",
            "date",
            "description",
        ]

        widgets = {

            # ==================================================
            # TITRE LIBRE
            # ==================================================
            "titre": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Titre de la dépense",
                }
            ),

            # ==================================================
            # MONTANT
            # ==================================================
            "montant": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "1",
                    "min": "0",
                    "placeholder": "Montant",
                }
            ),

            # ==================================================
            # DATE LIBRE
            # ==================================================
            "date": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
            ),

            # ==================================================
            # DESCRIPTION
            # ==================================================
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Description de la dépense",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Format accepté par le champ HTML date
        self.fields["date"].input_formats = [
            "%Y-%m-%d"
        ]

        # ==================================================
        # NOUVELLE DÉPENSE
        # ==================================================
        # On propose automatiquement la date du jour,
        # mais l'utilisateur peut la modifier.
        # ==================================================
        if not self.instance.pk:
            self.initial["date"] = timezone.localdate()
