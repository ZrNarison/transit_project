from django import forms
from django.utils import timezone

from personnel.models import Personnel
from materiaux.models import Materiaux, Vehicule

from .models import (
    Projet,
    EquipeProjet,
    PointProjet,
    RapportProjet,
    RapportTravail,
    RapportMateriau,
    VehiculeProjet,
    RapportVehicule,
    ActiviteTransportProjet,
    PersonnelExecutionProjet,
    MouvementPersonnelProjet,
    MouvementVehiculeProjet,
    EquipageProjet,
    AvanceEquipeProjet,
    EquipeMateriauProjet,
    VehiculeLourdsProjet,
)


# ============================================================
# WIDGETS BOOTSTRAP
# ============================================================

DATE_WIDGET = forms.DateInput(
    format="%Y-%m-%d",
    attrs={
        "class": "form-control",
        "type": "date",
    },
)

DATETIME_WIDGET = forms.DateTimeInput(
    format="%Y-%m-%dT%H:%M",
    attrs={
        "class": "form-control",
        "type": "datetime-local",
    },
)

TEXT_WIDGET = forms.TextInput(
    attrs={
        "class": "form-control",
    },
)

TEXTAREA_WIDGET = forms.Textarea(
    attrs={
        "class": "form-control",
        "rows": 4,
    },
)

SELECT_WIDGET = forms.Select(
    attrs={
        "class": "form-select",
    },
)

NUMBER_WIDGET = forms.NumberInput(
    attrs={
        "class": "form-control",
        "step": "0.01",
    },
)

CHECKBOX_WIDGET = forms.CheckboxInput(
    attrs={
        "class": "form-check-input",
    },
)

