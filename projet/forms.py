from django import forms
from decimal import Decimal
from personnel.models import Personnel
from materiaux.models import Materiaux, Vehicule

from .models import (
    Projet,
    EquipeProjet,
    VehiculeProjet,
    ActiviteTransportProjet,
    PointProjet,
    RapportProjet,
    RapportTravail,
    RapportMateriau,
    RapportVehicule,
)


# ============================================================
# STYLE BOOTSTRAP
# ============================================================

DATE_WIDGET = forms.DateInput(
    attrs={
        "class": "form-control",
        "type": "date",
    }
)

TEXT_WIDGET = forms.TextInput(
    attrs={
        "class": "form-control",
    }
)

TEXTAREA_WIDGET = forms.Textarea(
    attrs={
        "class": "form-control",
        "rows": 4,
    }
)

SELECT_WIDGET = forms.Select(
    attrs={
        "class": "form-select",
    }
)

NUMBER_WIDGET = forms.NumberInput(
    attrs={
        "class": "form-control",
        "step": "0.01",
    }
)

CHECKBOX_WIDGET = forms.CheckboxInput(
    attrs={
        "class": "form-check-input",
    }
)

FILE_WIDGET = forms.ClearableFileInput(
    attrs={
        "class": "form-control",
    }
)


# ============================================================
# PROJET
# ============================================================

class ProjetForm(forms.ModelForm):

    class Meta:
        model = Projet

        fields = [
            "titre",
            "localisation",
            "date_debut",
            "date_fin",
            "statut",
            "budget_previsionnel",
            "observation",
        ]

        widgets = {
            "titre": TEXT_WIDGET,
            "localisation": TEXT_WIDGET,
            "date_debut": DATE_WIDGET,
            "date_fin": DATE_WIDGET,
            "statut": SELECT_WIDGET,
            "budget_previsionnel": NUMBER_WIDGET,
            "observation": TEXTAREA_WIDGET,
        }

        labels = {
            "titre": "Titre du projet",
            "localisation": "Localisation",
            "date_debut": "Date de début",
            "date_fin": "Date de fin",
            "statut": "Statut",
            "budget_previsionnel": "Budget prévisionnel (Ar)",
            "observation": "Observation",
        }

    def clean(self):

        cleaned_data = super().clean()

        date_debut = cleaned_data.get("date_debut")
        date_fin = cleaned_data.get("date_fin")
        budget = cleaned_data.get("budget_previsionnel")

        if (
            date_debut
            and date_fin
            and date_fin < date_debut
        ):
            self.add_error(
                "date_fin",
                (
                    "La date de fin doit être "
                    "supérieure ou égale à la date de début."
                ),
            )

        if budget is not None and budget < 0:

            self.add_error(
                "budget_previsionnel",
                "Le budget ne peut pas être négatif.",
            )

        return cleaned_data


# ============================================================
# EQUIPE PROJET
# ============================================================

