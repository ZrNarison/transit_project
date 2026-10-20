from django import forms
from django.db import models
from django.utils import timezone
from decimal import Decimal
from django.db import transaction
from personnel.models import Personnel
from django.core.exceptions import ValidationError
from .models import (Projet,EquipeProjet,PointProjet,EnginProjet,RapportProjet,
    RapportTravail,MouvementMateriauProjet,
    RapportMateriau,
    VehiculeProjet,
    RapportVehicule,
    ActiviteTransportProjet,
    PersonnelExecutionProjet,
    MouvementPersonnelProjet,
    MouvementVehiculeProjet,
    EquipageProjet,MateriauProjet,
    AvanceEquipeProjet,
    EquipeMateriauProjet,
    VehiculeLourdsProjet
)
from .models import (
    MateriauProjet,
    AchatMateriauProjet,
    ReceptionMateriauProjet,
    DistributionMateriauProjet,
    ConsommationMateriauProjet,
    RetourMateriauProjet,
    PersonnelExecutionProjet,
    PointProjet,
)
from django.urls import path, reverse, reverse_lazy

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
# VÉHICULE ROUTIER AFFECTÉ AU PROJET
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
        ]

        widgets = {
            "vehicule": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Exemple : Camion 01",
                }
            ),

            "chauffeur": forms.Select(
                attrs={
                    "class": "form-select",
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
                    "placeholder": "Exemple : 3.50",
                }
            ),

            "actif": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

        labels = {
            "vehicule": "Véhicule",
            "chauffeur": "Conducteur / Chauffeur",
            "date_debut": "Début de l'affectation",
            "date_fin": "Fin de l'affectation",
            "kilometrage_initial": "Kilométrage initial",
            "kilometrage_final": "Kilométrage final",
            "consommation_km_litre": "Consommation (km/L)",
            "actif": "Affectation active",
        }

    def __init__(self, *args, projet=None, **kwargs):

        super().__init__(*args, **kwargs)

        self.projet = projet

        # ----------------------------------------------------
        # CHAUFFEURS
        # ----------------------------------------------------

        self.fields["chauffeur"].queryset = (
            Personnel.objects
            .filter(typeTravail="Construction")
            .order_by("nom", "prenom")
        )

        self.fields["chauffeur"].required = False

        # ----------------------------------------------------
        # DATES DU PROJET
        # ----------------------------------------------------

        if projet:

            if projet.date_debut:
                self.fields["date_debut"].widget.attrs["min"] = (
                    projet.date_debut.isoformat()
                )

            if projet.date_fin:
                self.fields["date_debut"].widget.attrs["max"] = (
                    projet.date_fin.isoformat()
                )

                self.fields["date_fin"].widget.attrs["min"] = (
                    projet.date_debut.isoformat()
                )

                self.fields["date_fin"].widget.attrs["max"] = (
                    projet.date_fin.isoformat()
                )

        # ----------------------------------------------------
        # VALEURS PAR DÉFAUT
        # ----------------------------------------------------

        if not self.instance.pk:

            if projet:

                if projet.date_debut:
                    self.fields["date_debut"].initial = (
                        projet.date_debut
                    )

                if projet.date_fin:
                    self.fields["date_fin"].initial = (
                        projet.date_fin
                    )

            self.fields["actif"].initial = True

    def clean_vehicule(self):

        vehicule = self.cleaned_data.get("vehicule")

        if vehicule:
            vehicule = vehicule.strip()

        if not vehicule:
            raise forms.ValidationError(
                "Veuillez saisir le véhicule."
            )

        # Vérification du doublon dans le même projet
        if self.projet:

            queryset = VehiculeProjet.objects.filter(
                projet=self.projet,
                vehicule__iexact=vehicule,
            )

            if self.instance.pk:
                queryset = queryset.exclude(
                    pk=self.instance.pk
                )

            if queryset.exists():
                raise forms.ValidationError(
                    "Ce véhicule est déjà affecté à ce projet."
                )

        return vehicule

    def clean(self):

        cleaned_data = super().clean()

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
        # DATES
        # ----------------------------------------------------

        if date_debut and date_fin:

            if date_fin < date_debut:

                self.add_error(
                    "date_fin",
                    "La fin de l'affectation doit être "
                    "postérieure ou égale au début.",
                )

        # ----------------------------------------------------
        # LIMITES DU PROJET
        # ----------------------------------------------------

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
        # KILOMÉTRAGE
        # ----------------------------------------------------

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
            and kilometrage_final < kilometrage_initial
        ):

            self.add_error(
                "kilometrage_final",
                "Le kilométrage final doit être "
                "supérieur ou égal au kilométrage initial.",
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

        return cleaned_data


# ============================================================
# ENGIN DE CHANTIER AFFECTÉ AU PROJET
# ============================================================
class EnginProjetForm(forms.ModelForm):

    class Meta:
        model = EnginProjet

        fields = [
            "engin",
            "conducteur",
            "date_debut",
            "date_fin",
            "heures_initiales",
            "heures_finales",
            "consommation_heure_litre",
            "actif",
        ]

        widgets = {
            "engin": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Exemple : Pelle hydraulique",
                }
            ),

            "conducteur": forms.Select(
                attrs={
                    "class": "form-select",
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

            "heures_initiales": forms.NumberInput(
                    attrs={
                        "class": "form-control",
                        "step": "0.01",
                        "min": "0",
                        "placeholder": "Compteur initial",
                    }
                ),

                "heures_finales": forms.NumberInput(
                    attrs={
                        "class": "form-control",
                        "step": "0.01",
                        "min": "0",
                        "placeholder": "Compteur final",
                    }
                ),

            "consommation_heure_litre": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Exemple : 12.50",
                }
            ),

            "actif": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }

        labels = {
            "engin": "Engin",
            "conducteur": "Conducteur",
            "date_debut": "Début de l'affectation",
            "date_fin": "Fin de l'affectation",
            "heures_initiales": "Heures initiales",
            "heures_finales": "Heures finales",
            "consommation_heure_litre": "Consommation (L/h)",
            "actif": "Affectation active",
        }

    def __init__(self, *args, projet=None, **kwargs):

        super().__init__(*args, **kwargs)

        self.projet = projet

        # ----------------------------------------------------
        # CONDUCTEURS
        # ----------------------------------------------------

        self.fields["conducteur"].queryset = (
            Personnel.objects
            .filter(typeTravail="Construction")
            .order_by("nom", "prenom")
        )

        self.fields["conducteur"].required = False

        # ----------------------------------------------------
        # DATES DU PROJET
        # ----------------------------------------------------

        if projet:

            if projet.date_debut:
                self.fields["date_debut"].widget.attrs["min"] = (
                    projet.date_debut.isoformat()
                )

            if projet.date_fin:
                self.fields["date_debut"].widget.attrs["max"] = (
                    projet.date_fin.isoformat()
                )

                self.fields["date_fin"].widget.attrs["min"] = (
                    projet.date_debut.isoformat()
                )

                self.fields["date_fin"].widget.attrs["max"] = (
                    projet.date_fin.isoformat()
                )

        # ----------------------------------------------------
        # VALEURS PAR DÉFAUT
        # ----------------------------------------------------

        if not self.instance.pk:

            if projet:

                if projet.date_debut:
                    self.fields["date_debut"].initial = (
                        projet.date_debut
                    )

                if projet.date_fin:
                    self.fields["date_fin"].initial = (
                        projet.date_fin
                    )

            self.fields["actif"].initial = True

    def clean_engin(self):

        engin = self.cleaned_data.get("engin")

        if engin:
            engin = engin.strip()

        if not engin:
            raise forms.ValidationError(
                "Veuillez saisir l'engin."
            )

        # Vérification du doublon dans le même projet
        if self.projet:

            queryset = EnginProjet.objects.filter(
                projet=self.projet,
                engin__iexact=engin,
            )

            if self.instance.pk:
                queryset = queryset.exclude(
                    pk=self.instance.pk
                )

            if queryset.exists():
                raise forms.ValidationError(
                    "Cet engin est déjà affecté à ce projet."
                )

        return engin

    def clean(self):

        cleaned_data = super().clean()

        date_debut = cleaned_data.get("date_debut")
        date_fin = cleaned_data.get("date_fin")

        heures_initiales = cleaned_data.get(
            "heures_initiales"
        )

        heures_finales = cleaned_data.get(
            "heures_finales"
        )

        consommation = cleaned_data.get(
            "consommation_heure_litre"
        )

        # ----------------------------------------------------
        # DATES
        # ----------------------------------------------------

        if date_debut and date_fin:

            if date_fin < date_debut:

                self.add_error(
                    "date_fin",
                    "La fin de l'affectation doit être "
                    "postérieure ou égale au début.",
                )

        # ----------------------------------------------------
        # LIMITES DU PROJET
        # ----------------------------------------------------

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
        # COMPTEUR D'HEURES
        # ----------------------------------------------------

        if (
            heures_initiales is not None
            and heures_initiales < 0
        ):
            self.add_error(
                "heures_initiales",
                "Les heures initiales ne peuvent pas être négatives.",
            )

        if (
            heures_finales is not None
            and heures_finales < 0
        ):
            self.add_error(
                "heures_finales",
                "Les heures finales ne peuvent pas être négatives.",
            )

        if (
            heures_initiales is not None
            and heures_finales is not None
            and heures_initiales < heures_finales
        ):
            self.add_error(
                "heures_finales",
                "Le compteur initial doit être supérieur "
                "ou égal au compteur final.",
            )

        # ----------------------------------------------------
        # CONSOMMATION
        # ----------------------------------------------------

        if (
            consommation is not None
            and consommation < 0
        ):

            self.add_error(
                "consommation_heure_litre",
                "La consommation L/h "
                "ne peut pas être négative.",
            )

        return cleaned_data