FILE_WIDGET = forms.ClearableFileInput(
    attrs={
        "class": "form-control",
    },
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

        if date_debut and date_fin and date_fin < date_debut:
            self.add_error(
                "date_fin",
                "La date de fin doit être supérieure "
                "ou égale à la date de début.",
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

    def __init__(self, *args, projet=None, **kwargs):

        super().__init__(*args, **kwargs)

        self.projet = projet

        self.fields["personnel"].queryset = (
            Personnel.objects
            .filter(typeTravail="Construction")
            .order_by("nom", "prenom")
        )

        if projet and not self.is_bound and not self.instance.pk:

            self.fields["date_debut"].initial = projet.date_debut
            self.fields["date_fin"].initial = projet.date_fin
            self.fields["actif"].initial = True

    def clean(self):

        cleaned_data = super().clean()

        personnel = cleaned_data.get("personnel")
        date_debut = cleaned_data.get("date_debut")
        date_fin = cleaned_data.get("date_fin")

        if self.projet and not self.instance.pk:

            if not date_debut:
                date_debut = self.projet.date_debut
                cleaned_data["date_debut"] = date_debut

            if not date_fin:
                date_fin = self.projet.date_fin
                cleaned_data["date_fin"] = date_fin

        if date_debut and date_fin and date_fin < date_debut:
            self.add_error(
                "date_fin",
                "La fin de l'affectation doit être "
                "postérieure ou égale au début.",
            )

        if self.projet:

            if (
                date_debut
                and self.projet.date_debut
                and date_debut < self.projet.date_debut
            ):
                self.add_error(
                    "date_debut",
                    "L'affectation ne peut pas commencer "
                    "avant le début du projet.",
                )

            if (
                date_fin
                and self.projet.date_fin
                and date_fin > self.projet.date_fin
            ):
                self.add_error(
                    "date_fin",
                    "L'affectation ne peut pas dépasser "
                    "la date de fin du projet.",
                )

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
                    "Ce personnel est déjà affecté "
                    "à ce projet.",
                )

        return cleaned_data

# ============================================================
# VEHICULE / ENGIN PROJET
# ============================================================

class VehiculeProjetForm(forms.ModelForm):

    class Meta:
        model = VehiculeProjet

        fields = [
            "vehicule",
            "type_vehicule",
            "chauffeur",
            "date_debut",
            "date_fin",

            # ROUTIER
            "kilometrage_initial",
            "kilometrage_final",
            "consommation_km_litre",

            # ENGIN
            "heures_initiales",
            "heures_finales",
            "consommation_heure_litre",

            "actif",
            "observation",
        ]

        widgets = {

            "vehicule": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": (
                        "Ex. Camion MAN 01 / Pelle CAT 320"
                    ),
                    "autocomplete": "off",
                }
            ),

            "type_vehicule": SELECT_WIDGET,

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
                    "placeholder": "Ex. 4.50",
                }
            ),

            "heures_initiales": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Ex. 1250.00",
                }
            ),

            "heures_finales": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Ex. 1287.50",
                }
            ),

            "consommation_heure_litre": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Ex. 8.00 L/h",
                }
            ),

            "actif": CHECKBOX_WIDGET,

            "observation": TEXTAREA_WIDGET,
        }

        labels = {

            "vehicule": (
                "Véhicule / Engin / Immatriculation"
            ),

            "type_vehicule": (
                "Type de véhicule"
            ),

            "chauffeur": (
                "Chauffeur / Conducteur"
            ),

            "date_debut": (
                "Début de l'affectation"
            ),

            "date_fin": (
                "Fin de l'affectation"
            ),

            "kilometrage_initial": (
                "Kilométrage initial"
            ),

            "kilometrage_final": (
                "Kilométrage final"
            ),

            "consommation_km_litre": (
                "Consommation (km/L)"
            ),

            "heures_initiales": (
                "Compteur horaire initial"
            ),

            "heures_finales": (
                "Compteur horaire final"
            ),

            "consommation_heure_litre": (
                "Consommation (L/h)"
            ),

            "actif": (
                "Affectation active"
            ),

            "observation": (
                "Observation"
            ),
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
        # CHAUFFEUR / CONDUCTEUR
        # ----------------------------------------------------

        self.fields[
            "chauffeur"
        ].queryset = (
            Personnel.objects
            .all()
            .order_by(
                "nom",
                "prenom",
            )
        )

        # ----------------------------------------------------
        # DATES DU PROJET
        # ----------------------------------------------------

        if (
            projet
            and not self.is_bound
            and not self.instance.pk
        ):

            self.fields[
                "date_debut"
            ].initial = projet.date_debut

            self.fields[
                "date_fin"
            ].initial = projet.date_fin

            self.fields[
                "actif"
            ].initial = True

    def clean(self):

        cleaned_data = super().clean()

        type_vehicule = cleaned_data.get(
            "type_vehicule"
        )

        vehicule = cleaned_data.get(
            "vehicule"
        )

        date_debut = cleaned_data.get(
            "date_debut"
        )

        date_fin = cleaned_data.get(
            "date_fin"
        )

        kilometrage_initial = cleaned_data.get(
            "kilometrage_initial"
        )

        kilometrage_final = cleaned_data.get(
            "kilometrage_final"
        )

        consommation_km_litre = cleaned_data.get(
            "consommation_km_litre"
        )

        heures_initiales = cleaned_data.get(
            "heures_initiales"
        )

        heures_finales = cleaned_data.get(
            "heures_finales"
        )

        consommation_heure_litre = cleaned_data.get(
            "consommation_heure_litre"
        )

        # ----------------------------------------------------
        # DATES AUTOMATIQUES
        # ----------------------------------------------------

        if (
            self.projet
            and not self.instance.pk
        ):

            if not date_debut:

                date_debut = (
                    self.projet.date_debut
                )

                cleaned_data[
                    "date_debut"
                ] = date_debut

            if not date_fin:

                date_fin = (
                    self.projet.date_fin
                )

                cleaned_data[
                    "date_fin"
                ] = date_fin

        # ----------------------------------------------------
        # DATES
        # ----------------------------------------------------

        if (
            date_debut
            and date_fin
            and date_fin < date_debut
        ):

            self.add_error(
                "date_fin",
                "La fin de l'affectation doit être "
                "postérieure ou égale au début.",
            )

        if self.projet:

            if (
                date_debut
                and self.projet.date_debut
                and date_debut < self.projet.date_debut
            ):

                self.add_error(
                    "date_debut",
                    "L'affectation ne peut pas commencer "
                    "avant le début du projet.",
                )

            if (
                date_fin
                and self.projet.date_fin
                and date_fin > self.projet.date_fin
            ):

                self.add_error(
                    "date_fin",
                    "L'affectation ne peut pas dépasser "
                    "la date de fin du projet.",
                )

        # ----------------------------------------------------
        # ROUTIER
        # ----------------------------------------------------

        if type_vehicule == "ROUTIER":

            if (
                kilometrage_initial is not None
                and kilometrage_initial < 0
            ):

                self.add_error(
                    "kilometrage_initial",
                    "Le kilométrage initial "
                    "ne peut pas être négatif.",
                )

            if (
                kilometrage_final is not None
                and kilometrage_final < 0
            ):

                self.add_error(
                    "kilometrage_final",
                    "Le kilométrage final "
                    "ne peut pas être négatif.",
                )

            if (
                kilometrage_initial is not None
                and kilometrage_final is not None
                and kilometrage_final
                < kilometrage_initial
            ):

                self.add_error(
                    "kilometrage_final",
                    "Le kilométrage final doit être "
                    "supérieur ou égal au kilométrage initial.",
                )

            if (
                consommation_km_litre is not None
                and consommation_km_litre < 0
            ):

                self.add_error(
                    "consommation_km_litre",
                    "La consommation ne peut pas "
                    "être négative.",
                )

        # ----------------------------------------------------
        # ENGIN
        # ----------------------------------------------------

        elif type_vehicule == "ENGIN":

            if (
                heures_initiales is not None
                and heures_initiales < 0
            ):

                self.add_error(
                    "heures_initiales",
                    "Les heures initiales "
                    "ne peuvent pas être négatives.",
                )

            if (
                heures_finales is not None
                and heures_finales < 0
            ):

                self.add_error(
                    "heures_finales",
                    "Les heures finales "
                    "ne peuvent pas être négatives.",
                )

            if (
                heures_initiales is not None
                and heures_finales is not None
                and heures_finales
                < heures_initiales
            ):

                self.add_error(
                    "heures_finales",
                    "Les heures finales doivent être "
                    "supérieures ou égales aux heures initiales.",
                )

            if (
                consommation_heure_litre is not None
                and consommation_heure_litre < 0
            ):

                self.add_error(
                    "consommation_heure_litre",
                    "La consommation L/h "
                    "ne peut pas être négative.",
                )

        # ----------------------------------------------------
        # VÉHICULE DUPLIQUÉ DANS LE PROJET
        # ----------------------------------------------------

        if vehicule and self.projet:

            queryset = (
                VehiculeProjet.objects
                .filter(
                    projet=self.projet,
                    vehicule=vehicule,
                )
            )

            if self.instance.pk:

                queryset = queryset.exclude(
                    pk=self.instance.pk
                )

            if queryset.exists():

                self.add_error(
                    "vehicule",
                    "Ce véhicule / engin est déjà "
                    "affecté à ce projet.",
                )

        return cleaned_data


# ============================================================
# MOUVEMENT VÉHICULE
# ============================================================

class MouvementVehiculeProjetForm(forms.ModelForm):

    class Meta:
        model = MouvementVehiculeProjet

        fields = [
            "vehicule_projet",
            "date_mouvement",
            "point_depart",
            "point_arrivee",
            "kilometrage_initial",
            "kilometrage_final",
            "heures_initiales",
            "heures_finales",
            "observation",
        ]

        widgets = {
            "vehicule_projet": SELECT_WIDGET,
            "date_mouvement": DATETIME_WIDGET,
            "point_depart": SELECT_WIDGET,
            "point_arrivee": SELECT_WIDGET,

            "kilometrage_initial": NUMBER_WIDGET,
            "kilometrage_final": NUMBER_WIDGET,

            "heures_initiales": NUMBER_WIDGET,
            "heures_finales": NUMBER_WIDGET,

            "observation": TEXTAREA_WIDGET,
        }

        labels = {
            "vehicule_projet": "Véhicule / Engin",
            "date_mouvement": "Date du mouvement",
            "point_depart": "Point de départ",
            "point_arrivee": "Point d'arrivée",
            "kilometrage_initial": "Km initial",
            "kilometrage_final": "Km final",
            "heures_initiales": "Heures initiales",
            "heures_finales": "Heures finales",
            "observation": "Observation",
        }

    def __init__(self, *args, projet=None, **kwargs):

        super().__init__(*args, **kwargs)

        self.fields["vehicule_projet"].queryset = (
            VehiculeProjet.objects
            .filter(projet=projet)
            .select_related("projet", "chauffeur")
            .order_by("vehicule")
            if projet
            else VehiculeProjet.objects.none()
        )

        self.fields["point_depart"].queryset = (
            PointProjet.objects
            .filter(projet=projet)
            .order_by("nom")
            if projet
            else PointProjet.objects.none()
        )

        self.fields["point_arrivee"].queryset = (
            PointProjet.objects
            .filter(projet=projet)
            .order_by("nom")
            if projet
            else PointProjet.objects.none()
        )

    def clean(self):

        cleaned_data = super().clean()

        vehicule = cleaned_data.get(
            "vehicule_projet"
        )

        if not vehicule:
            return cleaned_data

        # ----------------------------------------------------
        # ENGIN
        # ----------------------------------------------------

        if vehicule.type_vehicule == "ENGIN":

            self.fields[
                "kilometrage_initial"
            ].required = False

            self.fields[
                "kilometrage_final"
            ].required = False

        # ----------------------------------------------------
        # ROUTIER
        # ----------------------------------------------------

        else:

            self.fields[
                "heures_initiales"
            ].required = False

            self.fields[
                "heures_finales"
            ].required = False

        return cleaned_data


# ============================================================
# MOUVEMENT PERSONNEL
# ============================================================

class MouvementPersonnelProjetForm(forms.ModelForm):

    class Meta:
        model = MouvementPersonnelProjet

        fields = [
            "personnel_execution",
            "date_mouvement",
            "point",
            "activite",
            "date_debut",
            "date_fin",
            "observation",
        ]

        widgets = {
            "personnel_execution": SELECT_WIDGET,
            "date_mouvement": DATETIME_WIDGET,
            "point": SELECT_WIDGET,
            "activite": TEXT_WIDGET,
            "date_debut": DATETIME_WIDGET,
            "date_fin": DATETIME_WIDGET,
            "observation": TEXTAREA_WIDGET,
        }

        labels = {
            "personnel_execution": "Personnel",
            "date_mouvement": "Date du mouvement",
            "point": "Point de chantier",
            "activite": "Activité",
            "date_debut": "Début",
            "date_fin": "Fin",
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
        # PERSONNEL D'EXÉCUTION
        # ----------------------------------------------------

        self.fields["personnel_execution"].queryset = (
            PersonnelExecutionProjet.objects
            .filter(projet=projet)
            .select_related(
                "projet",
                "personnel",
            )
            .order_by("nom")
            if projet
            else PersonnelExecutionProjet.objects.none()
        )

        # ----------------------------------------------------
        # POINTS DU PROJET
        # ----------------------------------------------------

        self.fields["point"].queryset = (
            PointProjet.objects
            .filter(projet=projet)
            .order_by("nom")
            if projet
            else PointProjet.objects.none()
        )

        # ----------------------------------------------------
        # DATE PAR DÉFAUT
        # ----------------------------------------------------

        if (
            projet
            and not self.is_bound
            and not self.instance.pk
        ):
            self.fields["date_mouvement"].initial = (
                timezone.now()
            )

    def clean(self):

        cleaned_data = super().clean()

        personnel_execution = cleaned_data.get(
            "personnel_execution"
        )

        point = cleaned_data.get("point")

        date_mouvement = cleaned_data.get(
            "date_mouvement"
        )

        date_debut = cleaned_data.get(
            "date_debut"
        )

        date_fin = cleaned_data.get(
            "date_fin"
        )

        # ----------------------------------------------------
        # PERSONNEL
        # ----------------------------------------------------

        if self.projet and personnel_execution:

            if (
                personnel_execution.projet_id
                != self.projet.pk
            ):
                self.add_error(
                    "personnel_execution",
                    "Ce personnel d'exécution "
                    "n'appartient pas à ce projet.",
                )

        # ----------------------------------------------------
        # POINT
        # ----------------------------------------------------

        if self.projet and point:

            if point.projet_id != self.projet.pk:

                self.add_error(
                    "point",
                    "Ce point n'appartient pas à ce projet.",
                )

        # ----------------------------------------------------
        # POINT ET PERSONNEL : MÊME PROJET
        # ----------------------------------------------------

        if personnel_execution and point:

            if (
                personnel_execution.projet_id
                != point.projet_id
            ):
                self.add_error(
                    "point",
                    "Le point et le personnel doivent "
                    "appartenir au même projet.",
                )

        # ----------------------------------------------------
        # DATE DE MOUVEMENT
        # ----------------------------------------------------

        if self.projet and date_mouvement:

            date_mouvement_date = date_mouvement.date()

            if (
                self.projet.date_debut
                and date_mouvement_date
                < self.projet.date_debut
            ):
                self.add_error(
                    "date_mouvement",
                    "La date du mouvement ne peut pas "
                    "être avant le début du projet.",
                )

            if (
                self.projet.date_fin
                and date_mouvement_date
                > self.projet.date_fin
            ):
                self.add_error(
                    "date_mouvement",
                    "La date du mouvement ne peut pas "
                    "dépasser la fin du projet.",
                )

        # ----------------------------------------------------
        # DATES D'ACTIVITÉ
        # ----------------------------------------------------

        if (
            date_debut
            and date_fin
            and date_fin < date_debut
        ):
            self.add_error(
                "date_fin",
                "La date de fin doit être "
                "postérieure ou égale à la date de début.",
            )

        # ----------------------------------------------------
        # DÉBUT DE L'ACTIVITÉ
        # ----------------------------------------------------

        if self.projet and date_debut:

            if (
                self.projet.date_debut
                and date_debut.date()
                < self.projet.date_debut
            ):
                self.add_error(
                    "date_debut",
                    "Le début de l'activité ne peut pas "
                    "être avant le début du projet.",
                )

            if (
                self.projet.date_fin
                and date_debut.date()
                > self.projet.date_fin
            ):
                self.add_error(
                    "date_debut",
                    "Le début de l'activité ne peut pas "
                    "dépasser la fin du projet.",
                )

        # ----------------------------------------------------
        # FIN DE L'ACTIVITÉ
        # ----------------------------------------------------

        if self.projet and date_fin:

            if (
                self.projet.date_debut
                and date_fin.date()
                < self.projet.date_debut
            ):
                self.add_error(
                    "date_fin",
                    "La fin de l'activité ne peut pas "
                    "être avant le début du projet.",
                )

            if (
                self.projet.date_fin
                and date_fin.date()
                > self.projet.date_fin
            ):
                self.add_error(
                    "date_fin",
                    "La fin de l'activité ne peut pas "
                    "dépasser la fin du projet.",
                )

        return cleaned_data


# ============================================================
# POINT PROJET
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

    def clean_distance_km(self):

        value = self.cleaned_data.get("distance_km")

        if value is not None and value < 0:
            raise forms.ValidationError(
                "La distance ne peut pas être négative."
            )

        return value


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

    def __init__(self, *args, projet=None, **kwargs):

        super().__init__(*args, **kwargs)

        self.projet = projet

    def clean(self):

        cleaned_data = super().clean()

        avancement = cleaned_data.get("avancement")
        date_rapport = cleaned_data.get("date_rapport")

        if avancement is not None and not 0 <= avancement <= 100:
            self.add_error(
                "avancement",
                "L'avancement doit être compris entre 0 et 100 %.",
            )

        if self.projet and date_rapport:

            if (
                self.projet.date_debut
                and date_rapport < self.projet.date_debut
            ):
                self.add_error(
                    "date_rapport",
                    "La date du rapport ne peut pas être "
                    "avant le début du projet.",
                )

            if (
                self.projet.date_fin
                and date_rapport > self.projet.date_fin
            ):
                self.add_error(
                    "date_rapport",
                    "La date du rapport ne peut pas dépasser "
                    "la fin du projet.",
                )

        return cleaned_data


# ============================================================
# RAPPORT TRAVAIL
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

    def __init__(self, *args, projet=None, **kwargs):

        super().__init__(*args, **kwargs)

        self.projet = projet

        if projet:
            self.fields["point"].queryset = (
                PointProjet.objects
                .filter(projet=projet)
                .order_by("nom")
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
                    "Le point sélectionné n'appartient pas à ce projet.",
                )

        if date_debut and date_fin and date_fin < date_debut:
            self.add_error(
                "date_fin",
                "La date de fin doit être postérieure "
                "ou égale à la date de début.",
            )

        if self.projet:

            if (
                date_debut
                and self.projet.date_debut
                and date_debut < self.projet.date_debut
            ):
                self.add_error(
                    "date_debut",
                    "La date de début du travail ne peut pas "
                    "être avant le projet.",
                )

            if (
                date_fin
                and self.projet.date_fin
                and date_fin > self.projet.date_fin
            ):
                self.add_error(
                    "date_fin",
                    "La date de fin du travail ne peut pas "
                    "dépasser le projet.",
                )

        return cleaned_data


# ============================================================
# RAPPORT MATERIAU
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

    def __init__(self, *args, projet=None, **kwargs):

        super().__init__(*args, **kwargs)

        self.projet = projet

        self.fields["materiau"].queryset = (
            Materiaux.objects
            .all()
            .order_by("libelle")
        )

        if projet:
            self.fields["point"].queryset = (
                PointProjet.objects
                .filter(projet=projet)
                .order_by("nom")
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

        if quantite is not None and quantite <= 0:
            self.add_error(
                "quantite",
                "La quantité doit être supérieure à zéro.",
            )

        if point and self.projet:
            if point.projet_id != self.projet.pk:
                self.add_error(
                    "point",
                    "Le point sélectionné n'appartient pas à ce projet.",
                )

        if self.projet and date_ravitaillement:

            if (
                self.projet.date_debut
                and date_ravitaillement < self.projet.date_debut
            ):
                self.add_error(
                    "date_ravitaillement",
                    "La date de ravitaillement ne peut pas "
                    "être avant le début du projet.",
                )

            if (
                self.projet.date_fin
                and date_ravitaillement > self.projet.date_fin
            ):
                self.add_error(
                    "date_ravitaillement",
                    "La date de ravitaillement ne peut pas "
                    "dépasser la fin du projet.",
                )

        return cleaned_data


# ============================================================
# RAPPORT VEHICULE
# ============================================================

class RapportVehiculeForm(forms.ModelForm):

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

        # ----------------------------------------------------
        # VEHICULES
        # ----------------------------------------------------

        if projet:

            self.fields["vehicule"].queryset = (
                Vehicule.objects
                .filter(
                    actif=True,
                )
                .order_by("immatriculation")
            )

        else:

            self.fields["vehicule"].queryset = (
                Vehicule.objects
                .filter(actif=True)
                .order_by("immatriculation")
            )

        # ----------------------------------------------------
        # PERSONNEL
        # ----------------------------------------------------

        self.fields["chauffeur"].queryset = (
            Personnel.objects
            .all()
            .order_by("nom", "prenom")
        )

    def clean(self):

        cleaned_data = super().clean()

        projet = self.projet
        vehicule = cleaned_data.get("vehicule")
        chauffeur = cleaned_data.get("chauffeur")
        date_rapport = cleaned_data.get("date_rapport")
        kilometrage = cleaned_data.get("kilometrage")

        if kilometrage is not None and kilometrage < 0:
            self.add_error(
                "kilometrage",
                "Le kilométrage ne peut pas être négatif.",
            )

        if projet and date_rapport:

            if (
                projet.date_debut
                and date_rapport < projet.date_debut
            ):
                self.add_error(
                    "date_rapport",
                    "La date du rapport ne peut pas être "
                    "avant le début du projet.",
                )

            if (
                projet.date_fin
                and date_rapport > projet.date_fin
            ):
                self.add_error(
                    "date_rapport",
                    "La date du rapport ne peut pas dépasser "
                    "la fin du projet.",
                )

        # ----------------------------------------------------
        # VEHICULE
        #
        # RapportVehicule utilise materiaux.Vehicule.
        # VehiculeProjet utilise le matricule en texte.
        # ----------------------------------------------------

        if projet and vehicule:

            matricule = getattr(
                vehicule,
                "immatriculation",
                None,
            )

            if matricule is None:
                matricule = str(vehicule)

            affectation = (
                VehiculeProjet.objects
                .filter(
                    projet=projet,
                    vehicule=str(matricule),
                    actif=True,
                )
                .exists()
            )

            if not affectation:

                self.add_error(
                    "vehicule",
                    "Ce véhicule n'est pas actuellement "
                    "affecté à ce projet.",
                )

        # ----------------------------------------------------
        # CHAUFFEUR
        # ----------------------------------------------------

        if chauffeur and projet:

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

        return cleaned_data


# ============================================================
# ACTIVITE TRANSPORT PROJET
# ============================================================

class ActiviteTransportProjetForm(forms.ModelForm):

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
            "projet": SELECT_WIDGET,
            "vehicule": SELECT_WIDGET,
            "chauffeur": SELECT_WIDGET,
            "type_transport": SELECT_WIDGET,
            "mission": TEXT_WIDGET,
            "lieu_depart": TEXT_WIDGET,
            "destination": TEXT_WIDGET,
            "distance_km": NUMBER_WIDGET,
            "kilometrage_initial": NUMBER_WIDGET,
            "kilometrage_final": NUMBER_WIDGET,
            "consommation_km_litre": NUMBER_WIDGET,
            "quantite": NUMBER_WIDGET,
            "unite": TEXT_WIDGET,
            "date_transport": DATE_WIDGET,
            "observation": TEXTAREA_WIDGET,
        }

        labels = {
            "projet": "Projet",
            "vehicule": "Véhicule",
            "chauffeur": "Chauffeur",
            "type_transport": "Type de transport",
            "mission": "Mission",
            "lieu_depart": "Lieu de départ",
            "destination": "Destination",
            "distance_km": "Distance (km)",
            "kilometrage_initial": "Kilométrage initial",
            "kilometrage_final": "Kilométrage final",
            "consommation_km_litre": "Consommation (km/l)",
            "quantite": "Quantité",
            "unite": "Unité",
            "date_transport": "Date du transport",
            "observation": "Observation",
        }

    def __init__(self, *args, projet=None, **kwargs):

        super().__init__(*args, **kwargs)

        self.projet = projet

        if projet:

            self.fields["projet"].initial = projet.pk
            self.fields["projet"].disabled = True

            self.fields["chauffeur"].queryset = (
                Personnel.objects
                .filter(
                    equipe_projet__projet=projet,
                    equipe_projet__fonction="CHAUFFEUR",
                    equipe_projet__actif=True,
                )
                .distinct()
                .order_by("nom", "prenom")
            )

        else:

            self.fields["chauffeur"].queryset = (
                Personnel.objects
                .all()
                .order_by("nom", "prenom")
            )

        self.fields["vehicule"].queryset = (
            Vehicule.objects
            .filter(actif=True)
            .order_by("immatriculation")
        )

    def clean(self):

        cleaned_data = super().clean()

        projet = cleaned_data.get("projet")
        chauffeur = cleaned_data.get("chauffeur")
        date_transport = cleaned_data.get("date_transport")

        kilometrage_initial = cleaned_data.get(
            "kilometrage_initial"
        )

        kilometrage_final = cleaned_data.get(
            "kilometrage_final"
        )

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
                "Le kilométrage final doit être supérieur "
                "ou égal au kilométrage initial.",
            )

        if projet and date_transport:

            if (
                projet.date_debut
                and date_transport < projet.date_debut
            ):
                self.add_error(
                    "date_transport",
                    "La date du transport ne peut pas être "
                    "avant le début du projet.",
                )

            if (
                projet.date_fin
                and date_transport > projet.date_fin
            ):
                self.add_error(
                    "date_transport",
                    "La date du transport ne peut pas dépasser "
                    "la fin du projet.",
                )

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

        return cleaned_data

# ============================================================
# PERSONNEL EXECUTION PROJET
# ============================================================

class PersonnelExecutionProjetForm(forms.ModelForm):

    class Meta:
        model = PersonnelExecutionProjet

        fields = [
            "projet",
            "personnel",
            "nom",
            "type_class",
            "type_contrat",
            "salaire",
            "date_debut",
            "date_fin",
            "photo",
            "enregistre_par",
        ]

        widgets = {
            "projet": SELECT_WIDGET,
            "personnel": SELECT_WIDGET,
            "nom": TEXT_WIDGET,
            "type_class": SELECT_WIDGET,
            "type_contrat": SELECT_WIDGET,
            "salaire": NUMBER_WIDGET,
            "date_debut": DATETIME_WIDGET,
            "date_fin": DATETIME_WIDGET,
            "photo": FILE_WIDGET,
            "enregistre_par": SELECT_WIDGET,
        }

        labels = {
            "projet": "Projet",
            "personnel": "Personnel existant",
            "nom": "Nom",
            "type_class": "Classe",
            "type_contrat": "Type de contrat",
            "salaire": "Salaire / montant",
            "date_debut": "Date de début",
            "date_fin": "Date de fin",
            "photo": "Photo",
            "enregistre_par": "Enregistré par",
        }

    def __init__(self, *args, projet=None, **kwargs):

        super().__init__(*args, **kwargs)

        self.projet = projet

        # ----------------------------------------------------
        # PERSONNEL EXISTANT
        # ----------------------------------------------------

        self.fields["personnel"].queryset = (
            Personnel.objects
            .filter(
                typeTravail="Construction"
            )
            .order_by(
                "nom",
                "prenom",
            )
        )

        # ----------------------------------------------------
        # PROJET
        # ----------------------------------------------------

        if projet:

            self.fields["projet"].initial = projet.pk
            self.fields["projet"].disabled = True

        # ----------------------------------------------------
        # DATES PAR DÉFAUT
        # ----------------------------------------------------

        if (
            projet
            and not self.is_bound
            and not self.instance.pk
        ):

            if projet.date_debut:

                self.fields["date_debut"].initial = (
                    f"{projet.date_debut}T08:00"
                )

            if projet.date_fin:

                self.fields["date_fin"].initial = (
                    f"{projet.date_fin}T17:00"
                )

    def clean(self):

        cleaned_data = super().clean()

        type_class = cleaned_data.get(
            "type_class"
        )

        personnel = cleaned_data.get(
            "personnel"
        )

        nom = cleaned_data.get(
            "nom"
        )

        type_contrat = cleaned_data.get(
            "type_contrat"
        )

        salaire = cleaned_data.get(
            "salaire"
        )

        date_debut = cleaned_data.get(
            "date_debut"
        )

        date_fin = cleaned_data.get(
            "date_fin"
        )

        projet = (
            cleaned_data.get("projet")
            or self.projet
        )

        # ----------------------------------------------------
        # TYPES UTILISANT PERSONNEL
        # ----------------------------------------------------

        types_personnel = {
            "INGENIEUR",
            "CHEF_CHANTIER",
            "CHAUFFEUR",
            "CHEF_MAGASIN",
            "MAGASIN",
        }

        # ----------------------------------------------------
        # TYPES À SAISIE MANUELLE
        # ----------------------------------------------------

        types_manuels = {
            "CHEF_EQUIPE",
            "CHAUFFEUR_ENGIN",
            "MINIER",
            "AUTRE",
        }

        # ----------------------------------------------------
        # PERSONNEL EXISTANT
        # ----------------------------------------------------

        if type_class in types_personnel:

            if not personnel:

                self.add_error(
                    "personnel",
                    "Veuillez sélectionner un personnel.",
                )

            else:

                if personnel.typeTravail != "Construction":

                    self.add_error(
                        "personnel",
                        "Le personnel sélectionné doit "
                        "appartenir à Construction.",
                    )

                else:

                    cleaned_data["nom"] = str(
                        personnel
                    )

        # ----------------------------------------------------
        # SAISIE MANUELLE
        # ----------------------------------------------------

        elif type_class in types_manuels:

            if not nom or not nom.strip():

                self.add_error(
                    "nom",
                    "Veuillez saisir le nom du travailleur.",
                )

        # ----------------------------------------------------
        # CONTRAT AUTOMATIQUE
        # ----------------------------------------------------

        if type_class == "CHEF_EQUIPE":

            cleaned_data["type_contrat"] = (
                "FORFAITAIRE"
            )

        elif type_class == "MINIER":

            cleaned_data["type_contrat"] = (
                "PRE_PAYER"
            )

        else:

            cleaned_data["type_contrat"] = (
                "MENSUEL"
            )

        # ----------------------------------------------------
        # SALAIRE
        # ----------------------------------------------------

        if (
            salaire is not None
            and salaire < 0
        ):

            self.add_error(
                "salaire",
                "Le salaire / montant ne peut pas "
                "être négatif.",
            )

        # ----------------------------------------------------
        # DATES
        # ----------------------------------------------------

        if (
            date_debut
            and date_fin
            and date_fin < date_debut
        ):

            self.add_error(
                "date_fin",
                "La date de fin doit être "
                "postérieure ou égale "
                "à la date de début.",
            )

        # ----------------------------------------------------
        # LIMITES DU PROJET
        # ----------------------------------------------------

        if projet:

            if (
                date_debut
                and projet.date_debut
                and date_debut.date()
                < projet.date_debut
            ):

                self.add_error(
                    "date_debut",
                    "La date de début ne peut pas "
                    "être avant le début du projet.",
                )

            if (
                date_fin
                and projet.date_fin
                and date_fin.date()
                > projet.date_fin
            ):

                self.add_error(
                    "date_fin",
                    "La date de fin ne peut pas "
                    "dépasser la fin du projet.",
                )

        return cleaned_data
# ============================================================
# FORMULAIRE CHEF D'ÉQUIPE
# ============================================================

class ChefEquipeProjetForm(forms.ModelForm):

    class Meta:
        model = PersonnelExecutionProjet

        fields = [
            "nom",
            "type_contrat",
            "salaire",
            "date_debut",
            "date_fin",
            "photo",
        ]

        widgets = {
            "nom": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nom complet du chef d'équipe",
                }
            ),

            "type_contrat": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "salaire": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Montant du contrat",
                }
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

            "photo": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                }
            ),
        }

        labels = {
            "nom": "Nom du chef d'équipe",
            "type_contrat": "Type de contrat",
            "salaire": "Montant / rémunération",
            "date_debut": "Date de début",
            "date_fin": "Date de fin",
            "photo": "Photo",
        }

    def __init__(self, *args, projet=None, **kwargs):

        self.projet = projet

        super().__init__(*args, **kwargs)

        # --------------------------------------------------------
        # Le Chef d'équipe est obligatoirement forfaitaire
        # --------------------------------------------------------
        self.fields["type_contrat"].choices = [
            ("FORFAITAIRE", "Forfaitaire"),
        ]

        self.fields["type_contrat"].initial = "FORFAITAIRE"

    def clean_nom(self):

        nom = self.cleaned_data.get("nom")

        if not nom or not nom.strip():
            raise forms.ValidationError(
                "Le nom du chef d'équipe est obligatoire."
            )

        return nom.strip()

