from django import forms

from .models import MaterielEntre


class MaterielEntreForm(forms.ModelForm):

    class Meta:
        model = MaterielEntre

        fields = [
            "id_MaterielSort",
            "Nb_Entre",
            "dateEntre",              # <-- virgule importante
            "responsable_entree",
            "observation",
        ]

        widgets = {
            "id_MaterielSort": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),

            "Nb_Entre": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "1",
                    "step": "1",
                    "placeholder": "Quantité entrée",
                }
            ),

            "dateEntre": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "responsable_entree": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Responsable de l'entrée",
                }
            ),

            "observation": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Observation (optionnel)",
                }
            ),
        }

    # ==========================================================
    # VALIDATION QUANTITE
    # ==========================================================

    def clean_Nb_Entre(self):
        quantite = self.cleaned_data.get("Nb_Entre")

        if quantite is None or quantite <= 0:
            raise forms.ValidationError(
                "La quantité entrée doit être supérieure à 0."
            )

        return quantite

    # ==========================================================
    # VALIDATION DATE
    # ==========================================================

    def clean_dateEntre(self):
        date_entre = self.cleaned_data.get("dateEntre")

        sortie = self.cleaned_data.get("id_MaterielSort")

        if not date_entre:
            raise forms.ValidationError(
                "La date d'entrée est obligatoire."
            )

        if not sortie:
            return date_entre

        date_sortie = sortie.dateSortie

        # La date d'entrée doit être >= à la date de sortie
        if date_entre < date_sortie:
            raise forms.ValidationError(
                f"La date d'entrée doit être égale ou postérieure "
                f"à la date de sortie "
                f"({date_sortie.strftime('%d/%m/%Y')})."
            )

        return date_entre