class EquipeProjetForm(forms.ModelForm):

    class Meta:
        model = EquipeProjet

        fields = [
            "personnel",
            "fonction",
            "date_debut",
            "date_fin",
            "actif",
            "observation",
        ]

        widgets = {
            "personnel": SELECT_WIDGET,
            "fonction": SELECT_WIDGET,
            "date_debut": DATE_WIDGET,
            "date_fin": DATE_WIDGET,
            "actif": CHECKBOX_WIDGET,
            "observation": TEXTAREA_WIDGET,
        }

        labels = {
            "personnel": "Personnel",
            "fonction": "Fonction sur le projet",
            "date_debut": "Début de l'affectation",
            "date_fin": "Fin de l'affectation",
            "actif": "Affectation active",
            "observation": "Observation",
        }

    def __init__(
        self,
        *args,
        projet=None,
        **kwargs
    ):

        super().__init__(*args, **kwargs)

        self.projet = projet

        # ----------------------------------------------------
        # PERSONNEL CONSTRUCTION
        # ----------------------------------------------------

        self.fields["personnel"].queryset = (
            Personnel.objects
            .filter(
                typeTravail="Construction"
            )
            .order_by(
                "nom",
                "prenom"
            )
        )

        # ----------------------------------------------------
        # FONCTIONS
        # ----------------------------------------------------

        self.fields["fonction"].choices = (
            EquipeProjet.FONCTION_CHOICES
        )

        # ----------------------------------------------------
        # VALEURS PAR DÉFAUT
        # ----------------------------------------------------

        if projet and not self.is_bound:

            if not self.instance.pk:

                self.fields["date_debut"].initial = (
                    projet.date_debut
                )

                self.fields["date_fin"].initial = (
                    projet.date_fin
                )

                self.fields["actif"].initial = True

    def clean(self):

        cleaned_data = super().clean()

        personnel = cleaned_data.get("personnel")
        date_debut = cleaned_data.get("date_debut")
        date_fin = cleaned_data.get("date_fin")

        # ----------------------------------------------------
        # DATES PAR DÉFAUT
        # ----------------------------------------------------

        if self.projet and not self.instance.pk:

            if not date_debut and self.projet.date_debut:
                date_debut = self.projet.date_debut
                cleaned_data["date_debut"] = date_debut

            if not date_fin and self.projet.date_fin:
                date_fin = self.projet.date_fin
                cleaned_data["date_fin"] = date_fin

        # ----------------------------------------------------
        # DATE FIN >= DATE DEBUT
        # ----------------------------------------------------

        if date_debut and date_fin:

            if date_fin < date_debut:

                self.add_error(
                    "date_fin",
                    (
                        "La fin de l'affectation doit être "
                        "postérieure ou égale au début."
                    ),
                )

        # ----------------------------------------------------
        # LIMITES DU PROJET
        # ----------------------------------------------------

        if self.projet:

            if (
                date_debut
                and date_debut < self.projet.date_debut
            ):

                self.add_error(
                    "date_debut",
                    (
                        "L'affectation ne peut pas commencer "
                        "avant le début du projet."
                    ),
                )

            if (
                date_fin
                and date_fin > self.projet.date_fin
            ):

                self.add_error(
                    "date_fin",
                    (
                        "L'affectation ne peut pas dépasser "
                        "la date de fin du projet."
                    ),
                )

        # ----------------------------------------------------
        # PERSONNEL DÉJÀ AFFECTÉ
        # ----------------------------------------------------

        if personnel and self.projet:

            queryset = EquipeProjet.objects.filter(
                projet=self.projet,
                personnel=personnel,
            )

            if self.instance.pk:

                queryset = queryset.exclude(
                    pk=self.instance.pk
                )

            if queryset.exists():

                self.add_error(
                    "personnel",
                    (
                        "Ce personnel est déjà affecté "
                        "à ce projet."
                    ),
                )

        return cleaned_data


# ============================================================
# VÉHICULE AFFECTÉ AU PROJET
# ============================================================