class MouvementVehiculeProjetForm(forms.ModelForm):

    class Meta:
        model = MouvementVehiculeProjet

        fields = [
            "vehicule_projet",
            "engin_projet",
            "date_mouvement",
            "heure_depart",
            "heure_arrivee",
            "point_depart",
            "point_arrivee",
            "kilometrage_initial",
            "kilometrage_final",
            "heures_initiales",
            "heures_finales",
            "carburant_litre",
            "observation",
        ]

        widgets = {
            "vehicule_projet": SELECT_WIDGET,
            "engin_projet": SELECT_WIDGET,
            "date_mouvement": DATETIME_WIDGET,
            "heure_depart": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "heure_arrivee": forms.TimeInput(
                attrs={"class": "form-control", "type": "time"}
            ),
            "point_depart": SELECT_WIDGET,
            "point_arrivee": SELECT_WIDGET,
            "kilometrage_initial": NUMBER_WIDGET,
            "kilometrage_final": NUMBER_WIDGET,
            "heures_initiales": NUMBER_WIDGET,
            "heures_finales": NUMBER_WIDGET,
            "carburant_litre": NUMBER_WIDGET,
            "observation": TEXTAREA_WIDGET,
        }

        labels = {
            "vehicule_projet": "Véhicule routier",
            "engin_projet": "Engin de chantier",
            "date_mouvement": "Date du mouvement",
            "heure_depart": "Heure de départ",
            "heure_arrivee": "Heure d'arrivée",
            "point_depart": "Point de départ",
            "point_arrivee": "Point d'arrivée",
            "kilometrage_initial": "Kilométrage initial (km)",
            "kilometrage_final": "Kilométrage final (km)",
            "heures_initiales": "Compteur horaire initial",
            "heures_finales": "Compteur horaire final",
            "carburant_litre": "Carburant consommé (litres)",
            "observation": "Observation",
        }

    def __init__(self, *args, projet=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.projet = projet

        self.fields["vehicule_projet"].queryset = (
            VehiculeProjet.objects.filter(projet=projet)
            .order_by("vehicule")
            if projet else VehiculeProjet.objects.none()
        )

        self.fields["engin_projet"].queryset = (
            EnginProjet.objects.filter(projet=projet)
            .order_by("engin")
            if projet else EnginProjet.objects.none()
        )

        self.fields["point_depart"].queryset = (
            PointProjet.objects.filter(projet=projet).order_by("nom")
            if projet else PointProjet.objects.none()
        )

        self.fields["point_arrivee"].queryset = (
            PointProjet.objects.filter(projet=projet).order_by("nom")
            if projet else PointProjet.objects.none()
        )

    def clean(self):
        cleaned_data = super().clean()

        vehicule = cleaned_data.get("vehicule_projet")
        engin = cleaned_data.get("engin_projet")
        point_depart = cleaned_data.get("point_depart")
        point_arrivee = cleaned_data.get("point_arrivee")

        # Exactement un matériel doit être choisi.
        if vehicule and engin:
            self.add_error(
                "engin_projet",
                "Choisissez soit un véhicule routier, soit un engin."
            )
        elif not vehicule and not engin:
            self.add_error(
                "vehicule_projet",
                "Sélectionnez un véhicule routier ou un engin."
            )

        materiel = engin or vehicule

        if materiel and self.projet:
            if materiel.projet_id != self.projet.pk:
                self.add_error(
                    "engin_projet" if engin else "vehicule_projet",
                    "Le matériel sélectionné n'appartient pas à ce projet."
                )

        for champ, point in (
            ("point_depart", point_depart),
            ("point_arrivee", point_arrivee),
        ):
            if (
                point
                and self.projet
                and point.projet_id != self.projet.pk
            ):
                self.add_error(
                    champ,
                    "Ce point n'appartient pas au projet sélectionné."
                )

        if engin:
            initial = cleaned_data.get("heures_initiales")
            final = cleaned_data.get("heures_finales")

            if initial is not None and initial < 0:
                self.add_error(
                    "heures_initiales",
                    "Le compteur initial ne peut pas être négatif."
                )

            if final is not None and final < 0:
                self.add_error(
                    "heures_finales",
                    "Le compteur final ne peut pas être négatif."
                )

            if initial is not None and final is not None and final > initial:
                self.add_error(
                    "heures_finales",
                    "Le compteur final doit être inférieur ou égal "
                    "au compteur initial."
                )

        elif vehicule:
            initial = cleaned_data.get("kilometrage_initial")
            final = cleaned_data.get("kilometrage_final")

            if initial is not None and initial < 0:
                self.add_error(
                    "kilometrage_initial",
                    "Le kilométrage initial ne peut pas être négatif."
                )

            if final is not None and final < 0:
                self.add_error(
                    "kilometrage_final",
                    "Le kilométrage final ne peut pas être négatif."
                )

            if initial is not None and final is not None and final < initial:
                self.add_error(
                    "kilometrage_final",
                    "Le kilométrage final doit être supérieur ou égal "
                    "au kilométrage initial."
                )

        carburant = cleaned_data.get("carburant_litre")
        if carburant is not None and carburant < 0:
            self.add_error(
                "carburant_litre",
                "Le carburant ne peut pas être négatif."
            )

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
# FORMULAIRE POINT PROJET
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

    # ========================================================
    # INITIALISATION
    # ========================================================

    def __init__(
        self,
        *args,
        projet=None,
        **kwargs
    ):

        super().__init__(
            *args,
            **kwargs
        )

        self.projet = projet

    # ========================================================
    # VALIDATION DISTANCE
    # ========================================================

    def clean_distance_km(self):

        value = self.cleaned_data.get(
            "distance_km"
        )

        if value is not None and value < 0:

            raise forms.ValidationError(
                "La distance ne peut pas être négative."
            )

        return value

    # ========================================================
    # ENREGISTREMENT
    # ========================================================

    def save(self, commit=True):

        instance = super().save(
            commit=False
        )

        # ----------------------------------------------------
        # Le projet vient de l'URL
        # ----------------------------------------------------

        if self.projet is not None:

            instance.projet = self.projet

        if commit:

            instance.save()

        return instance

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
# PERSONNEL D'EXÉCUTION DU PROJET
# ============================================================

class PersonnelExecutionProjetForm(forms.ModelForm):

    class Meta:

        model = PersonnelExecutionProjet

        fields = [
            "projet",
            "personnel",
            "nom",
            "type_class",
            "montant",
            "date_debut",
            "date_fin",
            "photo",
            "point_projet",
            "materiau_projet",
            "quantite",
            "prix_unitaire",
            "date_production",
            "observation",
            "enregistre_par",
        ]

        widgets = {

            "projet": SELECT_WIDGET,

            "personnel": SELECT_WIDGET,

            "nom": TEXT_WIDGET,

            "type_class": SELECT_WIDGET,

            "montant": NUMBER_WIDGET,

            "date_debut": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
            ),

            "date_fin": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
            ),

            "photo": FILE_WIDGET,

            "point_projet": SELECT_WIDGET,

            "materiau_projet": SELECT_WIDGET,

            "quantite": NUMBER_WIDGET,

            "prix_unitaire": NUMBER_WIDGET,

            "date_production": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
            ),

            "observation": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Observation éventuelle...",
                }
            ),

            "enregistre_par": SELECT_WIDGET,
        }

        labels = {

            "projet": "Projet",

            "personnel": "Personnel interne",

            "nom": "Nom",

            "type_class": "Type",

            "montant": "Montant",

            "date_debut": "Date de début",

            "date_fin": "Date de fin",

            "photo": "Photo",

            "point_projet": "Point du projet",

            "materiau_projet": "Matériau du projet",

            "quantite": "Quantité",

            "prix_unitaire": "Prix unitaire",

            "date_production": "Date de production",

            "observation": "Observation",

            "enregistre_par": "Enregistré par",
        }
        

    # ========================================================
    # INITIALISATION
    # ========================================================

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # ----------------------------------------------------
        # Projet
        # ----------------------------------------------------

        projet_id = None

        if self.data.get("projet"):

            try:
                projet_id = int(
                    self.data.get("projet")
                )
            except (TypeError, ValueError):

                projet_id = None

        elif self.instance and self.instance.projet_id:

            projet_id = self.instance.projet_id

        # ----------------------------------------------------
        # Filtrer les points du projet
        # ----------------------------------------------------

        if projet_id:

            self.fields[
                "point_projet"
            ].queryset = PointProjet.objects.filter(
                projet_id=projet_id,
                actif=True,
            )

        else:

            self.fields[
                "point_projet"
            ].queryset = PointProjet.objects.none()

        # ----------------------------------------------------
        # Filtrer les matériaux du projet
        # ----------------------------------------------------

        if projet_id:

            self.fields[
                "materiau_projet"
            ].queryset = MateriauProjet.objects.filter(
                projet_id=projet_id,
                actif=True,
            ).select_related(
                "materiau"
            )

        else:

            self.fields[
                "materiau_projet"
            ].queryset = MateriauProjet.objects.none()

        # ----------------------------------------------------
        # Champs facultatifs au niveau formulaire
        #
        # La validation dépend ensuite du type.
        # ----------------------------------------------------

        self.fields[
            "personnel"
        ].required = False

        self.fields[
            "point_projet"
        ].required = False

        self.fields[
            "materiau_projet"
        ].required = False

        self.fields[
            "date_debut"
        ].required = False

        self.fields[
            "date_fin"
        ].required = False

        self.fields[
            "date_production"
        ].required = False

        self.fields[
            "montant"
        ].required = False

        # ----------------------------------------------------
        # Si modification d'un minier
        # ----------------------------------------------------

        if (
            self.instance
            and self.instance.pk
            and self.instance.type_class == "MINIER"
        ):

            self.fields[
                "montant"
            ].disabled = True

    # ========================================================
    # VALIDATION
    # ========================================================

    def clean(self):

        cleaned_data = super().clean()

        # ====================================================
        # DONNÉES
        # ====================================================

        projet = cleaned_data.get(
            "projet"
        )

        type_class = cleaned_data.get(
            "type_class"
        )

        personnel = cleaned_data.get(
            "personnel"
        )

        nom = cleaned_data.get(
            "nom"
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

        point_projet = cleaned_data.get(
            "point_projet"
        )

        materiau_projet = cleaned_data.get(
            "materiau_projet"
        )

        quantite = cleaned_data.get(
            "quantite"
        )

        prix_unitaire = cleaned_data.get(
            "prix_unitaire"
        )

        date_production = cleaned_data.get(
            "date_production"
        )

        # ====================================================
        # TYPE
        # ====================================================

        if not type_class:

            self.add_error(
                "type_class",
                "Le type de personnel est obligatoire.",
            )

            return cleaned_data

        TYPES_EXTERNES = {
            "CHEF_EQUIPE",
            "CHAUFFEUR_ENGIN",
            "MINIER",
            "AUTRE",
        }

        # ====================================================
        # PERSONNEL EXTERNE
        # ====================================================

        if type_class in TYPES_EXTERNES:

            if personnel:

                self.add_error(
                    "personnel",
                    "Ce type de personnel est externe. "
                    "Aucun personnel interne ne doit être sélectionné.",
                )

            cleaned_data["personnel"] = None

            if not nom or not nom.strip():

                self.add_error(
                    "nom",
                    "Le nom est obligatoire pour ce personnel externe.",
                )

        # ====================================================
        # DATE DÉBUT / DATE FIN
        # ====================================================

        if date_debut and date_fin:

            if date_fin < date_debut:

                self.add_error(
                    "date_fin",
                    "La date de fin doit être "
                    "postérieure ou égale à la date de début.",
                )

        # ====================================================
        # COHÉRENCE AVEC LE PROJET
        # ====================================================

        if projet:

            if (
                date_debut
                and projet.date_debut
                and date_debut < projet.date_debut
            ):

                self.add_error(
                    "date_debut",
                    "La date de début ne peut pas être "
                    "antérieure au début du projet.",
                )

            if (
                date_fin
                and projet.date_fin
                and date_fin > projet.date_fin
            ):

                self.add_error(
                    "date_fin",
                    "La date de fin ne peut pas dépasser "
                    "la fin du projet.",
                )

        # ====================================================
        # MONTANT
        # ====================================================

        if montant is not None:

            if montant < Decimal("0.00"):

                self.add_error(
                    "montant",
                    "Le montant ne peut pas être négatif.",
                )

        # ====================================================
        # CHEF D'ÉQUIPE
        # ====================================================

        if type_class == "CHEF_EQUIPE":

            # ------------------------------------------------
            # Point obligatoire
            # ------------------------------------------------

            if not point_projet:

                self.add_error(
                    "point_projet",
                    "Le point du projet est obligatoire "
                    "pour un chef d'équipe.",
                )

            # ------------------------------------------------
            # Matériau interdit
            # ------------------------------------------------

            cleaned_data["materiau_projet"] = None

            # ------------------------------------------------
            # Montant obligatoire
            # ------------------------------------------------

            if (
                montant is None
                or montant <= Decimal("0.00")
            ):

                self.add_error(
                    "montant",
                    "Le montant doit être supérieur à zéro "
                    "pour un chef d'équipe.",
                )

            # ------------------------------------------------
            # Production minière interdite
            # ------------------------------------------------

            cleaned_data["quantite"] = Decimal("0.00")

            cleaned_data["prix_unitaire"] = Decimal("0.00")

            cleaned_data["date_production"] = None

            # ------------------------------------------------
            # Dates obligatoires
            # ------------------------------------------------

            if not date_debut:

                self.add_error(
                    "date_debut",
                    "La date de début est obligatoire "
                    "pour un chef d'équipe.",
                )

            if not date_fin:

                self.add_error(
                    "date_fin",
                    "La date de fin est obligatoire "
                    "pour un chef d'équipe.",
                )

        # ====================================================
        # MINIER
        # ====================================================

        elif type_class == "MINIER":

            # ------------------------------------------------
            # Aucun point
            # ------------------------------------------------

            cleaned_data["point_projet"] = None

            # ------------------------------------------------
            # Matériau obligatoire
            # ------------------------------------------------

            if not materiau_projet:

                self.add_error(
                    "materiau_projet",
                    "Le matériau est obligatoire "
                    "pour un minier.",
                )

            # ------------------------------------------------
            # Cohérence matériau / projet
            # ------------------------------------------------

            if materiau_projet and projet:

                if (
                    materiau_projet.projet_id
                    != projet.pk
                ):

                    self.add_error(
                        "materiau_projet",
                        "Le matériau sélectionné "
                        "n'appartient pas à ce projet.",
                    )

                elif not materiau_projet.actif:

                    self.add_error(
                        "materiau_projet",
                        "Le matériau sélectionné "
                        "n'est plus actif pour ce projet.",
                    )

            # ------------------------------------------------
            # Quantité obligatoire
            # ------------------------------------------------

            if quantite is None:

                self.add_error(
                    "quantite",
                    "La quantité est obligatoire "
                    "pour un minier.",
                )

            elif quantite <= Decimal("0.00"):

                self.add_error(
                    "quantite",
                    "La quantité doit être "
                    "supérieure à zéro.",
                )

            # ------------------------------------------------
            # Prix unitaire obligatoire
            # ------------------------------------------------

            if prix_unitaire is None:

                self.add_error(
                    "prix_unitaire",
                    "Le prix unitaire est obligatoire "
                    "pour un minier.",
                )

            elif prix_unitaire <= Decimal("0.00"):

                self.add_error(
                    "prix_unitaire",
                    "Le prix unitaire doit être "
                    "supérieur à zéro.",
                )

            # ------------------------------------------------
            # Date de production
            # ------------------------------------------------

            if not date_production:

                self.add_error(
                    "date_production",
                    "La date de production est obligatoire "
                    "pour un minier.",
                )

            # ------------------------------------------------
            # Date dans la période du projet
            # ------------------------------------------------

            if projet and date_production:

                if (
                    projet.date_debut
                    and date_production < projet.date_debut
                ):

                    self.add_error(
                        "date_production",
                        "La date de production ne peut pas "
                        "être antérieure au début du projet.",
                    )

                if (
                    projet.date_fin
                    and date_production > projet.date_fin
                ):

                    self.add_error(
                        "date_production",
                        "La date de production ne peut pas "
                        "dépasser la fin du projet.",
                    )

            # ------------------------------------------------
            # Pas de montant saisi manuellement
            # ------------------------------------------------

            cleaned_data["montant"] = Decimal("0.00")

            # ------------------------------------------------
            # Dates d'affectation inutilisées
            # ------------------------------------------------

            cleaned_data["date_debut"] = None

            cleaned_data["date_fin"] = None

        # ====================================================
        # CHAUFFEUR D'ENGIN
        # ====================================================

        elif type_class == "CHAUFFEUR_ENGIN":

            # ------------------------------------------------
            # Aucun point
            # ------------------------------------------------

            cleaned_data["point_projet"] = None

            # ------------------------------------------------
            # Aucun matériau
            # ------------------------------------------------

            cleaned_data["materiau_projet"] = None

            # ------------------------------------------------
            # Aucune production minière
            # ------------------------------------------------

            cleaned_data["quantite"] = Decimal("0.00")

            cleaned_data["prix_unitaire"] = Decimal("0.00")

            cleaned_data["date_production"] = None

        # ====================================================
        # AUTRE
        # ====================================================

        elif type_class == "AUTRE":

            # ------------------------------------------------
            # Aucun point
            # ------------------------------------------------

            cleaned_data["point_projet"] = None

            # ------------------------------------------------
            # Aucun matériau
            # ------------------------------------------------

            cleaned_data["materiau_projet"] = None

            # ------------------------------------------------
            # Aucune production
            # ------------------------------------------------

            cleaned_data["quantite"] = Decimal("0.00")

            cleaned_data["prix_unitaire"] = Decimal("0.00")

            cleaned_data["date_production"] = None

        # ====================================================
        # COHÉRENCE POINT / PROJET
        # ====================================================

        point_projet = cleaned_data.get(
            "point_projet"
        )

        if point_projet and projet:

            if point_projet.projet_id != projet.pk:

                self.add_error(
                    "point_projet",
                    "Le point sélectionné "
                    "n'appartient pas à ce projet.",
                )

            elif not point_projet.actif:

                self.add_error(
                    "point_projet",
                    "Le point sélectionné "
                    "n'est plus actif pour ce projet.",
                )

        # ====================================================
        # VALEURS DE L'INSTANCE
        # ====================================================

        self.instance.type_class = type_class

        if type_class in TYPES_EXTERNES:

            self.instance.personnel = None

        # ----------------------------------------------------
        # Minier : montant calculé automatiquement
        # ----------------------------------------------------

        if type_class == "MINIER":

            self.instance.montant = Decimal("0.00")

            self.instance.point_projet = None

            self.instance.date_debut = None

            self.instance.date_fin = None

        # ----------------------------------------------------
        # Chef d'équipe
        # ----------------------------------------------------

        elif type_class == "CHEF_EQUIPE":

            self.instance.materiau_projet = None

            self.instance.quantite = Decimal("0.00")

            self.instance.prix_unitaire = Decimal("0.00")

            self.instance.date_production = None

        # ----------------------------------------------------
        # Chauffeur / Autre
        # ----------------------------------------------------

        elif type_class in {
            "CHAUFFEUR_ENGIN",
            "AUTRE",
        }:

            self.instance.point_projet = None

            self.instance.materiau_projet = None

            self.instance.quantite = Decimal("0.00")

            self.instance.prix_unitaire = Decimal("0.00")

            self.instance.date_production = None

        
        # ====================================================
        # RETOUR
        # ====================================================

        return cleaned_data


# ============================================================
# FORMULAIRE CHEF D'ÉQUIPE DU PROJET
# ============================================================

class ChefEquipeProjetForm(forms.ModelForm):

    class Meta:

        model = PersonnelExecutionProjet

        fields = [
            "projet",
            "nom",
            "type_class",
            "montant",
            "date_debut",
            "date_fin",
            "photo",
            "point_projet",
            "enregistre_par",
        ]

        widgets = {

            "projet": SELECT_WIDGET,

            "nom": TEXT_WIDGET,

            "type_class": SELECT_WIDGET,

            "montant": NUMBER_WIDGET,

            "date_debut": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
            ),

            "date_fin": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
            ),

            "photo": FILE_WIDGET,

            "point_projet": SELECT_WIDGET,

            "enregistre_par": SELECT_WIDGET,
        }

        labels = {

            "projet": "Projet",

            "nom": "Nom du chef d'équipe",

            "type_class": "Type",

            "montant": "Montant",

            "date_debut": "Date de début",

            "date_fin": "Date de fin",

            "photo": "Photo",

            "point_projet": "Point du projet",

            "enregistre_par": "Enregistré par",
        }

    # ========================================================
    # INITIALISATION
    # ========================================================

    def __init__(self, *args, projet=None, **kwargs):

        # ----------------------------------------------------
        # IMPORTANT :
        # récupérer "projet" AVANT super()
        # pour qu'il ne soit pas envoyé à BaseModelForm
        # ----------------------------------------------------

        super().__init__(*args, **kwargs)

        self.projet = projet

        # ----------------------------------------------------
        # Projet fourni par la vue
        # ----------------------------------------------------

        if self.projet is not None:

            self.fields["projet"].queryset = Projet.objects.filter(
                pk=self.projet.pk
            )

            self.fields["projet"].initial = self.projet.pk

            # Le projet est imposé par l'URL.
            self.fields["projet"].disabled = True

        else:

            self.fields["projet"].queryset = Projet.objects.all()

        # ----------------------------------------------------
        # Le type est toujours CHEF_EQUIPE
        # ----------------------------------------------------

        self.fields["type_class"].initial = "CHEF_EQUIPE"

        self.fields["type_class"].disabled = True

        # ----------------------------------------------------
        # Filtrer les points du projet
        # ----------------------------------------------------

        if self.projet is not None:

            self.fields[
                "point_projet"
            ].queryset = (
                PointProjet.objects
                .filter(
                    projet=self.projet,
                    actif=True,
                )
                .order_by("nom")
            )

        else:

            # ------------------------------------------------
            # Si aucun projet n'est fourni
            # on essaie de récupérer celui de l'instance
            # ------------------------------------------------

            projet_id = None

            if (
                self.instance
                and self.instance.pk
                and self.instance.projet_id
            ):

                projet_id = self.instance.projet_id

            if projet_id:

                self.fields[
                    "point_projet"
                ].queryset = (
                    PointProjet.objects
                    .filter(
                        projet_id=projet_id,
                        actif=True,
                    )
                    .order_by("nom")
                )

            else:

                self.fields[
                    "point_projet"
                ].queryset = PointProjet.objects.none()

        # ----------------------------------------------------
        # Champs obligatoires
        # ----------------------------------------------------

        self.fields["nom"].required = True

        self.fields["montant"].required = True

        self.fields["date_debut"].required = True

        self.fields["date_fin"].required = True

        self.fields["point_projet"].required = True

    # ========================================================
    # VALIDATION
    # ========================================================

    def clean(self):

        cleaned_data = super().clean()

        # ====================================================
        # PROJET
        # ====================================================

        projet = cleaned_data.get("projet")

        # Le projet passé par la vue est prioritaire.
        if self.projet is not None:

            projet = self.projet

            cleaned_data["projet"] = projet

        # ====================================================
        # DONNÉES
        # ====================================================

        nom = cleaned_data.get("nom")

        montant = cleaned_data.get("montant")

        date_debut = cleaned_data.get("date_debut")

        date_fin = cleaned_data.get("date_fin")

        point_projet = cleaned_data.get("point_projet")

        # ====================================================
        # PROJET OBLIGATOIRE
        # ====================================================

        if not projet:

            self.add_error(
                "projet",
                "Le projet est obligatoire.",
            )

        # ====================================================
        # TYPE
        # ====================================================

        cleaned_data["type_class"] = "CHEF_EQUIPE"

        # ====================================================
        # NOM
        # ====================================================

        if not nom or not nom.strip():

            self.add_error(
                "nom",
                "Le nom du chef d'équipe est obligatoire.",
            )

        # ====================================================
        # MONTANT
        # ====================================================

        if montant is None:

            self.add_error(
                "montant",
                "Le montant est obligatoire.",
            )

        elif montant <= Decimal("0.00"):

            self.add_error(
                "montant",
                "Le montant doit être supérieur à zéro.",
            )

        # ====================================================
        # DATE DE DÉBUT
        # ====================================================

        if not date_debut:

            self.add_error(
                "date_debut",
                "La date de début est obligatoire.",
            )

        # ====================================================
        # DATE DE FIN
        # ====================================================

        if not date_fin:

            self.add_error(
                "date_fin",
                "La date de fin est obligatoire.",
            )

        # ====================================================
        # COHÉRENCE DES DATES
        # ====================================================

        if date_debut and date_fin:

            if date_fin < date_debut:

                self.add_error(
                    "date_fin",
                    "La date de fin doit être "
                    "postérieure ou égale à la date de début.",
                )

        # ====================================================
        # COHÉRENCE AVEC LE PROJET
        # ====================================================

        if projet:

            if (
                date_debut
                and projet.date_debut
                and date_debut < projet.date_debut
            ):

                self.add_error(
                    "date_debut",
                    "La date de début du chef d'équipe "
                    "ne peut pas être antérieure "
                    "au début du projet.",
                )

            if (
                date_fin
                and projet.date_fin
                and date_fin > projet.date_fin
            ):

                self.add_error(
                    "date_fin",
                    "La date de fin du chef d'équipe "
                    "ne peut pas dépasser "
                    "la fin du projet.",
                )

        # ====================================================
        # POINT DU PROJET
        # ====================================================

        if not point_projet:

            self.add_error(
                "point_projet",
                "Le point du projet est obligatoire "
                "pour un chef d'équipe.",
            )

        elif projet:

            if point_projet.projet_id != projet.pk:

                self.add_error(
                    "point_projet",
                    "Le point sélectionné "
                    "n'appartient pas à ce projet.",
                )

            elif not point_projet.actif:

                self.add_error(
                    "point_projet",
                    "Le point sélectionné "
                    "n'est plus actif pour ce projet.",
                )

        # ====================================================
        # CHEF D'ÉQUIPE EXTERNE
        # ====================================================

        cleaned_data["personnel"] = None

        # ====================================================
        # CHAMPS NON UTILISÉS PAR CHEF_EQUIPE
        # ====================================================

        cleaned_data["materiau_projet"] = None

        cleaned_data["quantite"] = Decimal("0.00")

        cleaned_data["prix_unitaire"] = Decimal("0.00")

        cleaned_data["date_production"] = None

        # ====================================================
        # PRÉPARER L'INSTANCE
        # ====================================================

        self.instance.type_class = "CHEF_EQUIPE"

        self.instance.personnel = None

        self.instance.materiau_projet = None

        self.instance.quantite = Decimal("0.00")

        self.instance.prix_unitaire = Decimal("0.00")

        self.instance.date_production = None

        if projet:

            self.instance.projet = projet

        # ====================================================
        # RETOUR
        # ====================================================

        return cleaned_data

    # ========================================================
    # SAUVEGARDE
    # ========================================================

    def save(self, commit=True):

        instance = super().save(commit=False)

        # ----------------------------------------------------
        # Projet imposé par la vue
        # ----------------------------------------------------

        if self.projet is not None:

            instance.projet = self.projet

        # ----------------------------------------------------
        # Type
        # ----------------------------------------------------

        instance.type_class = "CHEF_EQUIPE"

        # ----------------------------------------------------
        # Chef d'équipe = personnel externe
        # ----------------------------------------------------

        instance.personnel = None

        # ----------------------------------------------------
        # Champs non utilisés
        # ----------------------------------------------------

        instance.materiau_projet = None

        instance.quantite = Decimal("0.00")

        instance.prix_unitaire = Decimal("0.00")

        instance.date_production = None

        if commit:

            instance.save()

        return instance

