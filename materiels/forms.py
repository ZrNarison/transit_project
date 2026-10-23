
from django import forms
from .models import H_Materiels, Materiels, Vehicule, ReparationVehicule
from personnel.models import Personnel, H_Personnel
from materiaux.models import H_Vehicule, ReparationVehicule as H_ReparationVehicule
from decimal import Decimal


# ============================================================
# MATERIELS GALAXY
# ============================================================
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
                attrs={"class": "form-control"}
            ),
            "nom": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nom du matÃ©riel",
                }
            ),
            "typeMat": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Type matÃ©riel",
                }
            ),
            "catMat": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "CatÃ©gorie",
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
            "nom": "Nom du matÃ©riel",
            "typeMat": "Type",
            "catMat": "CatÃ©gorie",
            "stock_initial": "Stock initial",
        }

    def __init__(self, *args, role=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = role

        if role == "UserEntreprise":
            self.fields["catMat"].initial = "Chantier"
            self.fields["catMat"].disabled = True

        elif role == "UserMica":
            self.fields["catMat"].initial = "Mica"
            self.fields["catMat"].disabled = True

        else:
            self.fields["catMat"].disabled = False

    def clean_catMat(self):
        categorie = self.cleaned_data.get("catMat", "")

        if self.role == "UserEntreprise":
            return "Chantier"

        if self.role == "UserMica":
            return "Mica"

        return categorie.strip()


# ============================================================
# VEHICULES / ENGINS GALAXY
# ============================================================
class VehiculeForm(forms.ModelForm):
    """Formulaire de création et de modification d'un véhicule GALAXY."""

    vehicule = forms.CharField(
        label="N° Immatriculation",
        max_length=30,
        required=True,
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Ex. : 54254 WWT ou 5474 TG",
                "autocomplete": "off",
                "style": "text-transform: uppercase;",
            }
        ),
        help_text="Saisissez une immatriculation unique.",
    )

    class Meta:
        model = Vehicule

        # Aucun chauffeur dans le formulaire.
        fields = [
            "vehicule",
            "type_vehicule",
            "date_debut",
            "date_fin",
            "kilometrage_initial",
            "kilometrage_final",
            "consommation_km_litre",
            "heures_initiales",
            "heures_finales",
            "consommation_heure_litre",
            "actif",
            "observation",
        ]

        widgets = {
            "type_vehicule": forms.Select(
                attrs={"class": "form-select"}
            ),
            "date_debut": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "date_fin": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "kilometrage_initial": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "kilometrage_final": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "consommation_km_litre": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "heures_initiales": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "heures_finales": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "consommation_heure_litre": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "actif": forms.CheckboxInput(
                attrs={"class": "form-check-input"}
            ),
            "observation": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Observations éventuelles...",
                }
            ),
        }

        labels = {
            "type_vehicule": "Type de véhicule",
            "date_debut": "Date de début",
            "date_fin": "Date de fin",
            "kilometrage_initial": "Kilométrage initial",
            "kilometrage_final": "Kilométrage final",
            "consommation_km_litre": "Consommation (km/L)",
            "heures_initiales": "Heures initiales",
            "heures_finales": "Heures finales",
            "consommation_heure_litre": "Consommation (L/h)",
            "actif": "Affectation active",
            "observation": "Observation",
        }

    def __init__(self, *args, projet=None, **kwargs):
        self.projet = projet

        super().__init__(*args, **kwargs)

        # Aucun chauffeur n'est demandé à l'enregistrement.
        self.fields["date_fin"].required = False

        # Les mesures sont facultatives dans le formulaire.
        champs_numeriques = [
            "kilometrage_initial",
            "kilometrage_final",
            "consommation_km_litre",
            "heures_initiales",
            "heures_finales",
            "consommation_heure_litre",
        ]

        for nom in champs_numeriques:
            self.fields[nom].required = False

        if not self.instance.pk:
            self.fields["actif"].initial = True

    def clean_vehicule(self):
        """Normalise l'immatriculation et interdit les doublons."""

        immatriculation = (
            self.cleaned_data.get("vehicule") or ""
        ).strip().upper()

        if not immatriculation:
            raise forms.ValidationError(
                "Le numéro d'immatriculation est obligatoire."
            )

        doublons = Vehicule.objects.filter(
            vehicule__iexact=immatriculation
        )

        if self.instance.pk:
            doublons = doublons.exclude(pk=self.instance.pk)

        if doublons.exists():
            raise forms.ValidationError(
                "Cette immatriculation est déjà enregistrée."
            )

        return immatriculation

    def clean(self):
        cleaned_data = super().clean()

        type_vehicule = cleaned_data.get("type_vehicule")
        date_debut = cleaned_data.get("date_debut")
        date_fin = cleaned_data.get("date_fin")

        # Vérification des dates.
        if date_debut and date_fin and date_fin < date_debut:
            self.add_error(
                "date_fin",
                "La date de fin doit être postérieure "
                "ou égale à la date de début.",
            )

        # Préserve les validations des dates du projet.
        if self.projet:
            projet_debut = getattr(
                self.projet, "date_debut", None
            )
            projet_fin = getattr(
                self.projet, "date_fin", None
            )

            if (
                date_debut
                and projet_debut
                and date_debut < projet_debut
            ):
                self.add_error(
                    "date_debut",
                    "La date de début ne peut pas précéder "
                    "celle du projet.",
                )

            if (
                date_debut
                and projet_fin
                and date_debut > projet_fin
            ):
                self.add_error(
                    "date_debut",
                    "La date de début ne peut pas dépasser "
                    "la date de fin du projet.",
                )

            if (
                date_fin
                and projet_debut
                and date_fin < projet_debut
            ):
                self.add_error(
                    "date_fin",
                    "La date de fin ne peut pas précéder "
                    "celle du projet.",
                )

            if (
                date_fin
                and projet_fin
                and date_fin > projet_fin
            ):
                self.add_error(
                    "date_fin",
                    "La date de fin ne peut pas dépasser "
                    "celle du projet.",
                )

        champs_km = [
            "kilometrage_initial",
            "kilometrage_final",
            "consommation_km_litre",
        ]

        champs_heures = [
            "heures_initiales",
            "heures_finales",
            "consommation_heure_litre",
        ]

        # Convertit les champs facultatifs vides en zéro.
        for nom in champs_km + champs_heures:
            valeur = cleaned_data.get(nom)

            if valeur is None:
                cleaned_data[nom] = Decimal("0.00")

        # Véhicule routier : validation des kilomètres.
        if type_vehicule == "ROUTIER":
            for nom in champs_km:
                valeur = cleaned_data.get(
                    nom, Decimal("0.00")
                )

                if valeur < Decimal("0.00"):
                    self.add_error(
                        nom,
                        "Cette valeur ne peut pas être négative.",
                    )

            km_initial = cleaned_data.get(
                "kilometrage_initial", Decimal("0.00")
            )
            km_final = cleaned_data.get(
                "kilometrage_final", Decimal("0.00")
            )

            if km_final < km_initial:
                self.add_error(
                    "kilometrage_final",
                    "Le kilométrage final doit être supérieur "
                    "ou égal au kilométrage initial.",
                )

            # Les mesures horaires ne concernent pas ce type.
            for nom in champs_heures:
                cleaned_data[nom] = Decimal("0.00")

        # Engin : validation des heures de fonctionnement.
        elif type_vehicule == "ENGIN":
            for nom in champs_heures:
                valeur = cleaned_data.get(
                    nom, Decimal("0.00")
                )

                if valeur < Decimal("0.00"):
                    self.add_error(
                        nom,
                        "Cette valeur ne peut pas être négative.",
                    )

            heures_initiales = cleaned_data.get(
                "heures_initiales", Decimal("0.00")
            )
            heures_finales = cleaned_data.get(
                "heures_finales", Decimal("0.00")
            )

            if heures_finales < heures_initiales:
                self.add_error(
                    "heures_finales",
                    "Les heures finales doivent être supérieures "
                    "ou égales aux heures initiales.",
                )

            # Les mesures kilométriques ne concernent pas ce type.
            for nom in champs_km:
                cleaned_data[nom] = Decimal("0.00")

        return cleaned_data