class VehiculeProjetForm(forms.ModelForm):

    class Meta:
        model = VehiculeProjet

        fields = [
            "vehicule",
            "chauffeur",
            "date_debut",
            "date_fin",
            "kilometrage_initial",
            "kilometrage_final",
            "consommation_km_litre",
            "actif",
            "observation",
        ]

        widgets = {
            "vehicule": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Exemple : Camion MAN 01",
                    "autocomplete": "off",
                }
            ),
            "chauffeur": SELECT_WIDGET,
            "date_debut": DATE_WIDGET,
            "date_fin": DATE_WIDGET,

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

            "actif": CHECKBOX_WIDGET,

            "observation": TEXTAREA_WIDGET,
        }

        labels = {
            "vehicule": "Véhicule",
            "chauffeur": "Chauffeur",
            "date_debut": "Début de l'affectation",
            "date_fin": "Fin de l'affectation",
            "kilometrage_initial": "Kilométrage initial",
            "kilometrage_final": "Kilométrage final",
            "consommation_km_litre": "Consommation (km/l)",
            "actif": "Affectation active",
            "observation": "Observation",
        }

    def __init__(
        self,
        *args,
        projet=None,
        **kwargs
    ):

        super().__init__(*args, **kwargs)

        self.projet = projet

        # ----------------------------------------------------
        # VÉHICULES DISPONIBLES
        # ----------------------------------------------------

        self.fields["vehicule"].queryset = (
            Vehicule.objects
            .filter(
                actif=True
            )
            .order_by(
                "immatriculation"
            )
        )

        # ----------------------------------------------------
        # CHAUFFEURS DE CONSTRUCTION
        # ----------------------------------------------------

        self.fields["chauffeur"].queryset = (
            Personnel.objects
            .filter(
                typeTravail="Construction"
            )
            .order_by(
                "nom",
                "prenom"
            )
        )

        # ----------------------------------------------------
        # VALEURS PAR DÉFAUT
        # ----------------------------------------------------

        if projet and not self.is_bound:

            if not self.instance.pk:

                self.fields["date_debut"].initial = (
                    projet.date_debut
                )

                self.fields["date_fin"].initial = (
                    projet.date_fin
                )

                self.fields["actif"].initial = True

    def clean(self):

        cleaned_data = super().clean()

        vehicule = cleaned_data.get("vehicule")
        chauffeur = cleaned_data.get("chauffeur")

        date_debut = cleaned_data.get("date_debut")
        date_fin = cleaned_data.get("date_fin")

        kilometrage_initial = cleaned_data.get(
            "kilometrage_initial"
        )

        kilometrage_final = cleaned_data.get(
            "kilometrage_final"
        )

        consommation = cleaned_data.get(
            "consommation_km_litre"
        )

        # ----------------------------------------------------
        # DATES PAR DÉFAUT
        # ----------------------------------------------------

        if self.projet and not self.instance.pk:

            if not date_debut:

                date_debut = self.projet.date_debut

                cleaned_data["date_debut"] = date_debut

            if not date_fin:

                date_fin = self.projet.date_fin

                cleaned_data["date_fin"] = date_fin

        # ----------------------------------------------------
        # DATE FIN >= DATE DEBUT
        # ----------------------------------------------------

        if date_debut and date_fin:

            if date_fin < date_debut:

                self.add_error(
                    "date_fin",
                    (
                        "La fin de l'affectation doit être "
                        "postérieure ou égale au début."
                    ),
                )

        # ----------------------------------------------------
        # LIMITES DU PROJET
        # ----------------------------------------------------

        if self.projet:

            if (
                date_debut
                and date_debut < self.projet.date_debut
            ):

                self.add_error(
                    "date_debut",
                    (
                        "L'affectation du véhicule ne peut pas "
                        "commencer avant le début du projet."
                    ),
                )

            if (
                date_fin
                and date_fin > self.projet.date_fin
            ):

                self.add_error(
                    "date_fin",
                    (
                        "L'affectation du véhicule ne peut pas "
                        "dépasser la date de fin du projet."
                    ),
                )

        # ----------------------------------------------------
        # KILOMÉTRAGE
        # ----------------------------------------------------

        if (
            kilometrage_initial is not None
            and kilometrage_initial < 0
        ):

            self.add_error(
                "kilometrage_initial",
                "Le kilométrage initial ne peut pas être négatif.",
            )

        if (
            kilometrage_final is not None
            and kilometrage_final < 0
        ):

            self.add_error(
                "kilometrage_final",
                "Le kilométrage final ne peut pas être négatif.",
            )

        if (
            kilometrage_initial is not None
            and kilometrage_final is not None
            and kilometrage_final < kilometrage_initial
        ):

            self.add_error(
                "kilometrage_final",
                (
                    "Le kilométrage final doit être "
                    "supérieur ou égal au kilométrage initial."
                ),
            )

        # ----------------------------------------------------
        # CONSOMMATION
        # ----------------------------------------------------

        if (
            consommation is not None
            and consommation < 0
        ):

            self.add_error(
                "consommation_km_litre",
                "La consommation ne peut pas être négative.",
            )

        # ----------------------------------------------------
        # VÉHICULE DÉJÀ AFFECTÉ
        # ----------------------------------------------------

        if vehicule and self.projet:

            queryset = VehiculeProjet.objects.filter(
                projet=self.projet,
                vehicule=vehicule,
            )

            if self.instance.pk:

                queryset = queryset.exclude(
                    pk=self.instance.pk
                )

            if queryset.exists():

                self.add_error(
                    "vehicule",
                    (
                        "Ce véhicule est déjà affecté à ce projet."
                    ),
                )

        # ----------------------------------------------------
        # CHAUFFEUR
        # ----------------------------------------------------

        if chauffeur:

            if chauffeur.typeTravail != "Construction":

                self.add_error(
                    "chauffeur",
                    (
                        "Le chauffeur sélectionné doit appartenir au personnel Construction."
                    ),
                )

        return cleaned_data


# ============================================================
# POINT DE CHANTIER
# ============================================================

class PointProjetForm(forms.ModelForm):

    class Meta:
        model = PointProjet

        fields = [
            "nom",
            "localisation",
            "distance_km",
            "travail_prevu",
            "observation",
            "actif",
        ]

        widgets = {
            "nom": TEXT_WIDGET,
            "localisation": TEXT_WIDGET,
            "distance_km": NUMBER_WIDGET,
            "travail_prevu": TEXT_WIDGET,
            "observation": TEXTAREA_WIDGET,
            "actif": CHECKBOX_WIDGET,
        }

        labels = {
            "nom": "Nom du point",
            "localisation": "Localisation",
            "distance_km": "Distance (km)",
            "travail_prevu": "Travail prévu",
            "observation": "Observation",
            "actif": "Point actif",
        }

    def __init__(
        self,
        *args,
        projet=None,
        **kwargs
    ):

        super().__init__(*args, **kwargs)

        self.projet = projet

        self.fields["localisation"].queryset = (
            Personnel.objects
            .filter(
                typeTravail="Construction"
            )
            .order_by(
                "nom",
                "prenom"
            )
        )

    def clean(self):

        cleaned_data = super().clean()

        distance = cleaned_data.get("distance_km")

        if (
            distance is not None
            and distance < 0
        ):

            self.add_error(
                "distance_km",
                "La distance ne peut pas être négative.",
            )

        return cleaned_data


