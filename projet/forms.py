from django import forms
from django.utils import timezone
from decimal import Decimal
from personnel.models import Personnel
from materiaux.models import Materiaux, Vehicule

from .models import (Projet,EquipeProjet,PointProjet,EnginProjet,RapportProjet,
    RapportTravail,
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
        # HEURES
        # ----------------------------------------------------

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
            and heures_finales < heures_initiales
        ):

            self.add_error(
                "heures_finales",
                "Les heures finales doivent être "
                "supérieures ou égales aux heures initiales.",
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
            "date_mouvement",
            "point_depart",
            "point_arrivee",
            "heure_depart",
            "heure_arrivee",
            "kilometrage_initial",
            "kilometrage_final",
            "heures_initiales",
            "heures_finales",
            "carburant_litre",
            "observation",
        ]

        widgets = {
            "vehicule_projet": forms.Select(
                attrs={"class": "form-select"}
            ),

            "date_mouvement": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "class": "form-control",
                    "type": "datetime-local",
                },
            ),

            "point_depart": forms.Select(
                attrs={"class": "form-select"}
            ),

            "point_arrivee": forms.Select(
                attrs={"class": "form-select"}
            ),

            "heure_depart": forms.TimeInput(
                format="%H:%M",
                attrs={
                    "class": "form-control",
                    "type": "time",
                },
            ),

            "heure_arrivee": forms.TimeInput(
                format="%H:%M",
                attrs={
                    "class": "form-control",
                    "type": "time",
                },
            ),

            "kilometrage_initial": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Kilométrage initial",
                },
            ),

            "kilometrage_final": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Kilométrage final",
                },
            ),

            "heures_initiales": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Compteur horaire initial",
                },
            ),

            "heures_finales": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Compteur horaire final",
                },
            ),

            "carburant_litre": forms.NumberInput(
                attrs={
                    "class": "form-control",
                    "step": "0.01",
                    "min": "0",
                    "placeholder": "Carburant consommé en litres",
                },
            ),

            "observation": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Observation sur le mouvement...",
                },
            ),
        }

    def __init__(self, *args, **kwargs):
        projet = kwargs.pop("projet", None)

        super().__init__(*args, **kwargs)

        # Configuration générale des champs.
        for field_name, field in self.fields.items():
            field.required = field_name in (
                "vehicule_projet",
                "date_mouvement",
                "carburant_litre",
            )

            if field_name not in (
                "vehicule_projet",
                "point_depart",
                "point_arrivee",
            ):
                field.widget.attrs.setdefault(
                    "class", "form-control"
                )

        # Limiter les véhicules au projet concerné si le projet est fourni.
        if projet is not None:
            self.fields["vehicule_projet"].queryset = (
                VehiculeProjet.objects.filter(projet=projet)
            )

            self.fields["point_depart"].queryset = (
                PointProjet.objects.filter(projet=projet)
            )

            self.fields["point_arrivee"].queryset = (
                PointProjet.objects.filter(projet=projet)
            )
        else:
            self.fields["vehicule_projet"].queryset = (
                VehiculeProjet.objects.all()
            )

            self.fields["point_depart"].queryset = (
                PointProjet.objects.all()
            )

            self.fields["point_arrivee"].queryset = (
                PointProjet.objects.all()
            )

    def clean(self):
        cleaned_data = super().clean()

        vehicule = cleaned_data.get("vehicule_projet")
        km_initial = cleaned_data.get("kilometrage_initial")
        km_final = cleaned_data.get("kilometrage_final")
        heures_initiales = cleaned_data.get("heures_initiales")
        heures_finales = cleaned_data.get("heures_finales")
        carburant = cleaned_data.get("carburant_litre")

        # Validation du kilométrage pour les véhicules routiers.
        if vehicule and vehicule.type_vehicule != "ENGIN":
            if (
                km_initial is not None
                and km_final is not None
                and km_final < km_initial
            ):
                self.add_error(
                    "kilometrage_final",
                    "Le kilométrage final doit être supérieur "
                    "ou égal au kilométrage initial.",
                )

        # Validation du compteur horaire pour les engins.
        if vehicule and vehicule.type_vehicule == "ENGIN":
            if (
                heures_initiales is not None
                and heures_finales is not None
                and heures_finales > heures_initiales
            ):
                self.add_error(
                    "heures_finales",
                    "Le compteur final doit être inférieur ou égal au compteur initial.",
                )

        # Validation du carburant.
        if carburant is not None and carburant < Decimal("0.00"):
            self.add_error(
                "carburant_litre",
                "La quantité de carburant ne peut pas être négative.",
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