# ============================================================
# REPARATIONS VEHICULES GALAXY
# ============================================================
class ReparationVehiculeForm(forms.ModelForm):
    class Meta:
        model = ReparationVehicule

        fields = [
            "date_reparation",
            "vehicule",
            "designation",
            "type_reparation",
            "garage",
            "quantite",
            "unite",
            "prix_unitaire",
            "montant_main_oeuvre",
            "photo_piece_remplacee",
            "photo_piece_remplacante",
        ]

        widgets = {
            "date_reparation": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "vehicule": forms.Select(
                attrs={"class": "form-select"}
            ),
            "designation": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Désignation de la réparation",
                }
            ),
            "type_reparation": forms.Select(
                attrs={"class": "form-select"}
            ),
            "garage": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nom du garage",
                }
            ),
            "quantite": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
            "unite": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Unité",
                }
            ),
            "prix_unitaire": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "montant_main_oeuvre": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                }
            ),
            "photo_piece_remplacee": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),
            "photo_piece_remplacante": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),
        }

        labels = {
            "date_reparation": "Date de réparation",
            "vehicule": "Matériel / véhicule GALAXY",
            "designation": "Désignation",
            "type_reparation": "Type de réparation",
            "garage": "Garage",
            "quantite": "Quantité",
            "unite": "Unité",
            "prix_unitaire": "Prix unitaire",
            "montant_main_oeuvre": "Main-d'œuvre",
            "photo_piece_remplacee": "Photo de la pièce remplacée",
            "photo_piece_remplacante": "Photo de la pièce de remplacement",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Afficher uniquement les véhicules et engins du modèle Vehicule.
        self.fields["vehicule"].queryset = (
            Vehicule.objects.all().order_by("vehicule")
        )

# ============================================================
# MATERIELS H / MCCR
# ============================================================
class H_MaterielsForm(forms.ModelForm):
    class Meta:
        model = H_Materiels

        fields = [
            "photo",
            "nom",
            "typeMat",
            "catMat",
            "stock_initial",
        ]

        widgets = {
            "photo": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),
            "nom": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nom du matÃ©riel",
                }
            ),
            "typeMat": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Type matÃ©riel",
                }
            ),
            "catMat": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "CatÃ©gorie",
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
            "nom": "Nom du matÃ©riel",
            "typeMat": "Type",
            "catMat": "CatÃ©gorie",
            "stock_initial": "Stock initial",
        }

    def __init__(self, *args, role=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.role = role

        if role == "UserEntreprise":
            self.fields["catMat"].initial = "Chantier"
            self.fields["catMat"].disabled = True

        elif role == "UserMica":
            self.fields["catMat"].initial = "Mica"
            self.fields["catMat"].disabled = True

        else:
            self.fields["catMat"].disabled = False

    def clean_catMat(self):
        categorie = self.cleaned_data.get("catMat", "")

        if self.role == "UserEntreprise":
            return "Chantier"

        if self.role == "UserMica":
            return "Mica"

        return categorie.strip()


# ============================================================
# VÃ‰HICULES / ENGINS H / MCCR
# ============================================================
class H_VehiculeForm(forms.ModelForm):
    class Meta:
        model = H_Vehicule
        fields = [
            "immatriculation",
            "marque",
            "modele",
            "kilometrage",
            "actif",
        ]
        widgets = {
            "immatriculation": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Exemple : 1234 TAA",
            }),
            "marque": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Marque du véhicule",
            }),
            "modele": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Modèle du véhicule",
            }),
            "kilometrage": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
            }),
            "actif": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }
        labels = {
            "immatriculation": "Immatriculation",
            "marque": "Marque",
            "modele": "Modèle",
            "kilometrage": "Kilométrage actuel",
            "actif": "Véhicule actif",
        }

    def clean_immatriculation(self):
        immatriculation = self.cleaned_data.get("immatriculation", "")
        immatriculation = immatriculation.strip().upper()
        if not immatriculation:
            raise forms.ValidationError(
                "Veuillez saisir l'immatriculation du véhicule."
            )
        return immatriculation

    def clean_kilometrage(self):
        kilometrage = self.cleaned_data.get("kilometrage")
        if kilometrage is not None and kilometrage < 0:
            raise forms.ValidationError(
                "Le kilométrage ne peut pas être négatif."
            )
        return kilometrage

