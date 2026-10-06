from django import forms

from .models import Materiels


class MaterielsForm(forms.ModelForm):

    class Meta:
        model = Materiels

        fields = [
            "photo",
            "nom",
            "typeMat",
            "catMat",
            "stock_initial",
        ]

        widgets = {
            "photo": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                }
            ),

            "nom": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nom du matériel",
                }
            ),

            "typeMat": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Type matériel",
                }
            ),

            "catMat": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Catégorie",
                }
            ),

            "stock_initial": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Stock initial",
                    "min": "0",
                    "step": "1",
                }
            ),
        }

        labels = {
            "photo": "Photo",
            "nom": "Nom du matériel",
            "typeMat": "Type",
            "catMat": "Catégorie",
            "stock_initial": "Stock initial",
        }

    # ============================================================
    # INITIALISATION
    # ============================================================

    def __init__(self, *args, role=None, **kwargs):

        super().__init__(*args, **kwargs)

        self.role = role

        # ========================================================
        # USER ENTREPRISE
        # Catégorie imposée = Chantier
        # ========================================================

        if role == "UserEntreprise":

            self.fields["catMat"].initial = "Chantier"

            # L'utilisateur ne peut pas modifier le champ
            self.fields["catMat"].disabled = True

        # ========================================================
        # USER MICA
        # Catégorie imposée = Mica
        # ========================================================

        elif role == "UserMica":

            self.fields["catMat"].initial = "Mica"

            # L'utilisateur ne peut pas modifier le champ
            self.fields["catMat"].disabled = True

        # ========================================================
        # ADMIN / SUPERADMIN / SUPERVISEUR
        # Catégorie libre
        # ========================================================

        else:

            self.fields["catMat"].disabled = False

    # ============================================================
    # VALIDATION CATEGORIE
    # ============================================================

    def clean_catMat(self):

        categorie = self.cleaned_data.get(
            "catMat",
            ""
        )

        # ========================================================
        # USER ENTREPRISE
        # ========================================================

        if self.role == "UserEntreprise":
            return "Chantier"

        # ========================================================
        # USER MICA
        # ========================================================

        if self.role == "UserMica":
            return "Mica"

        # ========================================================
        # ADMIN / SUPERADMIN / SUPERVISEUR
        # ========================================================

        return categorie.strip()