# ============================================================
# RAPPORT PROJET
# ============================================================

class RapportProjetForm(forms.ModelForm):

    class Meta:
        model = RapportProjet

        fields = [
            "date_rapport",
            "titre",
            "avancement",
            "travaux_realises",
            "difficultes",
            "actions_planifiees",
            "observation",
        ]

        widgets = {
            "date_rapport": DATE_WIDGET,
            "titre": TEXT_WIDGET,

            "avancement": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "max": "100",
                }
            ),

            "travaux_realises": TEXTAREA_WIDGET,
            "difficultes": TEXTAREA_WIDGET,
            "actions_planifiees": TEXTAREA_WIDGET,
            "observation": TEXTAREA_WIDGET,
        }

        labels = {
            "date_rapport": "Date du rapport",
            "titre": "Titre",
            "avancement": "Avancement (%)",
            "travaux_realises": "Travaux réalisés",
            "difficultes": "Difficultés rencontrées",
            "actions_planifiees": "Plan d'action",
            "observation": "Observation",
        }

    def __init__(
        self,
        *args,
        projet=None,
        **kwargs
    ):

        super().__init__(*args, **kwargs)

        self.projet = projet

    def clean(self):

        cleaned_data = super().clean()

        avancement = cleaned_data.get("avancement")
        date_rapport = cleaned_data.get("date_rapport")

        if avancement is not None:

            if avancement < 0 or avancement > 100:

                self.add_error(
                    "avancement",
                    (
                        "L'avancement doit être compris "
                        "entre 0 et 100 %."
                    ),
                )

        if self.projet and date_rapport:

            if date_rapport < self.projet.date_debut:

                self.add_error(
                    "date_rapport",
                    (
                        "La date du rapport ne peut pas "
                        "être avant le début du projet."
                    ),
                )

            if date_rapport > self.projet.date_fin:

                self.add_error(
                    "date_rapport",
                    (
                        "La date du rapport ne peut pas "
                        "dépasser la fin du projet."
                    ),
                )

        return cleaned_data


# ============================================================
# RAPPORT TRAVAUX
# ============================================================

class RapportTravailForm(forms.ModelForm):

    class Meta:
        model = RapportTravail

        fields = [
            "point",
            "titre",
            "localisation",
            "date_debut",
            "date_fin",
            "description",
            "photo",
            "observation",
        ]

        widgets = {
            "point": SELECT_WIDGET,
            "titre": TEXT_WIDGET,
            "localisation": TEXT_WIDGET,
            "date_debut": DATE_WIDGET,
            "date_fin": DATE_WIDGET,
            "description": TEXTAREA_WIDGET,
            "photo": FILE_WIDGET,
            "observation": TEXTAREA_WIDGET,
        }

        labels = {
            "point": "Point de chantier",
            "titre": "Titre du travail",
            "localisation": "Localisation",
            "date_debut": "Date de début",
            "date_fin": "Date de fin",
            "description": "Description",
            "photo": "Photo du travail",
            "observation": "Observation",
        }

    def __init__(
        self,
        *args,
        projet=None,
        **kwargs
    ):

        super().__init__(*args, **kwargs)

        self.projet = projet

        if projet:

            self.fields["point"].queryset = (
                PointProjet.objects
                .filter(
                    projet=projet
                )
                .order_by(
                    "nom"
                )
            )

        else:

            self.fields["point"].queryset = (
                PointProjet.objects.none()
            )

    def clean(self):

        cleaned_data = super().clean()

        point = cleaned_data.get("point")
        date_debut = cleaned_data.get("date_debut")
        date_fin = cleaned_data.get("date_fin")

        if point and self.projet:

            if point.projet_id != self.projet.pk:

                self.add_error(
                    "point",
                    (
                        "Le point sélectionné "
                        "n'appartient pas à ce projet."
                    ),
                )

        if (
            date_debut
            and date_fin
            and date_fin < date_debut
        ):

            self.add_error(
                "date_fin",
                (
                    "La date de fin doit être "
                    "postérieure ou égale à la date de début."
                ),
            )

        if self.projet:

            if (
                date_debut
                and date_debut < self.projet.date_debut
            ):

                self.add_error(
                    "date_debut",
                    (
                        "La date de début du travail "
                        "ne peut pas être avant le projet."
                    ),
                )

            if (
                date_fin
                and date_fin > self.projet.date_fin
            ):

                self.add_error(
                    "date_fin",
                    (
                        "La date de fin du travail "
                        "ne peut pas dépasser le projet."
                    ),
                )

        return cleaned_data


