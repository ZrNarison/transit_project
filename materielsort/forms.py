from django import forms

from .models import MaterielSort
from materiels.models import Materiels


class MaterielSortForm(forms.ModelForm):

    class Meta:
        model = MaterielSort

        fields = [
            "id_Materiel",
            "demandeur",
            "responsable_sortie",
            "Nb_MatSort",
            "dateSortie",
            "observation",
        ]

        widgets = {
            "id_Materiel": forms.Select(
                attrs={
                    "class": "form-select"
                }
            ),

            "demandeur": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nom du demandeur"
                }
            ),

            "responsable_sortie": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Responsable de la sortie du matériel"
                }
            ),

            "Nb_MatSort": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nombre de matériel à sortir",
                    "min": "1"
                }
            ),

            "dateSortie": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date"
                }
            ),

            "observation": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "placeholder": "Observations éventuelles",
                    "rows": 3
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # =====================================================
        # RÉCUPÉRATION DES MATÉRIELS
        # =====================================================

        materiels = (
            Materiels.objects
            .all()
            .order_by(
                "nom",
                "typeMat",
                "catMat",
                "id"
            )
        )

        # =====================================================
        # REGROUPEMENT
        #
        # NOM + TYPE + CATÉGORIE
        # =====================================================

        groupes = {}

        for materiel in materiels:

            nom = (materiel.nom or "").strip()
            type_mat = (materiel.typeMat or "").strip()
            categorie = (materiel.catMat or "").strip()

            cle = (
                nom.lower(),
                type_mat.lower(),
                categorie.lower(),
            )

            if cle not in groupes:
                groupes[cle] = materiel

        # =====================================================
        # CONSTRUCTION DE LA LISTE DÉROULANTE
        # =====================================================

        choix = [
            (
                "",
                "--------- Sélectionner un matériel ---------"
            )
        ]

        for materiel in groupes.values():

            nom = (materiel.nom or "").strip()
            type_mat = (materiel.typeMat or "").strip()
            categorie = (materiel.catMat or "").strip()

            libelle = (
                f"{nom.upper()} | "
                f"{type_mat.title()} | "
                f"{categorie.title()}"
            )

            choix.append(
                (
                    materiel.id,
                    libelle
                )
            )

        self.fields["id_Materiel"].choices = choix

    # =========================================================
    # VALIDATION QUANTITÉ
    # =========================================================

    def clean_Nb_MatSort(self):

        quantite = self.cleaned_data.get("Nb_MatSort")

        if quantite is None or quantite <= 0:

            raise forms.ValidationError(
                "La quantité sortie doit être supérieure à 0."
            )

        return quantite