def clean(self):
    cleaned_data = super().clean()

    projet = self.projet

    nom = cleaned_data.get("nom")
    type_contrat = cleaned_data.get("type_contrat")
    salaire = cleaned_data.get("salaire")
    date_debut = cleaned_data.get("date_debut")
    date_fin = cleaned_data.get("date_fin")

    # ============================================================
    # NORMALISATION DES DATES
    # ============================================================
    # Django peut retourner un datetime ou un date selon le champ,
    # le widget ou les données reçues.
    # On convertit tout en date avant toute comparaison.
    # ============================================================

    def normaliser_date(valeur):
        if valeur is None:
            return None

        if isinstance(valeur, datetime.datetime):
            return valeur.date()

        if isinstance(valeur, datetime.date):
            return valeur

        return valeur

    date_debut = normaliser_date(date_debut)
    date_fin = normaliser_date(date_fin)

    # Mettre les valeurs normalisées dans cleaned_data
    cleaned_data["date_debut"] = date_debut
    cleaned_data["date_fin"] = date_fin

    # ============================================================
    # PROJET OBLIGATOIRE
    # ============================================================

    if not projet:
        raise forms.ValidationError(
            "Le projet est obligatoire."
        )

    # ============================================================
    # NOM
    # ============================================================

    if not nom or not str(nom).strip():
        self.add_error(
            "nom",
            "Le nom du chef d'équipe est obligatoire."
        )

    # ============================================================
    # TYPE DE CONTRAT
    # ============================================================

    if not type_contrat:
        self.add_error(
            "type_contrat",
            "Le type de contrat est obligatoire."
        )

    # Un chef d'équipe externe est payé au forfait
    if type_contrat and type_contrat != "FORFAITAIRE":
        self.add_error(
            "type_contrat",
            "Un chef d'équipe externe doit avoir un contrat forfaitaire."
        )

    # ============================================================
    # RÉMUNÉRATION
    # ============================================================

    if salaire is None:
        self.add_error(
            "salaire",
            "La rémunération est obligatoire."
        )
    else:
        try:
            if salaire < 0:
                self.add_error(
                    "salaire",
                    "La rémunération ne peut pas être négative."
                )
        except (TypeError, ValueError):
            self.add_error(
                "salaire",
                "La rémunération saisie est invalide."
            )

    # ============================================================
    # DATES
    # ============================================================

    if not date_debut:
        self.add_error(
            "date_debut",
            "La date de début est obligatoire."
        )

    if not date_fin:
        self.add_error(
            "date_fin",
            "La date de fin est obligatoire."
        )

    # ============================================================
    # COMPARAISON DES DATES
    # ============================================================

    if date_debut and date_fin:

        if date_fin < date_debut:
            self.add_error(
                "date_fin",
                "La date de fin doit être supérieure ou égale "
                "à la date de début."
            )

    # ============================================================
    # RESPECT DE LA PÉRIODE DU PROJET
    # ============================================================

    projet_date_debut = normaliser_date(
        projet.date_debut
    )

    projet_date_fin = normaliser_date(
        projet.date_fin
    )

    if date_debut and projet_date_debut:

        if date_debut < projet_date_debut:
            self.add_error(
                "date_debut",
                "La date de début du chef d'équipe ne peut pas "
                "être antérieure à la date de début du projet."
            )

    if date_fin and projet_date_fin:

        if date_fin > projet_date_fin:
            self.add_error(
                "date_fin",
                "La date de fin du chef d'équipe ne peut pas "
                "dépasser la date de fin du projet."
            )

    # ============================================================
    # RETOUR
    # ============================================================

    return cleaned_data

    