# ============================================================
# RAPPORT MATÉRIAU
# ============================================================

class RapportMateriauForm(forms.ModelForm):

    class Meta:
        model = RapportMateriau

        fields = [
            "point",
            "materiau",
            "quantite",
            "point_ravitaillement",
            "date_ravitaillement",
            "observation",
        ]

        widgets = {
            "point": SELECT_WIDGET,
            "materiau": SELECT_WIDGET,
            "quantite": NUMBER_WIDGET,
            "point_ravitaillement": TEXT_WIDGET,
            "date_ravitaillement": DATE_WIDGET,
            "observation": TEXTAREA_WIDGET,
        }

        labels = {
            "point": "Point de chantier",
            "materiau": "Matériau",
            "quantite": "Quantité",
            "point_ravitaillement": "Point de ravitaillement",
            "date_ravitaillement": "Date de ravitaillement",
            "observation": "Observation",
        }

    def __init__(
        self,
        *args,
        projet=None,
        **kwargs
    ):

        super().__init__(*args, **kwargs)

        self.projet = projet

        self.fields["materiau"].queryset = (
            Materiaux.objects
            .all()
            .order_by(
                "libelle"
            )
        )

        if projet:

            self.fields["point"].queryset = (
                PointProjet.objects
                .filter(
                    projet=projet
                )
                .order_by(
                    "nom"
                )
            )

        else:

            self.fields["point"].queryset = (
                PointProjet.objects.none()
            )

    def clean(self):

        cleaned_data = super().clean()

        quantite = cleaned_data.get("quantite")
        point = cleaned_data.get("point")
        date_ravitaillement = cleaned_data.get(
            "date_ravitaillement"
        )

        if (
            quantite is not None
            and quantite <= 0
        ):

            self.add_error(
                "quantite",
                (
                    "La quantité doit être "
                    "supérieure à zéro."
                ),
            )

        if point and self.projet:

            if point.projet_id != self.projet.pk:

                self.add_error(
                    "point",
                    (
                        "Le point sélectionné "
                        "n'appartient pas à ce projet."
                    ),
                )

        if self.projet and date_ravitaillement:

            if (
                date_ravitaillement
                < self.projet.date_debut
            ):

                self.add_error(
                    "date_ravitaillement",
                    (
                        "La date de ravitaillement "
                        "ne peut pas être avant le début du projet."
                    ),
                )

            if (
                date_ravitaillement
                > self.projet.date_fin
            ):

                self.add_error(
                    "date_ravitaillement",
                    (
                        "La date de ravitaillement "
                        "ne peut pas dépasser la fin du projet."
                    ),
                )

        return cleaned_data


#RAPPORT VEHICULE