class FormulaireMateriauProjet(forms.ModelForm):
    """Planification des matériaux nécessaires au projet."""

    class Meta:
        model = MateriauProjet
        fields = [
            "materiau",
            "unite",
            "quantite_prevue",
        ]
        widgets = {
            "materiau": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ex. : Ciment, sable, gravier...",
            }),
            "unite": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Ex. : sac, m³, kg, pièce...",
            }),
            "quantite_prevue": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0.001",
                "step": "0.001",
            }),
        }

    def clean_quantite_prevue(self):
        quantite = self.cleaned_data["quantite_prevue"]
        if quantite <= Decimal("0"):
            raise ValidationError("La quantité prévue doit être supérieure à zéro.")
        return quantite


# ============================================================
# FORMULAIRE — ACHAT DE MATÉRIAUX DU PROJET
# ============================================================
class AchatMateriauProjetForm(forms.ModelForm):
    """Enregistrement d'un achat de matériaux pour un projet."""

    class Meta:
        model = AchatMateriauProjet

        fields = [
            "materiau_projet",
            "fournisseur",
            "date_achat",
            "quantite_achetee",
            "prix_unitaire",
            "observation",
        ]

        widgets = {
            "materiau_projet": forms.Select(attrs={
                "class": "form-select",
            }),
            "fournisseur": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Nom du fournisseur",
            }),
            "date_achat": forms.DateInput(attrs={
                "class": "form-control",
                "type": "date",
            }),
            "quantite_achetee": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0.01",
                "step": "0.01",
            }),
            "prix_unitaire": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0",
                "step": "0.01",
            }),
            "observation": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Observations éventuelles...",
            }),
        }

        labels = {
            "materiau_projet": "Matériau acheté",
            "fournisseur": "Fournisseur",
            "date_achat": "Date d'achat",
            "quantite_achetee": "Quantité achetée",
            "prix_unitaire": "Prix unitaire",
            "observation": "Observation",
        }

    def __init__(self, *args, projet=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.projet = projet

        # Limiter les matériaux à ceux du projet courant.
        if projet is not None:
            self.fields["materiau_projet"].queryset = (
                MateriauProjet.objects.filter(
                    projet=projet
                ).order_by("materiau")
            )
        else:
            self.fields["materiau_projet"].queryset = (
                MateriauProjet.objects.none()
            )

    def clean_quantite_achetee(self):
        quantite = self.cleaned_data.get("quantite_achetee")

        if quantite is None or quantite <= Decimal("0"):
            raise ValidationError(
                "La quantité achetée doit être strictement supérieure à zéro."
            )

        return quantite

    def clean_prix_unitaire(self):
        prix = self.cleaned_data.get("prix_unitaire")

        if prix is None or prix < Decimal("0"):
            raise ValidationError(
                "Le prix unitaire ne peut pas être négatif."
            )

        return prix

    def clean(self):
        cleaned_data = super().clean()

        materiau = cleaned_data.get("materiau_projet")
        date_achat = cleaned_data.get("date_achat")

        if self.projet is None:
            raise ValidationError(
                "Le projet doit être fourni pour enregistrer un achat."
            )

        if materiau and materiau.projet_id != self.projet.pk:
            self.add_error(
                "materiau_projet",
                "Ce matériau n'appartient pas au projet sélectionné.",
            )

        if materiau and date_achat:
            projet_materiau = materiau.projet

            if (
                projet_materiau.date_debut
                and date_achat < projet_materiau.date_debut
            ):
                self.add_error(
                    "date_achat",
                    "La date d'achat ne peut pas précéder le début du projet.",
                )

            if (
                projet_materiau.date_fin
                and date_achat > projet_materiau.date_fin
            ):
                self.add_error(
                    "date_achat",
                    "La date d'achat ne peut pas dépasser la fin du projet.",
                )

        return cleaned_data

class ReceptionMateriauProjetForm(forms.ModelForm):
    """Enregistrement d'une réception de matériaux pour le projet."""

    class Meta:
        model = ReceptionMateriauProjet
        fields = [
            "materiau_projet",
            "date_reception",
            "quantite_recue",
            "point",
            "piece_justificative",
            "observation",
        ]

        widgets = {
            "materiau_projet": forms.Select(
                attrs={"class": "form-select"}
            ),
            "date_reception": forms.DateInput(
                attrs={"class": "form-control", "type": "date"}
            ),
            "quantite_recue": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
            "point": forms.Select(
                attrs={"class": "form-select", "id": "id_point"}
            ),
            "piece_justificative": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": ".pdf,.jpg,.jpeg,.png,.webp",
                }
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
            "materiau_projet": "Matériau",
            "date_reception": "Date de réception",
            "quantite_recue": "Quantité reçue",
            "point": "Point de réception / livraison",
            "piece_justificative": "Photo ou pièce justificative",
            "observation": "Observation",
        }

        help_texts = {
            "piece_justificative": (
                "Formats acceptés : PDF, JPG, JPEG, PNG et WEBP."
            ),
        }

    def __init__(self, *args, projet=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.projet = projet

        self.fields["point"].required = False
        self.fields["piece_justificative"].required = False

        self.fields["materiau_projet"].queryset = (
            MateriauProjet.objects.none()
        )
        self.fields["point"].queryset = PointProjet.objects.none()

        if projet is not None:
            self.fields["materiau_projet"].queryset = (
                MateriauProjet.objects.filter(
                    projet=projet
                ).order_by("materiau")
            )

            self.fields["point"].queryset = (
                PointProjet.objects.filter(
                    projet=projet
                ).order_by("nom")
            )

    def clean_quantite_recue(self):
        quantite = self.cleaned_data.get("quantite_recue")

        if quantite is None or quantite <= Decimal("0"):
            raise forms.ValidationError(
                "La quantité reçue doit être strictement supérieure à zéro."
            )

        return quantite

    def clean_piece_justificative(self):
        fichier = self.cleaned_data.get("piece_justificative")

        if fichier and fichier.size > 10 * 1024 * 1024:
            raise forms.ValidationError(
                "La pièce justificative ne doit pas dépasser 10 Mo."
            )

        return fichier

    def clean(self):
        cleaned_data = super().clean()

        materiau = cleaned_data.get("materiau_projet")
        date_reception = cleaned_data.get("date_reception")
        point = cleaned_data.get("point")

        if self.projet is None:
            raise forms.ValidationError(
                "Le projet doit être fourni pour enregistrer une réception."
            )

        if materiau and materiau.projet_id != self.projet.pk:
            self.add_error(
                "materiau_projet",
                "Ce matériau n'appartient pas au projet sélectionné.",
            )

        if point and point.projet_id != self.projet.pk:
            self.add_error(
                "point",
                "Le point sélectionné n'appartient pas à ce projet.",
            )

        if date_reception:
            date_debut = getattr(self.projet, "date_debut", None)
            date_fin = getattr(self.projet, "date_fin", None)

            if date_debut and date_reception < date_debut:
                self.add_error(
                    "date_reception",
                    "La réception ne peut pas précéder le début du projet.",
                )

            if date_fin and date_reception > date_fin:
                self.add_error(
                    "date_reception",
                    "La réception ne peut pas dépasser la fin du projet.",
                )

        return cleaned_data


class DistributionMateriauProjetForm(forms.ModelForm):
    """Distribution de matériaux vers un point du chantier."""

    class Meta:
        model = DistributionMateriauProjet
        fields = [
            "materiau_projet",
            "vehicule",
            "point",
            "date_distribution",
            "quantite",
            "observation",
        ]

        widgets = {
            "materiau_projet": forms.Select(
                attrs={"class": "form-select"}
            ),
            "vehicule": forms.Select(
                attrs={"class": "form-select"}
            ),
            "point": forms.Select(
                attrs={"class": "form-select"}
            ),
            "date_distribution": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "quantite": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
            "observation": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
        }

    def __init__(self, *args, projet=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.projet = projet

        self.fields["materiau_projet"].queryset = (
            MateriauProjet.objects.none()
        )
        self.fields["vehicule"].queryset = (
            VehiculeProjet.objects.none()
        )
        self.fields["point"].queryset = (
            PointProjet.objects.none()
        )

        self.fields["vehicule"].required = False
        self.fields["vehicule"].empty_label = "Aucun véhicule"

        if projet is not None:
            self.fields["materiau_projet"].queryset = (
                MateriauProjet.objects.filter(
                    projet=projet
                ).order_by("materiau", "id")
            )

            self.fields["vehicule"].queryset = (
                VehiculeProjet.objects.filter(
                    projet=projet,
                    actif=True,
                ).order_by("vehicule", "id")
            )

            self.fields["point"].queryset = (
                PointProjet.objects.filter(
                    projet=projet
                ).order_by("nom", "id")
            )

    def clean_quantite(self):
        quantite = self.cleaned_data.get("quantite")

        if quantite is None or quantite <= Decimal("0"):
            raise forms.ValidationError(
                "La quantité distribuée doit être supérieure à zéro."
            )

        return quantite

    def clean(self):
        cleaned_data = super().clean()

        materiau = cleaned_data.get("materiau_projet")
        vehicule = cleaned_data.get("vehicule")
        point = cleaned_data.get("point")

        if self.projet is None:
            raise forms.ValidationError(
                "Le projet doit être fourni pour enregistrer une distribution."
            )

        if materiau and materiau.projet_id != self.projet.pk:
            self.add_error(
                "materiau_projet",
                "Ce matériau n'appartient pas au projet sélectionné.",
            )

        if point and point.projet_id != self.projet.pk:
            self.add_error(
                "point",
                "Le point sélectionné n'appartient pas à ce projet.",
            )

        if vehicule and vehicule.projet_id != self.projet.pk:
            self.add_error(
                "vehicule",
                "Ce véhicule ou engin n'appartient pas au projet sélectionné.",
            )

        return cleaned_data



class ConsommationMateriauProjetForm(forms.ModelForm):
    """Enregistrement de la consommation des matériaux du projet."""

    class Meta:
        model = ConsommationMateriauProjet

        fields = [
            "distribution",
            "reception_directe",
            "date_consommation",
            "quantite_utilisee",
            "observation",
        ]

        widgets = {
            "distribution": forms.Select(
                attrs={"class": "form-select"}
            ),
            "reception_directe": forms.Select(
                attrs={"class": "form-select"}
            ),
            "date_consommation": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
                format="%Y-%m-%d",
            ),
            "quantite_utilisee": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
            "observation": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
        }

    def __init__(self, *args, projet=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.projet = projet

        self.fields["distribution"].required = False
        self.fields["reception_directe"].required = False

        self.fields["distribution"].queryset = (
            DistributionMateriauProjet.objects.none()
        )

        self.fields["reception_directe"].queryset = (
            ReceptionMateriauProjet.objects.none()
        )

        self.fields["date_consommation"].input_formats = [
            "%Y-%m-%d"
        ]

        self.fields["quantite_utilisee"].min_value = Decimal("0.01")

        if projet is not None:
            self.fields["distribution"].queryset = (
                DistributionMateriauProjet.objects.filter(
                    materiau_projet__projet=projet,
                )
                .select_related(
                    "materiau_projet",
                    "vehicule",
                    "point",
                    "enregistre_par",
                )
                .order_by("-date_distribution", "-id")
            )

            self.fields["reception_directe"].queryset = (
                ReceptionMateriauProjet.objects.filter(
                    materiau_projet__projet=projet,
                    point__isnull=False,
                )
                .select_related(
                    "materiau_projet",
                    "point",
                )
                .order_by("-date_reception", "-id")
            )

    def clean_quantite_utilisee(self):
        quantite = self.cleaned_data.get("quantite_utilisee")

        if quantite is None or quantite <= Decimal("0"):
            raise forms.ValidationError(
                "La quantité consommée doit être supérieure à zéro."
            )

        return quantite

    def clean(self):
        cleaned_data = super().clean()

        distribution = cleaned_data.get("distribution")
        reception = cleaned_data.get("reception_directe")

        if self.projet is None:
            raise forms.ValidationError(
                "Le projet doit être fourni pour enregistrer une consommation."
            )

        # Ne pas ajouter une seconde erreur si un champ est déjà invalide.
        if (
            "distribution" in self.errors
            or "reception_directe" in self.errors
        ):
            return cleaned_data

        # Une seule source doit être sélectionnée.
        if distribution is None and reception is None:
            self.add_error(
                None,
                "Sélectionnez une distribution ou une réception directe.",
            )
            return cleaned_data

        if distribution is not None and reception is not None:
            self.add_error(
                None,
                "Choisissez une seule source : distribution ou réception directe.",
            )
            return cleaned_data

        # Vérifier que la distribution appartient au projet.
        if distribution is not None:
            if distribution.materiau_projet.projet_id != self.projet.pk:
                self.add_error(
                    "distribution",
                    "Cette distribution n'appartient pas au projet sélectionné.",
                )

            if distribution.point_id is None:
                self.add_error(
                    "distribution",
                    "Cette distribution n'a pas de point de stockage associé.",
                )

        # Vérifier que la réception appartient au projet.
        if reception is not None:
            if reception.materiau_projet.projet_id != self.projet.pk:
                self.add_error(
                    "reception_directe",
                    "Cette réception n'appartient pas au projet sélectionné.",
                )

            if reception.point_id is None:
                self.add_error(
                    "reception_directe",
                    "Cette réception ne possède pas de point de stockage.",
                )

        return cleaned_data

class RetourMateriauProjetForm(forms.ModelForm):

    materiau = forms.ChoiceField(
        label="Matériau",
        choices=[],
        required=True,
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    point = forms.ModelChoiceField(
        label="Point",
        queryset=PointProjet.objects.none(),
        required=True,
        empty_label="Sélectionner un point",
        widget=forms.Select(
            attrs={"class": "form-select"}
        ),
    )

    class Meta:
        model = RetourMateriauProjet
        fields = [
            "materiau",
            "point",
            "date_retour",
            "quantite",
            "observation",
        ]

        widgets = {
            "date_retour": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
                format="%Y-%m-%d",
            ),
            "quantite": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                }
            ),
            "observation": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                }
            ),
        }

    def __init__(self, *args, projet=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.projet = projet

        self.fields["date_retour"].input_formats = ["%Y-%m-%d"]
        self.fields["quantite"].min_value = Decimal("0.01")

        if projet is None:
            return

        distributions = DistributionMateriauProjet.objects.filter(
            materiau_projet__projet=projet,
        )

        materiaux = (
            distributions
            .values_list("materiau_projet__materiau", flat=True)
            .distinct()
            .order_by("materiau_projet__materiau")
        )

        self.fields["materiau"].choices = [
            (nom, nom)
            for nom in materiaux
            if nom
        ]

        points_ids = distributions.values_list(
            "point_id",
            flat=True,
        ).distinct()

        self.fields["point"].queryset = (
            PointProjet.objects.filter(pk__in=points_ids)
            .order_by("nom")
        )

    def _distributions_concernees(self, verrouiller=False):
        """
        Récupère les distributions du matériau et du point choisis,
        par ordre chronologique FIFO.
        """

        materiau = self.cleaned_data.get("materiau")
        point = self.cleaned_data.get("point")

        if not materiau or not point or self.projet is None:
            return DistributionMateriauProjet.objects.none()

        queryset = DistributionMateriauProjet.objects.filter(
            materiau_projet__projet=self.projet,
            materiau_projet__materiau=materiau,
            point=point,
        ).order_by("date_distribution", "id")

        if verrouiller:
            queryset = queryset.select_for_update()

        return queryset

    @staticmethod
    def _quantite_deja_retournee(distribution):
        """
        Additionne les retours déjà enregistrés sur une distribution.
        Ne nécessite pas l'import de Sum.
        """

        total = Decimal("0.00")

        retours = distribution.retours.only("quantite").iterator()

        for retour in retours:
            total += retour.quantite

        return total

    def _calculer_disponible(self, distributions=None):
        """
        Calcule la quantité distribuée restant disponible pour retour,
        après déduction des retours précédents.
        """

        if distributions is None:
            distributions = self._distributions_concernees()

        disponible = Decimal("0.00")

        for distribution in distributions:
            deja_retournee = self._quantite_deja_retournee(
                distribution
            )

            reste = distribution.quantite - deja_retournee

            if reste > 0:
                disponible += reste

        return disponible

    def clean(self):
        cleaned_data = super().clean()

        materiau = cleaned_data.get("materiau")
        point = cleaned_data.get("point")
        quantite = cleaned_data.get("quantite")

        if self.projet is None:
            raise ValidationError(
                "Le projet doit être fourni pour enregistrer un retour."
            )

        if not materiau or not point or quantite is None:
            return cleaned_data

        distributions = self._distributions_concernees()

        if not distributions.exists():
            self.add_error(
                "point",
                "Aucune distribution n'existe pour ce matériau "
                "à ce point dans ce projet.",
            )
            return cleaned_data

        if quantite <= Decimal("0"):
            self.add_error(
                "quantite",
                "La quantité retournée doit être supérieure à zéro.",
            )
            return cleaned_data

        disponible = self._calculer_disponible(distributions)

        if quantite > disponible:
            self.add_error(
                "quantite",
                (
                    f"Quantité demandée : {quantite}. "
                    f"Quantité disponible pour retour : {disponible}."
                ),
            )

        return cleaned_data

    @transaction.atomic
    def enregistrer_retour(self, enregistre_par):
        """
        Enregistre le retour en répartissant sa quantité entre les
        distributions FIFO. Chaque objet créé conserve sa distribution.
        """

        if not self.is_valid():
            raise ValidationError(
                "Le formulaire contient des erreurs."
            )

        quantite_restante = self.cleaned_data["quantite"]

        distributions = list(
            self._distributions_concernees(verrouiller=True)
        )

        disponible = self._calculer_disponible(distributions)

        if quantite_restante > disponible:
            raise ValidationError(
                {
                    "quantite": (
                        f"Quantité disponible insuffisante : {disponible}."
                    )
                }
            )

        retours_crees = []

        for distribution in distributions:
            if quantite_restante <= Decimal("0"):
                break

            deja_retournee = self._quantite_deja_retournee(
                distribution
            )

            reste_distribution = (
                distribution.quantite - deja_retournee
            )

            if reste_distribution <= Decimal("0"):
                continue

            quantite_affectee = min(
                quantite_restante,
                reste_distribution,
            )

            retour = RetourMateriauProjet(
                distribution=distribution,
                reception_directe=None,
                date_retour=self.cleaned_data["date_retour"],
                quantite=quantite_affectee,
                observation=self.cleaned_data.get("observation", ""),
                enregistre_par=enregistre_par,
            )

            retour.full_clean()
            retour.save()

            retours_crees.append(retour)
            quantite_restante -= quantite_affectee

        if quantite_restante > Decimal("0"):
            raise ValidationError(
                {
                    "quantite": (
                        "La quantité n'a pas pu être répartie intégralement "
                        "entre les distributions."
                    )
                }
            )

        return retours_crees

# ============================================================
# FORMULAIRE MATÉRIAU DU PROJET
# ============================================================
class MateriauProjetForm(forms.ModelForm):

    class Meta:
        model = MateriauProjet

        fields = [
            "projet",
            "materiau",
            "unite",
            "quantite_prevue",
        ]

        widgets = {
            "projet": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "materiau": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Exemple : Ciment, sable, gravier...",
                }
            ),

            "unite": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Exemple : m³, tonne, kg, litre...",
                }
            ),

            "quantite_prevue": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Quantité prévue",
                }
            ),
        }

        labels = {
            "projet": "Projet",
            "materiau": "Matériau",
            "unite": "Unité",
            "quantite_prevue": "Quantité prévue",
        }

    # ========================================================
    # INITIALISATION
    # ========================================================

    def __init__(self, *args, projet=None, **kwargs):

        super().__init__(*args, **kwargs)

        self.projet = projet

        if self.projet is not None:

            self.fields["projet"].queryset = (
                Projet.objects.filter(
                    pk=self.projet.pk
                )
            )

            self.fields["projet"].initial = self.projet.pk
            self.fields["projet"].disabled = True

    # ========================================================
    # VALIDATION QUANTITÉ
    # ========================================================

    def clean_quantite_prevue(self):

        quantite = self.cleaned_data.get(
            "quantite_prevue"
        )

        if (
            quantite is not None
            and quantite < Decimal("0.00")
        ):
            raise forms.ValidationError(
                "La quantité prévue ne peut pas être négative."
            )

        return quantite

    # ========================================================
    # VALIDATION GÉNÉRALE
    # ========================================================

    def clean(self):

        cleaned_data = super().clean()

        projet = cleaned_data.get("projet")
        materiau = cleaned_data.get("materiau")

        if self.projet is not None:

            projet = self.projet
            cleaned_data["projet"] = projet

        if not projet:

            self.add_error(
                "projet",
                "Le projet est obligatoire.",
            )

        if not materiau:

            self.add_error(
                "materiau",
                "Le matériau est obligatoire.",
            )

        return cleaned_data

    # ========================================================
    # ENREGISTREMENT
    # ========================================================

    def save(self, commit=True):

        instance = super().save(commit=False)

        if self.projet is not None:
            instance.projet = self.projet

        if commit:
            instance.save()

        return instance