# ============================================================
# REPARATIONS VEHICULES H / MCCR
# ============================================================
class H_ReparationVehiculeForm(forms.ModelForm):

    class Meta:
        model = H_ReparationVehicule

        fields = [
            "date_reparation",
            "vehicule",
            "chauffeur",
            "chauffeur_personnel",
            "designation",
            "type_reparation",
            "garage",
            "quantite",
            "unite",
            "prix_unitaire",
            "montant_main_oeuvre",
            "photo_piece_remplacee",
            "photo_piece_remplacante",
        ]

        widgets = {
            "date_reparation": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),

            "vehicule": forms.Select(
                attrs={"class": "form-select"}
            ),

            "chauffeur": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nom du chauffeur",
                }
            ),

            "chauffeur_personnel": forms.Select(
                attrs={"class": "form-select"}
            ),

            "designation": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "DÃ©signation de la rÃ©paration",
                }
            ),

            "type_reparation": forms.Select(
                attrs={"class": "form-select"}
            ),

            "garage": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nom du garage",
                }
            ),

            "quantite": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),

            "unite": forms.TextInput(
                attrs={"class": "form-control"}
            ),

            "prix_unitaire": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                }
            ),

            "montant_main_oeuvre": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0",
                    "step": "0.01",
                }
            ),

            "photo_piece_remplacee": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),

            "photo_piece_remplacante": forms.ClearableFileInput(
                attrs={"class": "form-control"}
            ),
        }

        labels = {
            "date_reparation": "Date de rÃ©paration",
            "vehicule": "MatÃ©riel / vÃ©hicule MCCR",
            "chauffeur": "Chauffeur (texte historique)",
            "chauffeur_personnel": "Chauffeur MCCR",
            "designation": "DÃ©signation de la rÃ©paration",
            "type_reparation": "Type de rÃ©paration",
            "garage": "Garage",
            "quantite": "QuantitÃ©",
            "unite": "UnitÃ©",
            "prix_unitaire": "Prix unitaire",
            "montant_main_oeuvre": "Montant de la main-d'Å“uvre",
            "photo_piece_remplacee": "Photo de la piÃ¨ce remplacÃ©e",
            "photo_piece_remplacante": "Photo de la piÃ¨ce de remplacement",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # MatÃ©riels appartenant Ã  MCCR uniquement.
        self.fields["vehicule"].queryset = (
            H_Materiels.objects.all().order_by("nom")
        )

        # Personnel appartenant Ã  MCCR uniquement.
        self.fields["chauffeur_personnel"].queryset = (
            H_Personnel.objects.all().order_by("nom", "prenom")
        )

        # Le chauffeur liÃ© au personnel reste facultatif.
        self.fields["chauffeur_personnel"].required = False