class RapportVehiculeForm(forms.ModelForm):
    """
    Formulaire de création/modification d'un rapport véhicule
    pour un projet donné.
    """

    class Meta:
        model = RapportVehicule

        fields = [
            "vehicule",
            "chauffeur",
            "date_rapport",
            "kilometrage",
            "etat",
            "description",
            "photo",
            "observation",
        ]

        widgets = {
            "vehicule": SELECT_WIDGET,
            "chauffeur": SELECT_WIDGET,
            "date_rapport": DATE_WIDGET,
            "kilometrage": NUMBER_WIDGET,
            "etat": TEXT_WIDGET,
            "description": TEXTAREA_WIDGET,
            "photo": FILE_WIDGET,
            "observation": TEXTAREA_WIDGET,
        }

        labels = {
            "vehicule": "Véhicule",
            "chauffeur": "Chauffeur",
            "date_rapport": "Date du rapport",
            "kilometrage": "Kilométrage",
            "etat": "État du véhicule",
            "description": "Description",
            "photo": "Photo",
            "observation": "Observation",
        }

    def __init__(self, *args, projet=None, **kwargs):

        super().__init__(*args, **kwargs)

        self.projet = projet

        # ====================================================
        # PROJET
        # ====================================================

        if projet is not None:
            self.instance.projet = projet

        # ====================================================
        # VÉHICULES
        # ====================================================

        if projet is not None:

            self.fields["vehicule"].queryset = (
                Vehicule.objects
                .filter(
                    actif=True,
                    affectations_projets__projet=projet,
                    affectations_projets__actif=True,
                )
                .distinct()
                .order_by("immatriculation")
            )

        else:

            self.fields["vehicule"].queryset = (
                Vehicule.objects
                .filter(
                    actif=True,
                )
                .order_by("immatriculation")
            )

        # ====================================================
        # CHAUFFEURS
        # ====================================================

        if projet is not None:

            self.fields["chauffeur"].queryset = (
                Personnel.objects
                .filter(
                    typeTravail="Construction",
                    affectations_projets__projet=projet,
                    affectations_projets__fonction="CHAUFFEUR",
                    affectations_projets__actif=True,
                )
                .distinct()
                .order_by(
                    "nom",
                    "prenom",
                )
            )

        else:

            self.fields["chauffeur"].queryset = (
                Personnel.objects
                .filter(
                    typeTravail="Construction",
                )
                .order_by(
                    "nom",
                    "prenom",
                )
            )

    def clean(self):

        cleaned_data = super().clean()

        # ====================================================
        # DONNÉES
        # ====================================================

        projet = self.projet

        vehicule = cleaned_data.get(
            "vehicule"
        )

        chauffeur = cleaned_data.get(
            "chauffeur"
        )

        date_rapport = cleaned_data.get(
            "date_rapport"
        )

        kilometrage = cleaned_data.get(
            "kilometrage"
        )

        # ====================================================
        # PROJET
        # ====================================================

        if projet is not None:

            self.instance.projet_id = projet.pk

        # ====================================================
        # VÉHICULE
        # ====================================================

        if vehicule is not None:

            self.instance.vehicule_id = vehicule.pk

        # ====================================================
        # CHAUFFEUR
        # ====================================================

        if chauffeur is not None:

            self.instance.chauffeur_id = chauffeur.pk

        # ====================================================
        # KILOMÉTRAGE
        # ====================================================

        if (
            kilometrage is not None
            and kilometrage < Decimal("0.00")
        ):

            self.add_error(
                "kilometrage",
                "Le kilométrage ne peut pas être négatif.",
            )

        # ====================================================
        # DATE DU RAPPORT
        # ====================================================

        if (
            projet is not None
            and date_rapport
        ):

            if (
                projet.date_debut
                and date_rapport < projet.date_debut
            ):

                self.add_error(
                    "date_rapport",
                    "La date du rapport ne peut pas "
                    "être avant le début du projet.",
                )

            elif (
                projet.date_fin
                and date_rapport > projet.date_fin
            ):

                self.add_error(
                    "date_rapport",
                    "La date du rapport ne peut pas "
                    "dépasser la fin du projet.",
                )

        # ====================================================
        # VÉHICULE AFFECTÉ AU PROJET
        # ====================================================

        if (
            projet is not None
            and vehicule is not None
        ):

            affectation_vehicule = (
                VehiculeProjet.objects
                .filter(
                    projet_id=projet.pk,
                    vehicule_id=vehicule.pk,
                    actif=True,
                )
                .exists()
            )

            if not affectation_vehicule:

                self.add_error(
                    "vehicule",
                    "Ce véhicule n'est pas actuellement "
                    "affecté à ce projet.",
                )

        # ====================================================
        # CHAUFFEUR
        # ====================================================

        if chauffeur is not None:

            if chauffeur.typeTravail != "Construction":

                self.add_error(
                    "chauffeur",
                    "Le chauffeur sélectionné doit appartenir "
                    "au personnel Construction.",
                )

            if projet is not None:

                affectation_chauffeur = (
                    EquipeProjet.objects
                    .filter(
                        projet_id=projet.pk,
                        personnel_id=chauffeur.pk,
                        fonction="CHAUFFEUR",
                        actif=True,
                    )
                    .exists()
                )

                if not affectation_chauffeur:

                    self.add_error(
                        "chauffeur",
                        "Ce personnel n'est pas actuellement "
                        "affecté comme chauffeur à ce projet.",
                    )

        return cleaned_data



# ============================================================
# FORMULAIRE ACTIVITÉ TRANSPORT DU PROJET
# ============================================================