# ============================================================
# FORMULAIRE MINIER DU PROJET
# ============================================================
class MinierProjetForm(forms.ModelForm):

    class Meta:

        model = PersonnelExecutionProjet

        fields = [
            "nom",
            "materiau_projet",
            "quantite",
            "prix_unitaire",
            "date_production",
            "photo",
            "observation",
        ]

        widgets = {

            "nom": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Nom du minier",
                }
            ),

            "materiau_projet": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),

            "quantite": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0.01",
                    "placeholder": "Quantité produite",
                }
            ),

            "prix_unitaire": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0.01",
                    "placeholder": "Prix unitaire",
                }
            ),

            "date_production": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
            ),

            "photo": forms.ClearableFileInput(
                attrs={
                    "class": "form-control",
                    "accept": "image/*",
                }
            ),

            "observation": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Observation éventuelle...",
                }
            ),
        }

        labels = {

            "nom": "Nom du minier",

            "materiau_projet": "Matériau",

            "quantite": "Quantité",

            "prix_unitaire": "Prix unitaire",

            "date_production": "Date de production",

            "photo": "Photo",

            "observation": "Observation",
        }

    # ========================================================
    # INITIALISATION
    # ========================================================

    def __init__(
        self,
        *args,
        projet=None,
        **kwargs
    ):

        super().__init__(
            *args,
            **kwargs
        )

        self.projet = projet

        # ----------------------------------------------------
        # Aucun matériau par défaut
        # ----------------------------------------------------

        self.fields[
            "materiau_projet"
        ].queryset = (
            MateriauProjet.objects.none()
        )

        # ----------------------------------------------------
        # Matériaux du projet
        # ----------------------------------------------------

        if self.projet is not None:

            self.fields[
                "materiau_projet"
            ].queryset = (

                MateriauProjet.objects

                .filter(
                    projet=self.projet
                )

                .select_related(
                    "projet"
                )

                .order_by(
                    "materiau",
                    "id"
                )
            )

        # ----------------------------------------------------
        # Première option
        # ----------------------------------------------------

        self.fields[
            "materiau_projet"
        ].empty_label = (
            "Sélectionner un matériau"
        )

    # ========================================================
    # VALIDATION
    # ========================================================

    def clean(self):

        cleaned_data = super().clean()

        nom = cleaned_data.get(
            "nom"
        )

        materiau_projet = cleaned_data.get(
            "materiau_projet"
        )

        quantite = cleaned_data.get(
            "quantite"
        )

        prix_unitaire = cleaned_data.get(
            "prix_unitaire"
        )

        date_production = cleaned_data.get(
            "date_production"
        )

        # ====================================================
        # PROJET OBLIGATOIRE
        # ====================================================

        if self.projet is None:

            raise forms.ValidationError(
                "Le projet est obligatoire "
                "pour enregistrer un minier."
            )

        # ====================================================
        # IMPORTANT :
        # PRÉPARER L'INSTANCE AVANT LA VALIDATION DU MODÈLE
        # ====================================================
        #
        # Le formulaire ne contient volontairement PAS :
        #
        #     personnel
        #     type_class
        #     projet
        #     point_projet
        #     montant
        #
        # Ces valeurs sont imposées pour un MINIER.
        #
        # Cela évite notamment que PersonnelExecutionProjet.clean()
        # génère une erreur "personnel" alors que le champ n'existe
        # pas dans ce formulaire.
        # ====================================================

        self.instance.projet = self.projet

        self.instance.type_class = "MINIER"

        self.instance.personnel = None

        self.instance.point_projet = None

        self.instance.montant = Decimal("0.00")

        # ====================================================
        # NOM
        # ====================================================

        if not nom or not nom.strip():

            self.add_error(
                "nom",
                "Le nom du minier est obligatoire."
            )

        # ====================================================
        # MATÉRIAU
        # ====================================================

        if not materiau_projet:

            self.add_error(
                "materiau_projet",
                "Le matériau est obligatoire "
                "pour un minier."
            )

        else:

            # ------------------------------------------------
            # Le matériau doit appartenir au projet
            # ------------------------------------------------

            if (
                materiau_projet.projet_id
                != self.projet.pk
            ):

                self.add_error(
                    "materiau_projet",
                    "Le matériau sélectionné "
                    "n'appartient pas à ce projet."
                )

        # ====================================================
        # QUANTITÉ
        # ====================================================

        if quantite is None:

            self.add_error(
                "quantite",
                "La quantité est obligatoire."
            )

        elif quantite <= Decimal("0.00"):

            self.add_error(
                "quantite",
                "La quantité doit être "
                "supérieure à zéro."
            )

        # ====================================================
        # PRIX UNITAIRE
        # ====================================================

        if prix_unitaire is None:

            self.add_error(
                "prix_unitaire",
                "Le prix unitaire est obligatoire."
            )

        elif prix_unitaire <= Decimal("0.00"):

            self.add_error(
                "prix_unitaire",
                "Le prix unitaire doit être "
                "supérieur à zéro."
            )

        # ====================================================
        # DATE DE PRODUCTION
        # ====================================================

        if not date_production:

            self.add_error(
                "date_production",
                "La date de production est obligatoire."
            )

        # ====================================================
        # DATE / PÉRIODE DU PROJET
        # ====================================================

        if (
            self.projet
            and date_production
        ):

            if (
                self.projet.date_debut
                and date_production
                < self.projet.date_debut
            ):

                self.add_error(
                    "date_production",
                    "La date de production ne peut pas "
                    "être antérieure au début du projet."
                )

            if (
                self.projet.date_fin
                and date_production
                > self.projet.date_fin
            ):

                self.add_error(
                    "date_production",
                    "La date de production ne peut pas "
                    "dépasser la fin du projet."
                )

        return cleaned_data

    # ========================================================
    # ENREGISTREMENT
    # ========================================================

    def save(
        self,
        commit=True
    ):

        instance = super().save(
            commit=False
        )

        # ----------------------------------------------------
        # Projet
        # ----------------------------------------------------

        instance.projet = self.projet

        # ----------------------------------------------------
        # Type
        # ----------------------------------------------------

        instance.type_class = "MINIER"

        # ----------------------------------------------------
        # Le minier est externe
        # ----------------------------------------------------

        instance.personnel = None

        # ----------------------------------------------------
        # Pas de point de chantier
        # ----------------------------------------------------

        instance.point_projet = None

        # ----------------------------------------------------
        # Montant forfaitaire
        # ----------------------------------------------------

        instance.montant = Decimal(
            "0.00"
        )

        # ----------------------------------------------------
        # Sauvegarde
        # ----------------------------------------------------

        if commit:

            instance.save()

        return instance


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
# FORMULAIRE AVANCE EQUIPE PROJET
# ============================================================
class AvanceEquipeProjetForm(forms.ModelForm):
    """
    Formulaire de gestion des avances des chefs d'équipe et miniers.

    Les bénéficiaires sont filtrés par projet.
    Les listes sont reconstruites depuis la base de données
    à chaque création ou modification du formulaire.
    """

    class Meta:
        model = AvanceEquipeProjet

        fields = [
            "equipe_execution",
            "miniers_execution",
            "montant",
            "date_avance",
        ]

        widgets = {
            "equipe_execution": forms.Select(
                attrs={
                    "class": "form-select",
                    "id": "id_equipe_execution",
                }
            ),

            "miniers_execution": forms.Select(
                attrs={
                    "class": "form-select",
                    "id": "id_miniers_execution",
                }
            ),

            "montant": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                    "placeholder": "Montant de l'avance",
                }
            ),

            "date_avance": forms.DateInput(
                format="%Y-%m-%d",
                attrs={
                    "class": "form-control",
                    "type": "date",
                },
            ),
        }

    # ========================================================
    # INITIALISATION
    # ========================================================

    def __init__(self, *args, projet=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.projet = projet

        # Les deux champs sont facultatifs individuellement.
        # La méthode clean() impose ensuite un seul bénéficiaire.
        self.fields["equipe_execution"].required = False
        self.fields["miniers_execution"].required = False

        # ----------------------------------------------------
        # AUCUN PROJET
        # ----------------------------------------------------

        if projet is None:
            self.fields["equipe_execution"].queryset = (
                EquipeProjet.objects.none()
            )

            self.fields["miniers_execution"].queryset = (
                EquipeProjet.objects.none()
            )

        else:
            # ------------------------------------------------
            # CHEFS D'ÉQUIPE DU PROJET
            # ------------------------------------------------

            chefs = EquipeProjet.objects.filter(
                projet_id=projet.pk,
                fonction="CHEF_EQUIPE",
            ).filter(
                models.Q(personnel_execution__isnull=False)
                | models.Q(personnel__isnull=False)
            ).select_related(
                "personnel",
                "personnel_execution",
                "projet",
            ).order_by("id")

            # ------------------------------------------------
            # MINIERS DU PROJET
            # ------------------------------------------------

            miniers = EquipeProjet.objects.filter(
                projet_id=projet.pk,
                fonction="MINIER",
            ).filter(
                models.Q(personnel_execution__isnull=False)
                | models.Q(personnel__isnull=False)
            ).select_related(
                "personnel",
                "personnel_execution",
                "projet",
            ).order_by("id")

            # Les QuerySets sont évalués selon les besoins
            # lors du rendu du formulaire.
            self.fields["equipe_execution"].queryset = chefs
            self.fields["miniers_execution"].queryset = miniers

        # ----------------------------------------------------
        # LIBELLÉS
        # ----------------------------------------------------

        self.fields["equipe_execution"].label = "Chef d'équipe"
        self.fields["miniers_execution"].label = "Minier"

        self.fields["equipe_execution"].empty_label = (
            "— Choisir un chef d'équipe —"
        )

        self.fields["miniers_execution"].empty_label = (
            "— Choisir un minier —"
        )

        self.fields["equipe_execution"].label_from_instance = (
            self._afficher_beneficiaire
        )

        self.fields["miniers_execution"].label_from_instance = (
            self._afficher_beneficiaire
        )

        # ----------------------------------------------------
        # FORMAT DE DATE
        # ----------------------------------------------------

        self.fields["date_avance"].input_formats = [
            "%Y-%m-%d",
        ]

        # Valeur initiale pour une nouvelle avance.
        if not self.instance.pk and not self.is_bound:
            from django.utils import timezone

            self.initial.setdefault(
                "date_avance",
                timezone.localdate(),
            )

    # ========================================================
    # AFFICHAGE DU BÉNÉFICIAIRE
    # ========================================================

    @staticmethod
    def _afficher_beneficiaire(affectation):
        execution = getattr(
            affectation,
            "personnel_execution",
            None,
        )

        if execution and execution.nom:
            nom = execution.nom.strip()

            if execution.type_class == "CHEF_EQUIPE":
                return f"{nom} — Chef d'équipe"

            if execution.type_class == "MINIER":
                return f"{nom} — Minier"

            return nom

        personnel = getattr(affectation, "personnel", None)

        if personnel:
            return str(personnel)

        return f"Affectation #{affectation.pk}"

    # ========================================================
    # VALIDATION DU MONTANT
    # ========================================================

    def clean_montant(self):
        montant = self.cleaned_data.get("montant")

        if montant is None or montant <= 0:
            raise ValidationError(
                "Le montant de l'avance doit être supérieur à zéro."
            )

        return montant

    # ========================================================
    # VALIDATION DE LA DATE
    # ========================================================

    def clean_date_avance(self):
        date_avance = self.cleaned_data.get("date_avance")

        if not date_avance:
            raise ValidationError(
                "Veuillez renseigner la date de l'avance."
            )

        return date_avance

    # ========================================================
    # VALIDATION GÉNÉRALE
    # UN SEUL BÉNÉFICIAIRE
    # ========================================================

    def clean(self):
        cleaned_data = super().clean()

        chef = cleaned_data.get("equipe_execution")
        minier = cleaned_data.get("miniers_execution")

        if self.projet is None:
            raise ValidationError(
                "Le projet doit être défini pour enregistrer l'avance."
            )

        # ----------------------------------------------------
        # OBLIGER À CHOISIR UN SEUL BÉNÉFICIAIRE
        # ----------------------------------------------------

        if chef and minier:
            message = (
                "Choisissez un seul bénéficiaire : "
                "un chef d'équipe ou un minier."
            )

            self.add_error("equipe_execution", message)
            self.add_error("miniers_execution", message)

        elif not chef and not minier:
            message = (
                "Veuillez sélectionner un chef d'équipe "
                "ou un minier."
            )

            self.add_error("equipe_execution", message)
            self.add_error("miniers_execution", message)

        # ----------------------------------------------------
        # VÉRIFIER LE CHEF D'ÉQUIPE
        # ----------------------------------------------------

        if chef:
            if chef.projet_id != self.projet.pk:
                self.add_error(
                    "equipe_execution",
                    "Ce bénéficiaire n'appartient pas à ce projet.",
                )

            elif chef.fonction != "CHEF_EQUIPE":
                self.add_error(
                    "equipe_execution",
                    "Le bénéficiaire sélectionné doit être un chef d'équipe.",
                )

        # ----------------------------------------------------
        # VÉRIFIER LE MINIER
        # ----------------------------------------------------

        if minier:
            if minier.projet_id != self.projet.pk:
                self.add_error(
                    "miniers_execution",
                    "Ce bénéficiaire n'appartient pas à ce projet.",
                )

            elif minier.fonction != "MINIER":
                self.add_error(
                    "miniers_execution",
                    "Le bénéficiaire sélectionné doit être un minier.",
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



# ============================================================
# FORMULAIRE UNIQUE DES MOUVEMENTS DE MATÉRIAUX
# ============================================================
class MouvementMateriauProjetForm(forms.ModelForm):

    class Meta:
        model = MouvementMateriauProjet

        fields = [
            "type_mouvement",
            "materiau_projet",
            "point_depart",
            "point_arrivee",
            "vehicule_transport",
            "date_mouvement",
            "quantite",
            "prix_unitaire",
            "observation",
        ]

        widgets = {
            "type_mouvement": forms.Select(
                attrs={"class": "form-select"}
            ),
            "materiau_projet": forms.Select(
                attrs={"class": "form-select"}
            ),
            "point_depart": forms.Select(
                attrs={"class": "form-select"}
            ),
            "point_arrivee": forms.Select(
                attrs={"class": "form-select"}
            ),
            "vehicule_transport": forms.Select(
                attrs={"class": "form-select"}
            ),
            "date_mouvement": forms.DateInput(
                attrs={
                    "class": "form-control",
                    "type": "date",
                }
            ),
            "quantite": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                    "placeholder": "Saisir la quantité",
                }
            ),
            "prix_unitaire": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "min": "0.01",
                    "step": "0.01",
                    "placeholder": "Prix unitaire en Ariary",
                }
            ),
            "observation": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Observation facultative",
                }
            ),
        }

    def __init__(self, *args, projet=None, **kwargs):
        super().__init__(*args, **kwargs)

        self.projet = projet

        # Libellés
        self.fields["type_mouvement"].label = "Type de mouvement"
        self.fields["materiau_projet"].label = "Matériau"
        self.fields["point_depart"].label = "Point d'origine"
        self.fields["point_arrivee"].label = "Point de destination"
        self.fields["vehicule_transport"].label = (
            "Véhicule / Engin de transport"
        )
        self.fields["date_mouvement"].label = "Date du mouvement"
        self.fields["quantite"].label = "Quantité"
        self.fields["prix_unitaire"].label = "Prix unitaire (Ar)"
        self.fields["observation"].label = "Observation"

        # Champs facultatifs
        for champ in (
            "point_depart",
            "point_arrivee",
            "vehicule_transport",
            "observation",
            "prix_unitaire",
        ):
            self.fields[champ].required = False

        # Querysets limités au projet
        self.fields["materiau_projet"].queryset = (
            MateriauProjet.objects.none()
        )
        self.fields["point_depart"].queryset = PointProjet.objects.none()
        self.fields["point_arrivee"].queryset = PointProjet.objects.none()
        self.fields["vehicule_transport"].queryset = (
            VehiculeProjet.objects.none()
        )

        self.fields["vehicule_transport"].empty_label = (
            "Aucun véhicule / engin"
        )
        self.fields["point_depart"].empty_label = (
            "Sélectionner le point d'origine"
        )
        self.fields["point_arrivee"].empty_label = (
            "Sélectionner le point de destination"
        )

        if projet is not None:
            self.fields["materiau_projet"].queryset = (
                MateriauProjet.objects
                .filter(projet=projet)
                .order_by("materiau", "id")
            )

            self.fields["point_depart"].queryset = (
                PointProjet.objects
                .filter(projet=projet)
                .order_by("id")
            )

            self.fields["point_arrivee"].queryset = (
                PointProjet.objects
                .filter(projet=projet)
                .order_by("id")
            )

            self.fields["vehicule_transport"].queryset = (
                VehiculeProjet.objects
                .filter(projet=projet, actif=True)
                .order_by("vehicule", "id")
            )

    def clean(self):
        cleaned_data = super().clean()

        materiau = cleaned_data.get("materiau_projet")
        type_mouvement = cleaned_data.get("type_mouvement")
        point_depart = cleaned_data.get("point_depart")
        point_arrivee = cleaned_data.get("point_arrivee")
        vehicule = cleaned_data.get("vehicule_transport")
        quantite = cleaned_data.get("quantite")
        prix_unitaire = cleaned_data.get("prix_unitaire")

        entree = (
            type_mouvement
            == MouvementMateriauProjet.TypeMouvement.ENTREE
        )
        sortie = (
            type_mouvement
            == MouvementMateriauProjet.TypeMouvement.SORTIE
        )
        retour = (
            type_mouvement
            == MouvementMateriauProjet.TypeMouvement.RETOUR
        )

        # Prix : obligatoire uniquement pour une entrée
        if entree:
            if prix_unitaire is None:
                self.add_error(
                    "prix_unitaire",
                    "Le prix unitaire est obligatoire pour une entrée.",
                )
            elif prix_unitaire <= 0:
                self.add_error(
                    "prix_unitaire",
                    "Le prix unitaire doit être supérieur à zéro.",
                )
        elif sortie or retour:
            cleaned_data["prix_unitaire"] = None

        # Quantité
        if quantite is not None and quantite <= 0:
            self.add_error(
                "quantite",
                "La quantité doit être supérieure à zéro.",
            )

        # Matériau appartenant au projet
        if self.projet and materiau:
            if materiau.projet_id != self.projet.pk:
                self.add_error(
                    "materiau_projet",
                    "Ce matériau n'appartient pas à ce projet.",
                )

        # Points appartenant au projet
        if self.projet and point_depart:
            if point_depart.projet_id != self.projet.pk:
                self.add_error(
                    "point_depart",
                    "Ce point d'origine n'appartient pas à ce projet.",
                )

        if self.projet and point_arrivee:
            if point_arrivee.projet_id != self.projet.pk:
                self.add_error(
                    "point_arrivee",
                    "Ce point de destination n'appartient pas à ce projet.",
                )

        # Véhicule appartenant au projet
        if self.projet and vehicule:
            if vehicule.projet_id != self.projet.pk:
                self.add_error(
                    "vehicule_transport",
                    "Ce véhicule ou engin n'appartient pas à ce projet.",
                )

        # Règles de circulation des matériaux
        if entree:
            if point_depart:
                self.add_error(
                    "point_depart",
                    "Pour une entrée, laissez le point d'origine vide.",
                )

            if not point_arrivee:
                self.add_error(
                    "point_arrivee",
                    "Indiquez le point qui reçoit le matériau.",
                )

        elif sortie:
            if not point_depart:
                self.add_error(
                    "point_depart",
                    "Indiquez le point d'où sort le matériau.",
                )

            if not point_arrivee:
                self.add_error(
                    "point_arrivee",
                    "Indiquez le point de destination du matériau.",
                )

            if (
                point_depart
                and point_arrivee
                and point_depart.pk == point_arrivee.pk
            ):
                self.add_error(
                    "point_arrivee",
                    "L'origine et la destination doivent être différentes.",
                )

        elif retour:
            if not point_depart:
                self.add_error(
                    "point_depart",
                    "Indiquez le point d'où revient le matériau.",
                )

            if not point_arrivee:
                self.add_error(
                    "point_arrivee",
                    "Indiquez le point qui reçoit le retour.",
                )

            if (
                point_depart
                and point_arrivee
                and point_depart.pk == point_arrivee.pk
            ):
                self.add_error(
                    "point_arrivee",
                    "L'origine et la destination doivent être différentes.",
                )

        elif type_mouvement:
            self.add_error(
                "type_mouvement",
                "Le type de mouvement sélectionné est invalide.",
            )

        return cleaned_data