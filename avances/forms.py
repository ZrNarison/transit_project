from django import forms

from .models import Avance
from personnel.models import Personnel


class AvanceForm(forms.ModelForm):

    class Meta:
        model = Avance

        fields = [
            "personnel",
            "motifAv",
            "montantAv",
            "typeAv",
            "dateAv",
        ]

        labels = {
            "personnel": "Personnel",
            "motifAv": "Motif",
            "montantAv": "Montant",
            "typeAv": "Type d'avance",
            "dateAv": "Date de l'avance",
        }

        widgets = {

            # =================================================
            # PERSONNEL
            # =================================================
            "personnel": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            # =================================================
            # MOTIF
            # =================================================
            "motifAv": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Motif de l'avance",
                }
            ),

            # =================================================
            # MONTANT
            # =================================================
            "montantAv": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Montant",
                    "min": "1",
                    "step": "1",
                }
            ),

            # =================================================
            # TYPE D'AVANCE
            # =================================================
            "typeAv": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            # =================================================
            # DATE
            #
            # IMPORTANT :
            # dateAv est un DateField.
            # On utilise donc type="date".
            #
            # NE PAS mettre :
            # format="%Y-%m-%d%"
            #
            # NE PAS mettre :
            # type="datetime-local"
            # =================================================
            "dateAv": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
        }

    # =========================================================
    # INITIALISATION
    # =========================================================

    def __init__(self, *args, role=None, **kwargs):

        super().__init__(*args, **kwargs)

        # =====================================================
        # PERSONNEL SELON LE RÔLE
        # =====================================================

        queryset = (
            Personnel.objects
            .select_related("categorie")
            .all()
            .order_by("nom", "prenom")
        )

        # -----------------------------------------------------
        # USER MICA
        # -----------------------------------------------------

        if role == "UserMica":

            queryset = queryset.filter(
                typeTravail="Mica"
            )

        # -----------------------------------------------------
        # USER ENTREPRISE
        # -----------------------------------------------------

        elif role == "UserEntreprise":

            queryset = queryset.filter(
                typeTravail="Construction"
            )

        # -----------------------------------------------------
        # ADMIN / SUPERADMIN / SUPERVISEUR
        # -----------------------------------------------------

        elif role in [
            "Admin",
            "SuperAdmin",
            "Superviseur",
        ]:

            pass

        # -----------------------------------------------------
        # AUTRE RÔLE
        # -----------------------------------------------------

        else:

            queryset = Personnel.objects.none()

        self.fields["personnel"].queryset = queryset

        # =====================================================
        # DATE EXISTANTE EN MODIFICATION
        # =====================================================

        if self.instance and self.instance.pk:

            if self.instance.dateAv:

                self.initial["dateAv"] = (
                    self.instance.dateAv.strftime("%Y-%m-%d")
                )

    # =========================================================
    # VALIDATION MONTANT
    # =========================================================

    def clean_montantAv(self):

        montant = self.cleaned_data.get("montantAv")

        if montant is None:
            raise forms.ValidationError(
                "Le montant est obligatoire."
            )

        if montant <= 0:
            raise forms.ValidationError(
                "Le montant doit être supérieur à 0."
            )

        return montant

    # =========================================================
    # VALIDATION PERSONNEL
    # =========================================================

    def clean_personnel(self):

        personnel = self.cleaned_data.get("personnel")

        if not personnel:
            raise forms.ValidationError(
                "Veuillez sélectionner un personnel."
            )

        return personnel

    # =========================================================
    # VALIDATION MOTIF
    # =========================================================

    def clean_motifAv(self):

        motif = self.cleaned_data.get("motifAv")

        if not motif or not motif.strip():

            raise forms.ValidationError(
                "Veuillez renseigner le motif de l'avance."
            )

        return motif.strip()

    # =========================================================
    # VALIDATION DATE
    # =========================================================

    def clean_dateAv(self):

        date_avance = self.cleaned_data.get("dateAv")

        if not date_avance:

            raise forms.ValidationError(
                "Veuillez sélectionner une date."
            )

        return date_avance