class ActiviteTransportProjetForm(forms.ModelForm):
    """
    Formulaire de gestion des activités de transport d'un projet.

    Compatible avec le modèle actuel :

        ActiviteTransportProjet

    Le projet peut être fourni depuis la vue avec :

        ActiviteTransportProjetForm(projet=projet)

    Le champ projet reste affiché dans le formulaire, mais il est
    automatiquement initialisé avec le projet fourni.
    """

    class Meta:
        model = ActiviteTransportProjet

        fields = [
            "projet",
            "vehicule",
            "chauffeur",
            "type_transport",
            "mission",
            "lieu_depart",
            "destination",
            "distance_km",
            "kilometrage_initial",
            "kilometrage_final",
            "consommation_km_litre",
            "quantite",
            "unite",
            "date_transport",
            "observation",
        ]

        widgets = {
            "projet": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "vehicule": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ex. Camion Mercedes",
                }
            ),

            "chauffeur": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "type_transport": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "mission": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ex. Transport de matériaux",
                }
            ),

            "lieu_depart": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ex. Magasin central",
                }
            ),

            "destination": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Ex. Point A - Zoto",
                }
            ),

            "distance_km": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
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
                    "placeholder": "Ex. 5.50 km/L",
                }
            ),

            "quantite": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                }
            ),

            "unite": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "kg, tonne, sac, personne...",
                }
            ),

            "date_transport": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
            ),

            "observation": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Observation...",
                }
            ),
        }

    def __init__(self, *args, **kwargs):

        # --------------------------------------------------------
        # Récupération du projet envoyé par la vue
        # --------------------------------------------------------

        projet = kwargs.pop("projet", None)

        super().__init__(*args, **kwargs)

        # --------------------------------------------------------
        # Projet
        # --------------------------------------------------------

        self.fields["projet"].queryset = (
            Projet.objects
            .all()
            .order_by("-date_debut", "titre")
        )

        if projet:

            self.fields["projet"].initial = projet.pk

            # Le projet est imposé par la vue.
            self.fields["projet"].disabled = True

        # --------------------------------------------------------
        # Chauffeurs Construction
        # --------------------------------------------------------

        self.fields["chauffeur"].queryset = (
            Personnel.objects
            .filter(
                typeTravail="Construction",
            )
            .order_by(
                "nom",
                "prenom",
            )
        )

        # --------------------------------------------------------
        # Si un projet est connu, filtrer les chauffeurs
        # affectés à ce projet.
        #
        # IMPORTANT :
        # On utilise le related_name de EquipeProjet.
        # Cette partie sera adaptée si ton modèle possède
        # un autre related_name.
        # --------------------------------------------------------

        if projet:

            self.fields["chauffeur"].queryset = (
                Personnel.objects
                .filter(
                    typeTravail="Construction",
                    equipeprojet__projet=projet,
                    equipeprojet__fonction="CHAUFFEUR",
                    equipeprojet__actif=True,
                )
                .distinct()
                .order_by(
                    "nom",
                    "prenom",
                )
            )

        # --------------------------------------------------------
        # Date initiale
        # --------------------------------------------------------

        if (
            self.instance
            and self.instance.pk
            and self.instance.date_transport
        ):
            self.initial["date_transport"] = (
                self.instance.date_transport.strftime(
                    "%Y-%m-%d"
                )
            )

        # --------------------------------------------------------
        # Champs obligatoires
        # --------------------------------------------------------

        for field_name in [
            "projet",
            "vehicule",
            "chauffeur",
            "type_transport",
            "mission",
            "lieu_depart",
            "destination",
            "distance_km",
            "kilometrage_initial",
            "kilometrage_final",
            "consommation_km_litre",
            "quantite",
            "date_transport",
        ]:
            self.fields[field_name].required = True

        self.fields["unite"].required = False
        self.fields["observation"].required = False

    # ============================================================
    # PROJET
    # ============================================================

    def clean_projet(self):

        projet = self.cleaned_data.get("projet")

        if not projet:
            raise forms.ValidationError(
                "Veuillez sélectionner un projet."
            )

        return projet

    # ============================================================
    # CHAUFFEUR
    # ============================================================

    def clean_chauffeur(self):

        chauffeur = self.cleaned_data.get("chauffeur")

        if not chauffeur:
            raise forms.ValidationError(
                "Veuillez sélectionner un chauffeur."
            )

        if chauffeur.typeTravail != "Construction":
            raise forms.ValidationError(
                "Le chauffeur doit appartenir au personnel "
                "Construction."
            )

        projet = self.cleaned_data.get("projet")

        if projet:

            affectation = (
                EquipeProjet.objects
                .filter(
                    projet=projet,
                    personnel=chauffeur,
                    fonction="CHAUFFEUR",
                    actif=True,
                )
                .exists()
            )

            if not affectation:
                raise forms.ValidationError(
                    "Ce personnel n'est pas affecté comme "
                    "chauffeur à ce projet."
                )

        return chauffeur

    # ============================================================
    # DISTANCE
    # ============================================================

    def clean_distance_km(self):

        value = self.cleaned_data.get("distance_km")

        if value is not None and value < 0:
            raise forms.ValidationError(
                "La distance ne peut pas être négative."
            )

        return value

    # ============================================================
    # KILOMÉTRAGE INITIAL
    # ============================================================

    def clean_kilometrage_initial(self):

        value = self.cleaned_data.get(
            "kilometrage_initial"
        )

        if value is not None and value < 0:
            raise forms.ValidationError(
                "Le kilométrage initial ne peut pas être négatif."
            )

        return value

    # ============================================================
    # KILOMÉTRAGE FINAL
    # ============================================================

    def clean_kilometrage_final(self):

        value = self.cleaned_data.get(
            "kilometrage_final"
        )

        initial = self.cleaned_data.get(
            "kilometrage_initial"
        )

        if value is not None and value < 0:
            raise forms.ValidationError(
                "Le kilométrage final ne peut pas être négatif."
            )

        if (
            initial is not None
            and value is not None
            and value < initial
        ):
            raise forms.ValidationError(
                "Le kilométrage final doit être supérieur "
                "ou égal au kilométrage initial."
            )

        return value

    # ============================================================
    # CONSOMMATION
    # ============================================================

    def clean_consommation_km_litre(self):

        value = self.cleaned_data.get(
            "consommation_km_litre"
        )

        if value is not None and value < 0:
            raise forms.ValidationError(
                "La consommation ne peut pas être négative."
            )

        return value

    # ============================================================
    # QUANTITÉ
    # ============================================================

    def clean_quantite(self):

        value = self.cleaned_data.get("quantite")

        if value is not None and value < 0:
            raise forms.ValidationError(
                "La quantité ne peut pas être négative."
            )

        return value

    # ============================================================
    # DATE TRANSPORT
    # ============================================================

    def clean_date_transport(self):

        date_transport = self.cleaned_data.get(
            "date_transport"
        )

        projet = self.cleaned_data.get("projet")

        if not date_transport:
            raise forms.ValidationError(
                "La date du transport est obligatoire."
            )

        if projet:

            if (
                projet.date_debut
                and date_transport < projet.date_debut
            ):
                raise forms.ValidationError(
                    "La date du transport ne peut pas être "
                    "avant le début du projet."
                )

            if (
                projet.date_fin
                and date_transport > projet.date_fin
            ):
                raise forms.ValidationError(
                    "La date du transport ne peut pas dépasser "
                    "la date de fin du projet."
                )

        return date_transport

    # ============================================================
    # CLEAN GLOBAL
    # ============================================================

    def clean(self):

        cleaned_data = super().clean()

        projet = cleaned_data.get("projet")
        chauffeur = cleaned_data.get("chauffeur")
        date_transport = cleaned_data.get("date_transport")

        # --------------------------------------------------------
        # Date / projet
        # --------------------------------------------------------

        if projet and date_transport:

            if (
                projet.date_debut
                and date_transport < projet.date_debut
            ):
                self.add_error(
                    "date_transport",
                    "La date du transport est antérieure "
                    "au début du projet.",
                )

            if (
                projet.date_fin
                and date_transport > projet.date_fin
            ):
                self.add_error(
                    "date_transport",
                    "La date du transport dépasse "
                    "la fin du projet.",
                )

        # --------------------------------------------------------
        # Chauffeur / équipe
        # --------------------------------------------------------

        if projet and chauffeur:

            affectation = (
                EquipeProjet.objects
                .filter(
                    projet=projet,
                    personnel=chauffeur,
                    fonction="CHAUFFEUR",
                    actif=True,
                )
                .exists()
            )

            if not affectation:

                self.add_error(
                    "chauffeur",
                    "Ce personnel n'est pas affecté comme "
                    "chauffeur à ce projet.",
                )

        # --------------------------------------------------------
        # Cohérence compteur
        # --------------------------------------------------------

        kilometrage_initial = cleaned_data.get(
            "kilometrage_initial"
        )

        kilometrage_final = cleaned_data.get(
            "kilometrage_final"
        )

        if (
            kilometrage_initial is not None
            and kilometrage_final is not None
            and kilometrage_final >= kilometrage_initial
        ):

            cleaned_data["_kilometres_compteur"] = (
                kilometrage_final
                - kilometrage_initial
            )

        return cleaned_data