# ============================================================
# EQUIPAGE PROJET
# ============================================================

class EquipageProjetForm(forms.ModelForm):

    class Meta:
        model = EquipageProjet

        fields = [
            "personnel_execution",
            "lieu",
            "montant",
            "date_debut",
            "date_fin",
            "enregistre_par",
        ]

        widgets = {
            "personnel_execution": SELECT_WIDGET,
            "lieu": SELECT_WIDGET,
            "montant": NUMBER_WIDGET,
            "date_debut": DATETIME_WIDGET,
            "date_fin": DATETIME_WIDGET,
            "enregistre_par": SELECT_WIDGET,
        }

        labels = {
            "personnel_execution": "Personnel d'exécution",
            "lieu": "Point de chantier",
            "montant": "Montant",
            "date_debut": "Date de début",
            "date_fin": "Date de fin",
            "enregistre_par": "Enregistré par",
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

            self.fields[
                "personnel_execution"
            ].queryset = (
                PersonnelExecutionProjet.objects
                .filter(
                    projet=projet
                )
                .order_by(
                    "nom"
                )
            )

            self.fields[
                "lieu"
            ].queryset = (
                PointProjet.objects
                .filter(
                    projet=projet
                )
                .order_by(
                    "nom"
                )
            )

        else:

            self.fields[
                "personnel_execution"
            ].queryset = (
                PersonnelExecutionProjet.objects.none()
            )

            self.fields[
                "lieu"
            ].queryset = (
                PointProjet.objects.none()
            )

    def clean(self):

        cleaned_data = super().clean()

        personnel_execution = cleaned_data.get(
            "personnel_execution"
        )

        lieu = cleaned_data.get(
            "lieu"
        )

        montant = cleaned_data.get(
            "montant"
        )

        date_debut = cleaned_data.get(
            "date_debut"
        )

        date_fin = cleaned_data.get(
            "date_fin"
        )

        if (
            montant is not None
            and montant < 0
        ):

            self.add_error(
                "montant",
                "Le montant ne peut pas être négatif.",
            )

        if (
            date_debut
            and date_fin
            and date_fin < date_debut
        ):

            self.add_error(
                "date_fin",
                "La date de fin doit être "
                "postérieure ou égale "
                "à la date de début.",
            )

        if personnel_execution and lieu:

            if (
                personnel_execution.projet_id
                != lieu.projet_id
            ):

                self.add_error(
                    "lieu",
                    "Le point et le personnel doivent "
                    "appartenir au même projet.",
                )

        if self.projet:

            if (
                personnel_execution
                and personnel_execution.projet_id
                != self.projet.pk
            ):

                self.add_error(
                    "personnel_execution",
                    "Ce personnel d'exécution "
                    "n'appartient pas à ce projet.",
                )

            if (
                lieu
                and lieu.projet_id
                != self.projet.pk
            ):

                self.add_error(
                    "lieu",
                    "Ce point n'appartient pas à ce projet.",
                )

        return cleaned_data



# ============================================================
# AVANCE EQUIPE PROJET
# ============================================================

class AvanceEquipeProjetForm(forms.ModelForm):

    class Meta:
        model = AvanceEquipeProjet

        fields = [
            "personnel_execution",
            "montant",
            "date_avance",
            "enregistre_par",
        ]

        widgets = {
            "personnel_execution": SELECT_WIDGET,
            "montant": NUMBER_WIDGET,
            "date_avance": DATETIME_WIDGET,
            "enregistre_par": SELECT_WIDGET,
        }

        labels = {
            "personnel_execution": "Travailleur",
            "montant": "Montant de l'avance",
            "date_avance": "Date de l'avance",
            "enregistre_par": "Enregistré par",
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

            self.fields[
                "personnel_execution"
            ].queryset = (
                PersonnelExecutionProjet.objects
                .filter(
                    projet=projet
                )
                .order_by(
                    "nom"
                )
            )

        else:

            self.fields[
                "personnel_execution"
            ].queryset = (
                PersonnelExecutionProjet.objects.none()
            )

    def clean(self):

        cleaned_data = super().clean()

        personnel_execution = cleaned_data.get(
            "personnel_execution"
        )

        montant = cleaned_data.get(
            "montant"
        )

        date_avance = cleaned_data.get(
            "date_avance"
        )

        if (
            montant is not None
            and montant <= 0
        ):

            self.add_error(
                "montant",
                "Le montant de l'avance doit "
                "être supérieur à zéro.",
            )

        if self.projet and personnel_execution:

            if (
                personnel_execution.projet_id
                != self.projet.pk
            ):

                self.add_error(
                    "personnel_execution",
                    "Ce travailleur n'appartient "
                    "pas à ce projet.",
                )

        if self.projet and date_avance:

            if (
                self.projet.date_debut
                and date_avance.date()
                < self.projet.date_debut
            ):

                self.add_error(
                    "date_avance",
                    "La date de l'avance ne peut pas "
                    "être avant le début du projet.",
                )

            if (
                self.projet.date_fin
                and date_avance.date()
                > self.projet.date_fin
            ):

                self.add_error(
                    "date_avance",
                    "La date de l'avance ne peut pas "
                    "dépasser la fin du projet.",
                )

        return cleaned_data
# ============================================================
# EQUIPE MATERIAU PROJET
# ============================================================

class EquipeMateriauProjetForm(forms.ModelForm):

    class Meta:
        model = EquipeMateriauProjet

        fields = [
            "personnel_execution",
            "point",
            "typemateriaux",
            "quantite",
            "unite",
            "prix_unitaire",
            "date_debut",
            "enregistre_par",
        ]

        widgets = {
            "personnel_execution": SELECT_WIDGET,
            "point": SELECT_WIDGET,
            "typemateriaux": SELECT_WIDGET,
            "quantite": NUMBER_WIDGET,
            "unite": TEXT_WIDGET,
            "prix_unitaire": NUMBER_WIDGET,
            "date_debut": DATETIME_WIDGET,
            "enregistre_par": SELECT_WIDGET,
        }

        labels = {
            "personnel_execution": "Travailleur",
            "point": "Point de chantier",
            "typemateriaux": "Type de matériau",
            "quantite": "Quantité",
            "unite": "Unité",
            "prix_unitaire": "Prix unitaire",
            "date_debut": "Date",
            "enregistre_par": "Enregistré par",
        }

    def __init__(
        self,
        *args,
        projet=None,
        **kwargs
    ):

        super().__init__(*args, **kwargs)

        self.projet = projet

        self.fields[
            "typemateriaux"
        ].queryset = (
            Materiaux.objects
            .all()
            .order_by(
                "libelle"
            )
        )

        if projet:

            self.fields[
                "personnel_execution"
            ].queryset = (
                PersonnelExecutionProjet.objects
                .filter(
                    projet=projet
                )
                .order_by(
                    "nom"
                )
            )

            self.fields[
                "point"
            ].queryset = (
                PointProjet.objects
                .filter(
                    projet=projet
                )
                .order_by(
                    "nom"
                )
            )

        else:

            self.fields[
                "personnel_execution"
            ].queryset = (
                PersonnelExecutionProjet.objects.none()
            )

            self.fields[
                "point"
            ].queryset = (
                PointProjet.objects.none()
            )

    def clean(self):

        cleaned_data = super().clean()

        personnel_execution = cleaned_data.get(
            "personnel_execution"
        )

        point = cleaned_data.get(
            "point"
        )

        quantite = cleaned_data.get(
            "quantite"
        )

        prix_unitaire = cleaned_data.get(
            "prix_unitaire"
        )

        date_debut = cleaned_data.get(
            "date_debut"
        )

        if (
            quantite is not None
            and quantite <= 0
        ):

            self.add_error(
                "quantite",
                "La quantité doit être "
                "supérieure à zéro.",
            )

        if (
            prix_unitaire is not None
            and prix_unitaire < 0
        ):

            self.add_error(
                "prix_unitaire",
                "Le prix unitaire ne peut "
                "pas être négatif.",
            )

        if personnel_execution and point:

            if (
                personnel_execution.projet_id
                != point.projet_id
            ):

                self.add_error(
                    "point",
                    "Le point et le personnel doivent "
                    "appartenir au même projet.",
                )

        if self.projet:

            if (
                personnel_execution
                and personnel_execution.projet_id
                != self.projet.pk
            ):

                self.add_error(
                    "personnel_execution",
                    "Ce travailleur n'appartient "
                    "pas à ce projet.",
                )

            if (
                point
                and point.projet_id
                != self.projet.pk
            ):

                self.add_error(
                    "point",
                    "Ce point n'appartient "
                    "pas à ce projet.",
                )

            if (
                date_debut
                and self.projet.date_debut
                and date_debut.date()
                < self.projet.date_debut
            ):

                self.add_error(
                    "date_debut",
                    "La date ne peut pas être "
                    "avant le début du projet.",
                )

            if (
                date_debut
                and self.projet.date_fin
                and date_debut.date()
                > self.projet.date_fin
            ):

                self.add_error(
                    "date_debut",
                    "La date ne peut pas dépasser "
                    "la fin du projet.",
                )

        return cleaned_data