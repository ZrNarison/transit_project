from decimal import Decimal
from datetime import timedelta
from django.core.validators import MinValueValidator
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from users.models import AppUser
from personnel.models import Personnel


# ============================================================
# PROJET
# ============================================================

class Projet(models.Model):
    """
    Projet / chantier de l'entreprise.
    """

    STATUT_CHOICES = [
        ("PLANIFIE", "Planifié"),
        ("EN_COURS", "En cours"),
        ("TERMINE", "Terminé"),
        ("SUSPENDU", "Suspendu"),
    ]

    titre = models.CharField(
        max_length=200,
        verbose_name="Titre du projet",
    )

    localisation = models.CharField(
        max_length=200,
        verbose_name="Localisation",
    )

    date_debut = models.DateField(
        verbose_name="Date de début",
    )

    date_fin = models.DateField(
        verbose_name="Date de fin",
    )

    statut = models.CharField(
        max_length=20,
        choices=STATUT_CHOICES,
        default="PLANIFIE",
        verbose_name="Statut",
    )

    budget_previsionnel = models.DecimalField(
        max_digits=15,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Budget prévisionnel",
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation",
    )

    enregistre_par = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="projets_enregistres",
        verbose_name="Enregistré par",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-date_debut",
            "-id",
        ]
        verbose_name = "Projet"
        verbose_name_plural = "Projets"

    def __str__(self):
        return f"{self.titre} - {self.localisation}"

    def clean(self):
        errors = {}

        # ----------------------------------------------------
        # DATES
        # ----------------------------------------------------

        if self.date_debut and self.date_fin:

            if self.date_fin < self.date_debut:
                errors["date_fin"] = (
                    "La date de fin doit être "
                    "postérieure ou égale à la date de début."
                )

        # ----------------------------------------------------
        # BUDGET
        # ----------------------------------------------------

        if (
            self.budget_previsionnel is not None
            and self.budget_previsionnel < Decimal("0.00")
        ):
            errors["budget_previsionnel"] = (
                "Le budget prévisionnel ne peut pas être négatif."
            )

        if errors:
            raise ValidationError(errors)

    @property
    def est_actif(self):
        """
        Projet actif uniquement lorsque :
        - la date actuelle est comprise dans la période ;
        - le statut est EN_COURS.
        """

        if not self.date_debut or not self.date_fin:
            return False

        aujourd_hui = timezone.localdate()

        return (
            self.date_debut
            <= aujourd_hui
            <= self.date_fin
            and self.statut == "EN_COURS"
        )

    @property
    def periode_terminee(self):
        """
        True lorsque la date de fin du projet est dépassée.
        """

        if not self.date_fin:
            return False

        return timezone.localdate() > self.date_fin

    @property
    def jours_restants(self):
        """
        Nombre de jours restants avant la fin du projet.
        """

        if not self.date_fin:
            return 0

        aujourd_hui = timezone.localdate()

        if aujourd_hui > self.date_fin:
            return 0

        return (self.date_fin - aujourd_hui).days

class PersonnelExecutionProjet(models.Model):
    """
    Personnel ou personne externe intervenant dans l'exécution
    d'un projet.
    """

    # ============================================================
    # TYPES
    # ============================================================

    TYPE_CLASS_CHOICES = [
        ("CHEF_EQUIPE", "Chef d'équipe"),
        ("CHAUFFEUR_ENGIN", "Chauffeur d'engin"),
        ("MINIER", "Minier"),
        ("AUTRE", "Autre"),
    ]

    # ============================================================
    # PROJET
    # ============================================================

    projet = models.ForeignKey(
        "Projet",
        on_delete=models.PROTECT,
        related_name="personnels_execution",
        verbose_name="Projet",
    )

    # ============================================================
    # PERSONNEL INTERNE
    # ============================================================

    personnel = models.ForeignKey(
        "personnel.Personnel",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="executions_projets",
        verbose_name="Personnel",
    )

    # ============================================================
    # NOM
    # ============================================================

    nom = models.CharField(
        max_length=150,
        verbose_name="Nom",
    )

    # ============================================================
    # TYPE
    # ============================================================

    type_class = models.CharField(
        max_length=30,
        choices=TYPE_CLASS_CHOICES,
        verbose_name="Type",
    )

    # ============================================================
    # MONTANT
    # ============================================================

    montant = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Montant",
    )

    # ============================================================
    # PÉRIODE
    # ============================================================

    date_debut = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de début",
    )

    date_fin = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de fin",
    )

    # ============================================================
    # PHOTO
    # ============================================================

    photo = models.ImageField(
        upload_to="personnels_execution/",
        null=True,
        blank=True,
        verbose_name="Photo",
    )

    # ============================================================
    # POINT DU PROJET
    # ============================================================

    point_projet = models.ForeignKey(
        "PointProjet",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="personnels_execution",
        verbose_name="Point du projet",
    )

    # ============================================================
    # MATÉRIAU DU PROJET
    # ============================================================

    materiau_projet = models.ForeignKey(
        "MateriauProjet",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="miniers",
        verbose_name="Matériau du projet",
    )

    # ============================================================
    # PRODUCTION
    # ============================================================

    quantite = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Quantité",
    )

    prix_unitaire = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Prix unitaire",
    )

    date_production = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de production",
    )

    # ============================================================
    # OBSERVATION
    # ============================================================

    observation = models.TextField(
        blank=True,
        verbose_name="Observation",
    )

    # ============================================================
    # ENREGISTREUR
    # ============================================================

    enregistre_par = models.ForeignKey(
        "personnel.Personnel",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="personnels_execution_enregistres",
        verbose_name="Enregistré par",
    )

    # ============================================================
    # DATES TECHNIQUES
    # ============================================================

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    # ============================================================
    # META
    # ============================================================

    class Meta:
        ordering = [
            "-date_debut",
            "-date_production",
            "nom",
        ]

        verbose_name = (
            "Personnel d'exécution du projet"
        )

        verbose_name_plural = (
            "Personnels d'exécution des projets"
        )

    # ============================================================
    # AFFICHAGE
    # ============================================================

    def __str__(self):

        if self.type_class == "MINIER":

            if self.materiau_projet_id:
                materiau = str(
                    self.materiau_projet
                )
            else:
                materiau = "Sans matériau"

            return (
                f"{self.nom} - "
                f"Minier - "
                f"{materiau}"
            )

        if self.type_class == "CHEF_EQUIPE":

            if self.point_projet_id:
                point = str(
                    self.point_projet
                )
            else:
                point = "Sans point"

            return (
                f"{self.nom} - "
                f"Chef d'équipe - "
                f"{point}"
            )

        return (
            f"{self.nom} - "
            f"{self.get_type_class_display()} - "
            f"{self.projet.titre}"
        )

    # ============================================================
    # MONTANT TOTAL DE PRODUCTION
    # ============================================================

    @property
    def montant_total_production(self):

        if self.type_class != "MINIER":
            return Decimal("0.00")

        quantite = (
            self.quantite
            if self.quantite is not None
            else Decimal("0.00")
        )

        prix_unitaire = (
            self.prix_unitaire
            if self.prix_unitaire is not None
            else Decimal("0.00")
        )

        return (
            quantite * prix_unitaire
        ).quantize(
            Decimal("0.01")
        )

    # ============================================================
    # MONTANT TOTAL DU PAIEMENT
    # ============================================================

    @property
    def montant_total_paiement(self):

        if self.type_class == "MINIER":
            return self.montant_total_production

        return (
            self.montant
            if self.montant is not None
            else Decimal("0.00")
        )

    # ============================================================
    # ACCÈS ACTIF
    # ============================================================

    @property
    def acces_actif(self):

        aujourd_hui = timezone.localdate()

        # --------------------------------------------------------
        # MINIER
        # --------------------------------------------------------

        if self.type_class == "MINIER":

            if not self.date_production:
                return False

            return (
                self.date_production
                == aujourd_hui
            )

        # --------------------------------------------------------
        # AUTRES TYPES
        # --------------------------------------------------------

        if not self.date_debut:
            return False

        if not self.date_fin:
            return (
                aujourd_hui
                >= self.date_debut
            )

        return (
            self.date_debut
            <= aujourd_hui
            <= self.date_fin
        )

    # ============================================================
    # PÉRIODE TERMINÉE
    # ============================================================

    @property
    def periode_terminee(self):

        aujourd_hui = timezone.localdate()

        # --------------------------------------------------------
        # MINIER
        # --------------------------------------------------------

        if self.type_class == "MINIER":

            if not self.date_production:
                return False

            return (
                aujourd_hui
                > self.date_production
            )

        # --------------------------------------------------------
        # AUTRES TYPES
        # --------------------------------------------------------

        if not self.date_fin:
            return False

        return (
            aujourd_hui
            > self.date_fin
        )

    # ============================================================
    # VALIDATION
    # ============================================================

    def clean(self):

        errors = {}

        # ========================================================
        # PROJET
        # ========================================================

        projet = (
            self.projet
            if self.projet_id
            else None
        )

        # ========================================================
        # VALIDATION DES DATES
        # ========================================================

        if (
            self.date_debut
            and self.date_fin
            and self.date_fin < self.date_debut
        ):
            errors["date_fin"] = (
                "La date de fin doit être "
                "postérieure ou égale à la "
                "date de début."
            )

        # ========================================================
        # LIMITES PAR RAPPORT AU PROJET
        # ========================================================

        if projet:

            if (
                self.date_debut
                and projet.date_debut
                and self.date_debut
                < projet.date_debut
            ):
                errors["date_debut"] = (
                    "La date de début du personnel "
                    "ne peut pas être antérieure "
                    "au début du projet."
                )

            if (
                self.date_fin
                and projet.date_fin
                and self.date_fin
                > projet.date_fin
            ):
                errors["date_fin"] = (
                    "La date de fin du personnel "
                    "ne peut pas dépasser la "
                    "date de fin du projet."
                )

        # ========================================================
        # MONTANT
        # ========================================================

        if (
            self.montant is not None
            and self.montant
            < Decimal("0.00")
        ):
            errors["montant"] = (
                "Le montant ne peut pas être négatif."
            )

        # ========================================================
        # TYPES EXTERNES
        # ========================================================

        TYPES_EXTERNES = {
            "CHEF_EQUIPE",
            "CHAUFFEUR_ENGIN",
            "MINIER",
            "AUTRE",
        }

        # ========================================================
        # PERSONNEL / NOM
        # ========================================================

        if self.type_class in TYPES_EXTERNES:

            # Ces types sont des personnes externes.
            if self.personnel_id:

                errors["personnel"] = (
                    "Ce type de personnel est externe "
                    "et ne doit pas être lié à un "
                    "personnel interne."
                )

            if (
                not self.nom
                or not self.nom.strip()
            ):
                errors["nom"] = (
                    "Le nom est obligatoire pour "
                    "ce type de personnel."
                )

        else:

            # Pour un éventuel type interne.
            if not self.personnel_id:

                errors["personnel"] = (
                    "Un personnel interne doit "
                    "être sélectionné."
                )

        # ========================================================
        # CHEF D'ÉQUIPE
        # ========================================================

        if self.type_class == "CHEF_EQUIPE":

            if not self.point_projet_id:

                errors["point_projet"] = (
                    "Le point du projet est obligatoire "
                    "pour un chef d'équipe."
                )

            if self.materiau_projet_id:

                errors["materiau_projet"] = (
                    "Un chef d'équipe ne peut pas "
                    "être associé à un matériau."
                )

            if (
                self.montant is None
                or self.montant
                <= Decimal("0.00")
            ):

                errors["montant"] = (
                    "Le montant est obligatoire et "
                    "doit être supérieur à zéro "
                    "pour un chef d'équipe."
                )

            if (
                self.quantite
                and self.quantite
                > Decimal("0.00")
            ):

                errors["quantite"] = (
                    "La quantité est réservée "
                    "aux miniers."
                )

            if (
                self.prix_unitaire
                and self.prix_unitaire
                > Decimal("0.00")
            ):

                errors["prix_unitaire"] = (
                    "Le prix unitaire est réservé "
                    "aux miniers."
                )

            if self.date_production:

                errors["date_production"] = (
                    "La date de production est "
                    "réservée aux miniers."
                )

        # ========================================================
        # MINIER
        # ========================================================

        elif self.type_class == "MINIER":

            # ----------------------------------------------------
            # MATÉRIAU OBLIGATOIRE
            # ----------------------------------------------------

            if not self.materiau_projet_id:

                errors["materiau_projet"] = (
                    "Le matériau est obligatoire "
                    "pour un minier."
                )

            # ----------------------------------------------------
            # PAS DE POINT
            # ----------------------------------------------------

            if self.point_projet_id:

                errors["point_projet"] = (
                    "Un minier ne peut pas être "
                    "associé à un point du projet."
                )

            # ----------------------------------------------------
            # QUANTITÉ
            # ----------------------------------------------------

            if self.quantite is None:

                errors["quantite"] = (
                    "La quantité est obligatoire "
                    "pour un minier."
                )

            elif self.quantite <= Decimal("0.00"):

                errors["quantite"] = (
                    "La quantité doit être "
                    "supérieure à zéro."
                )

            # ----------------------------------------------------
            # PRIX UNITAIRE
            # ----------------------------------------------------

            if self.prix_unitaire is None:

                errors["prix_unitaire"] = (
                    "Le prix unitaire est obligatoire "
                    "pour un minier."
                )

            elif (
                self.prix_unitaire
                <= Decimal("0.00")
            ):

                errors["prix_unitaire"] = (
                    "Le prix unitaire doit être "
                    "supérieur à zéro."
                )

            # ----------------------------------------------------
            # DATE DE PRODUCTION
            # ----------------------------------------------------

            if not self.date_production:

                errors["date_production"] = (
                    "La date de production est "
                    "obligatoire pour un minier."
                )

            # ----------------------------------------------------
            # DATE PAR RAPPORT AU PROJET
            # ----------------------------------------------------

            if (
                projet
                and self.date_production
            ):

                if (
                    projet.date_debut
                    and self.date_production
                    < projet.date_debut
                ):

                    errors["date_production"] = (
                        "La date de production ne peut "
                        "pas être antérieure au début "
                        "du projet."
                    )

                if (
                    projet.date_fin
                    and self.date_production
                    > projet.date_fin
                ):

                    errors["date_production"] = (
                        "La date de production ne peut "
                        "pas dépasser la fin du projet."
                    )

            # ----------------------------------------------------
            # MONTANT AUTOMATIQUE
            # ----------------------------------------------------

            if (
                self.montant
                and self.montant
                > Decimal("0.00")
            ):

                errors["montant"] = (
                    "Pour un minier, le montant est "
                    "calculé automatiquement avec "
                    "la quantité et le prix unitaire."
                )

        # ========================================================
        # CHAUFFEUR D'ENGIN / AUTRE
        # ========================================================

        elif self.type_class in {
            "CHAUFFEUR_ENGIN",
            "AUTRE",
        }:

            if self.point_projet_id:

                errors["point_projet"] = (
                    "Ce type de personnel ne peut "
                    "pas être associé à un point "
                    "du projet."
                )

            if self.materiau_projet_id:

                errors["materiau_projet"] = (
                    "Ce type de personnel ne peut "
                    "pas être associé à un matériau."
                )

            if (
                self.quantite
                and self.quantite
                > Decimal("0.00")
            ):

                errors["quantite"] = (
                    "La quantité de production est "
                    "réservée aux miniers."
                )

            if (
                self.prix_unitaire
                and self.prix_unitaire
                > Decimal("0.00")
            ):

                errors["prix_unitaire"] = (
                    "Le prix unitaire est réservé "
                    "aux miniers."
                )

            if self.date_production:

                errors["date_production"] = (
                    "La date de production est "
                    "réservée aux miniers."
                )

        # ========================================================
        # VÉRIFICATION MATÉRIAU / PROJET
        # ========================================================
        #
        # IMPORTANT :
        # MateriauProjet NE possède PAS de champ "actif".
        #
        # On vérifie uniquement que le matériau appartient
        # au même projet.
        #

        if (
            self.materiau_projet_id
            and self.projet_id
        ):

            if (
                self.materiau_projet.projet_id
                != self.projet_id
            ):

                errors["materiau_projet"] = (
                    "Le matériau sélectionné "
                    "n'appartient pas à ce projet."
                )

        # ========================================================
        # VÉRIFICATION POINT / PROJET
        # ========================================================

        if (
            self.point_projet_id
            and self.projet_id
        ):

            if (
                self.point_projet.projet_id
                != self.projet_id
            ):

                errors["point_projet"] = (
                    "Le point sélectionné "
                    "n'appartient pas à ce projet."
                )

            elif not self.point_projet.actif:

                errors["point_projet"] = (
                    "Le point sélectionné "
                    "n'est plus actif pour ce projet."
                )

        # ========================================================
        # ERREURS
        # ========================================================

        if errors:
            raise ValidationError(errors)



# ============================================================
# EQUIPE DU PROJET
# ============================================================

class EquipeProjet(models.Model):
    """
    Affectation d'une personne à l'équipe du projet.
    """

    FONCTION_CHOICES = [
        (
            "INGENIEUR",
            "Ingénieur Responsable du Chantier",
        ),
        (
            "CHEF_CHANTIER",
            "Chef de Chantier",
        ),
        (
            "CHEF_MAGASIN",
            "Chef Magasinier",
        ),
        (
            "MAGASINIER",
            "Magasinier",
        ),
        (
            "CHAUFFEUR",
            "Chauffeur",
        ),
        (
            "OUVRIER",
            "Ouvrier",
        ),
        (
            "CHEF_EQUIPE",
            "Chef d'équipe",
        ),
        (
            "MINIER",
            "Minier",
        ),
        (
            "AUTRE",
            "Autre",
        ),
    ]

    projet = models.ForeignKey(
        Projet,
        on_delete=models.PROTECT,
        related_name="equipe",
        verbose_name="Projet",
    )

    # --------------------------------------------------------
    # PERSONNEL ENTREPRISE
    # --------------------------------------------------------

    personnel = models.ForeignKey(
        Personnel,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="affectations_projets",
        verbose_name="Personnel de l'entreprise",
    )

    # --------------------------------------------------------
    # PERSONNE INSCRITE POUR LE PROJET
    # --------------------------------------------------------

    personnel_execution = models.ForeignKey(
        "PersonnelExecutionProjet",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="affectations_equipe",
        verbose_name="Personnel d'exécution du projet",
    )

    fonction = models.CharField(
        max_length=30,
        choices=FONCTION_CHOICES,
        verbose_name="Fonction sur le projet",
    )

    date_debut = models.DateField(
        verbose_name="Début de l'affectation",
    )

    date_fin = models.DateField(
        verbose_name="Fin de l'affectation",
    )

    actif = models.BooleanField(
        default=True,
        verbose_name="Affectation active",
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "projet",
            "fonction",
        ]
        verbose_name = "Équipe de projet"
        verbose_name_plural = "Équipe des projets"

    def __str__(self):

        if self.personnel_execution_id:
            personne = self.personnel_execution.nom

        elif self.personnel_id:
            personne = str(self.personnel)

        else:
            personne = "Personne non définie"

        return (
            f"{personne} - "
            f"{self.get_fonction_display()} - "
            f"{self.projet.titre}"
        )

    def clean(self):
        errors = {}

        # ----------------------------------------------------
        # UNE SEULE SOURCE DE PERSONNE
        # ----------------------------------------------------

        if not self.personnel_id and not self.personnel_execution_id:

            errors["personnel"] = (
                "Sélectionnez soit un personnel de l'entreprise, "
                "soit une personne inscrite pour l'exécution du projet."
            )

        if self.personnel_id and self.personnel_execution_id:

            errors["personnel"] = (
                "Une affectation ne peut pas avoir simultanément "
                "un personnel entreprise et un personnel d'exécution."
            )

        # ----------------------------------------------------
        # PERSONNEL ENTREPRISE
        # ----------------------------------------------------

        if self.personnel_id:

            personnel = self.personnel

            if personnel.typeTravail != "Construction":

                errors["personnel"] = (
                    "Le personnel affecté à un projet doit "
                    "appartenir au personnel Construction."
                )

            # Les fonctions externes doivent utiliser
            # PersonnelExecutionProjet.
            if self.fonction in {
                "CHEF_EQUIPE",
                "MINIER",
            }:
                errors["personnel"] = (
                    "Pour cette fonction, utilisez "
                    "l'inscription du Personnel d'exécution du projet."
                )

        # ----------------------------------------------------
        # PERSONNEL D'EXÉCUTION
        # ----------------------------------------------------

        if self.personnel_execution_id:

            execution = self.personnel_execution

            if execution.projet_id != self.projet_id:

                errors["personnel_execution"] = (
                    "La personne inscrite doit appartenir "
                    "au même projet."
                )

            # ------------------------------------------------
            # Correspondance fonction / inscription
            # ------------------------------------------------

            correspondance = {
                "CHEF_EQUIPE": "CHEF_EQUIPE",
                "MINIER": "MINIER",
                "CHEF_CHANTIER": "CHEF_CHANTIER",
                "INGENIEUR": "INGENIEUR",
                "CHAUFFEUR": "CHAUFFEUR",
                "CHEF_MAGASIN": "CHEF_MAGASIN",
                "MAGASINIER": "MAGASIN",
            }

            type_attendu = correspondance.get(self.fonction)

            if (
                type_attendu
                and execution.type_class != type_attendu
            ):
                errors["personnel_execution"] = (
                    "La fonction de l'affectation ne correspond "
                    "pas au type de l'inscription."
                )

        # ----------------------------------------------------
        # DATES
        # ----------------------------------------------------

        if self.date_debut and self.date_fin:

            if self.date_fin < self.date_debut:

                errors["date_fin"] = (
                    "La fin de l'affectation doit être "
                    "postérieure ou égale au début."
                )

        # ----------------------------------------------------
        # LIMITES DU PROJET
        # ----------------------------------------------------

        if self.projet_id:

            projet = self.projet

            if (
                self.date_debut
                and projet.date_debut
                and self.date_debut < projet.date_debut
            ):
                errors["date_debut"] = (
                    "L'affectation ne peut pas commencer "
                    "avant le début du projet."
                )

            if (
                self.date_fin
                and projet.date_fin
                and self.date_fin > projet.date_fin
            ):
                errors["date_fin"] = (
                    "L'affectation ne peut pas dépasser "
                    "la date de fin du projet."
                )

        if errors:
            raise ValidationError(errors)

    @property
    def acces_actif(self):

        if not self.actif:
            return False

        if not self.date_debut or not self.date_fin:
            return False

        aujourd_hui = timezone.localdate()

        return (
            self.date_debut
            <= aujourd_hui
            <= self.date_fin
        )

    @property
    def utilisateur(self):

        if self.personnel_id:

            return getattr(
                self.personnel,
                "user",
                None,
            )

        return None

    @property
    def periode_terminee(self):

        if not self.date_fin:
            return False

        return timezone.localdate() > self.date_fin



# ============================================================
# POINT DE CHANTIER
# ============================================================

class PointProjet(models.Model):

    projet = models.ForeignKey(
        Projet,
        on_delete=models.PROTECT,
        related_name="points",
        verbose_name="Projet",
    )

    nom = models.CharField(
        max_length=150,
        verbose_name="Nom du point",
    )

    localisation = models.CharField(
        max_length=250,
        blank=True,
        verbose_name="Localisation",
    )

    distance_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Distance (km)",
    )

    travail_prevu = models.CharField(
        max_length=255,
        verbose_name="Travail prévu",
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation",
    )

    actif = models.BooleanField(
        default=True,
        verbose_name="Point actif",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "projet",
            "nom",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "projet",
                    "nom",
                ],
                name="unique_code_point_projet",
            ),
        ]
        verbose_name = "Point de chantier"
        verbose_name_plural = "Points de chantier"

    def __str__(self):
        return f"{self.nom} - ({self.distance_km} km)"

    def clean(self):
        errors = {}

        if (
            self.distance_km is not None
            and self.distance_km < Decimal("0.00")
        ):
            errors["distance_km"] = (
                "La distance ne peut pas être négative."
            )

        if errors:
            raise ValidationError(errors)

class MateriauProjet(models.Model):
    """
    Matériau prévu pour un projet.

    Le nom du matériau est enregistré directement
    dans ce modèle sous forme de texte.
    """

    projet = models.ForeignKey(
        Projet,
        on_delete=models.PROTECT,
        related_name="materiaux_projet",
        verbose_name="Projet",
    )

    materiau = models.CharField(
        max_length=150,
        verbose_name="Matériau",
    )

    unite = models.CharField(
        max_length=50,
        verbose_name="Unité",
    )

    quantite_prevue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Quantité prévue",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "projet",
            "materiau",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "projet",
                    "materiau",
                ],
                name="unique_materiau_projet",
            ),
        ]

        verbose_name = "Matériau du projet"
        verbose_name_plural = "Matériaux du projet"

    def __str__(self):
        return (
            f"{self.materiau} - "
            f"{self.projet.titre}"
        )

    def clean(self):
        errors = {}

        if (
            self.quantite_prevue is not None
            and self.quantite_prevue < Decimal("0.00")
        ):
            errors["quantite_prevue"] = (
                "La quantité prévue ne peut pas être négative."
            )

        if errors:
            raise ValidationError(errors)



# ============================================================
# RAPPORT DE L'INGÉNIEUR
# ============================================================

class RapportProjet(models.Model):

    projet = models.ForeignKey(
        Projet,
        on_delete=models.PROTECT,
        related_name="rapports_projet",
        verbose_name="Projet",
    )

    auteur = models.ForeignKey(
        Personnel,
        on_delete=models.PROTECT,
        related_name="rapports_projet",
        verbose_name="Auteur",
    )

    date_rapport = models.DateField(
        default=timezone.localdate,
        verbose_name="Date du rapport",
    )

    titre = models.CharField(
        max_length=200,
        verbose_name="Titre",
    )

    avancement = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Avancement (%)",
    )

    travaux_realises = models.TextField(
        blank=True,
        verbose_name="Travaux réalisés",
    )

    difficultes = models.TextField(
        blank=True,
        verbose_name="Difficultés rencontrées",
    )

    actions_planifiees = models.TextField(
        blank=True,
        verbose_name="Plan d'action",
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-date_rapport",
            "-id",
        ]
        verbose_name = "Rapport de projet"
        verbose_name_plural = "Rapports de projet"

    def __str__(self):
        return f"{self.titre} - {self.projet.titre}"

    def clean(self):
        errors = {}

        if self.avancement is not None:

            if (
                self.avancement < Decimal("0.00")
                or self.avancement > Decimal("100.00")
            ):
                errors["avancement"] = (
                    "L'avancement doit être compris "
                    "entre 0 et 100 %."
                )

        if self.projet_id and self.date_rapport:

            projet = self.projet

            if self.date_rapport < projet.date_debut:

                errors["date_rapport"] = (
                    "La date du rapport ne peut pas "
                    "être avant le début du projet."
                )

            elif self.date_rapport > projet.date_fin:

                errors["date_rapport"] = (
                    "La date du rapport ne peut pas "
                    "dépasser la fin du projet."
                )

        if self.auteur_id:

            if self.auteur.typeTravail != "Construction":

                errors["auteur"] = (
                    "L'auteur doit appartenir "
                    "au personnel Construction."
                )

        if errors:
            raise ValidationError(errors)


# ============================================================
# RAPPORT DES TRAVAUX DU CHEF DE CHANTIER
# ============================================================

class RapportTravail(models.Model):

    projet = models.ForeignKey(
        Projet,
        on_delete=models.PROTECT,
        related_name="rapports_travaux",
        verbose_name="Projet",
    )

    point = models.ForeignKey(
        PointProjet,
        on_delete=models.PROTECT,
        related_name="rapports_travaux",
        verbose_name="Point de chantier",
        null=True,
        blank=True,
    )

    auteur = models.ForeignKey(
        Personnel,
        on_delete=models.PROTECT,
        related_name="rapports_travaux",
        verbose_name="Chef de chantier",
    )

    titre = models.CharField(
        max_length=200,
        verbose_name="Titre du travail",
    )

    localisation = models.CharField(
        max_length=200,
        blank=True,
        verbose_name="Localisation",
    )

    date_debut = models.DateField(
        verbose_name="Date de début",
    )

    date_fin = models.DateField(
        null=True,
        blank=True,
        verbose_name="Date de fin",
    )

    description = models.TextField(
        blank=True,
        verbose_name="Description",
    )

    photo = models.ImageField(
        upload_to="projets/travaux/",
        blank=True,
        null=True,
        verbose_name="Photo du travail",
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-date_debut",
            "-id",
        ]
        verbose_name = "Rapport de travail"
        verbose_name_plural = "Rapports de travaux"

    def __str__(self):
        return f"{self.titre} - {self.projet.titre}"

    def clean(self):
        errors = {}

        if (
            self.date_debut
            and self.date_fin
            and self.date_fin < self.date_debut
        ):
            errors["date_fin"] = (
                "La date de fin doit être "
                "postérieure ou égale à la date de début."
            )

        if self.projet_id:

            projet = self.projet

            if (
                self.date_debut
                and self.date_debut < projet.date_debut
            ):
                errors["date_debut"] = (
                    "La date de début du travail "
                    "ne peut pas être avant le projet."
                )

            if (
                self.date_fin
                and self.date_fin > projet.date_fin
            ):
                errors["date_fin"] = (
                    "La date de fin du travail "
                    "ne peut pas dépasser le projet."
                )

        if self.point_id and self.projet_id:

            if self.point.projet_id != self.projet_id:
                errors["point"] = (
                    "Le point sélectionné "
                    "n'appartient pas à ce projet."
                )

        if self.auteur_id:

            if self.auteur.typeTravail != "Construction":
                errors["auteur"] = (
                    "Le chef de chantier doit appartenir "
                    "au personnel Construction."
                )

        if errors:
            raise ValidationError(errors)


# ============================================================
# RAPPORT MATÉRIAUX
# ============================================================

class RapportMateriau(models.Model):

    projet = models.ForeignKey(
        Projet,
        on_delete=models.PROTECT,
        related_name="rapports_materiaux",
        verbose_name="Projet",
    )

    point = models.ForeignKey(
        PointProjet,
        on_delete=models.PROTECT,
        related_name="rapports_materiaux",
        null=True,
        blank=True,
        verbose_name="Point de chantier",
    )

    materiau = models.ForeignKey(
        "materiaux.Materiaux",
        on_delete=models.PROTECT,
        related_name="rapports_projets",
        verbose_name="Matériau",
    )

    auteur = models.ForeignKey(
        Personnel,
        on_delete=models.PROTECT,
        related_name="rapports_materiaux",
        verbose_name="Magasinier",
    )

    quantite = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Quantité",
    )

    point_ravitaillement = models.CharField(
        max_length=200,
        verbose_name="Point de ravitaillement",
    )

    date_ravitaillement = models.DateField(
        verbose_name="Date de ravitaillement",
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-date_ravitaillement",
            "-id",
        ]
        verbose_name = "Rapport matériau"
        verbose_name_plural = "Rapports matériaux"

    def __str__(self):
        return (
            f"{self.materiau} - "
            f"{self.quantite} - "
            f"{self.projet.titre}"
        )

    def clean(self):
        errors = {}

        if (
            self.quantite is not None
            and self.quantite <= Decimal("0.00")
        ):
            errors["quantite"] = (
                "La quantité doit être supérieure à zéro."
            )

        if self.projet_id and self.point_id:

            if self.point.projet_id != self.projet_id:
                errors["point"] = (
                    "Le point sélectionné "
                    "n'appartient pas à ce projet."
                )

        if self.projet_id and self.date_ravitaillement:

            projet = self.projet

            if self.date_ravitaillement < projet.date_debut:
                errors["date_ravitaillement"] = (
                    "La date de ravitaillement "
                    "ne peut pas être avant le début du projet."
                )

            elif self.date_ravitaillement > projet.date_fin:
                errors["date_ravitaillement"] = (
                    "La date de ravitaillement "
                    "ne peut pas dépasser la fin du projet."
                )

        if self.auteur_id:

            if self.auteur.typeTravail != "Construction":
                errors["auteur"] = (
                    "Le magasinier doit appartenir "
                    "au personnel Construction."
                )

        if errors:
            raise ValidationError(errors)



# ============================================================
# ENGIN AFFECTÉ AU PROJET
# ============================================================

class EnginProjet(models.Model):

    projet = models.ForeignKey(
        Projet,
        on_delete=models.PROTECT,
        related_name="engins_projet",
        verbose_name="Projet",
    )

    engin = models.CharField(
        max_length=30,
        verbose_name="Engin",
    )

    conducteur = models.ForeignKey(
        Personnel,
        on_delete=models.PROTECT,
        related_name="affectations_engins_projets",
        verbose_name="Conducteur",
        null=True,
        blank=True,
    )

    date_debut = models.DateField(
        verbose_name="Début de l'affectation",
    )

    date_fin = models.DateField(
        verbose_name="Fin de l'affectation",
    )

    heures_initiales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Heures initiales",
    )

    heures_finales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Heures finales",
    )

    consommation_heure_litre = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Consommation (L/h)",
    )

    actif = models.BooleanField(
        default=True,
        verbose_name="Affectation active",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = ["-date_debut", "-id"]

        constraints = [
            models.UniqueConstraint(
                fields=["projet", "engin"],
                name="unique_engin_projet",
            ),
        ]

        verbose_name = "Engin affecté au projet"
        verbose_name_plural = "Engins affectés aux projets"

    def __str__(self):
        conducteur = (
            str(self.conducteur)
            if self.conducteur_id
            else "Sans conducteur"
        )

        return (
            f"{self.engin} - "
            f"{self.projet.titre} - "
            f"{conducteur}"
        )

    def clean(self):
        errors = {}

        # ----------------------------------------------------
        # DATES
        # ----------------------------------------------------
        if self.date_debut and self.date_fin:
            if self.date_fin < self.date_debut:
                errors["date_fin"] = (
                    "La date de fin doit être postérieure "
                    "ou égale à la date de début."
                )

        # ----------------------------------------------------
        # PÉRIODE DU PROJET
        # ----------------------------------------------------
        if self.projet_id:
            projet = self.projet

            if (
                self.date_debut
                and projet.date_debut
                and self.date_debut < projet.date_debut
            ):
                errors["date_debut"] = (
                    "L'affectation ne peut pas commencer "
                    "avant le début du projet."
                )

            if (
                self.date_fin
                and projet.date_fin
                and self.date_fin > projet.date_fin
            ):
                errors["date_fin"] = (
                    "L'affectation ne peut pas dépasser "
                    "la date de fin du projet."
                )

        # ----------------------------------------------------
        # COMPTEUR D'HEURES
        # ----------------------------------------------------
        if (
            self.heures_initiales is not None
            and self.heures_initiales < Decimal("0.00")
        ):
            errors["heures_initiales"] = (
                "Les heures initiales ne peuvent pas être négatives."
            )

        if (
            self.heures_finales is not None
            and self.heures_finales < Decimal("0.00")
        ):
            errors["heures_finales"] = (
                "Les heures finales ne peuvent pas être négatives."
            )

        if (
            self.heures_initiales is not None
            and self.heures_finales is not None
            and self.heures_finales < self.heures_initiales
        ):
            errors["heures_finales"] = (
                "Les heures finales doivent être supérieures "
                "ou égales aux heures initiales."
            )

        # ----------------------------------------------------
        # CONSOMMATION
        # ----------------------------------------------------
        if (
            self.consommation_heure_litre is not None
            and self.consommation_heure_litre < Decimal("0.00")
        ):
            errors["consommation_heure_litre"] = (
                "La consommation ne peut pas être négative."
            )

        if errors:
            raise ValidationError(errors)

    @property
    def acces_actif(self):
        aujourd_hui = timezone.localdate()

        return (
            self.actif
            and self.date_debut <= aujourd_hui
            and self.date_fin >= aujourd_hui
        )

    @property
    def periode_terminee(self):
        return self.date_fin < timezone.localdate()

    @property
    def heures_travail(self):
        if (
            self.heures_initiales is None
            or self.heures_finales is None
        ):
            return Decimal("0.00")

        return max(
            Decimal("0.00"),
            self.heures_finales - self.heures_initiales,
        )

    @property
    def carburant_estime(self):
        if (
            self.heures_travail <= Decimal("0.00")
            or self.consommation_heure_litre is None
            or self.consommation_heure_litre <= Decimal("0.00")
        ):
            return Decimal("0.00")

        return (
            self.heures_travail
            * self.consommation_heure_litre
        ).quantize(Decimal("0.01"))

    @property
    def unite_travail(self):
        return "heures"

    @property
    def travail_total(self):
        return self.heures_travail


# ============================================================
# VÉHICULE / ENGIN AFFECTÉ AU PROJET
# ============================================================

class VehiculeProjet(models.Model):

    TYPE_VEHICULE_CHOICES = [
        (
            "ROUTIER",
            "Véhicule routier",
        ),
        (
            "ENGIN",
            "Engin de chantier",
        ),
    ]

    projet = models.ForeignKey(
        Projet,
        on_delete=models.PROTECT,
        related_name="vehicules_projet",
        verbose_name="Projet",
    )

    vehicule = models.CharField(
        max_length=30,
        verbose_name="Véhicule / Engin",
    )

    type_vehicule = models.CharField(
        max_length=20,
        choices=TYPE_VEHICULE_CHOICES,
        default="ROUTIER",
        verbose_name="Type",
    )

    chauffeur = models.ForeignKey(
        Personnel,
        on_delete=models.PROTECT,
        related_name="affectations_vehicules_projets",
        verbose_name="Conducteur / Chauffeur",
        null=True,
        blank=True,
    )

    date_debut = models.DateField(
        verbose_name="Début de l'affectation",
    )

    date_fin = models.DateField(
        verbose_name="Fin de l'affectation",
    )

    kilometrage_initial = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Kilométrage initial",
    )

    kilometrage_final = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Kilométrage final",
    )

    consommation_km_litre = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Consommation (km/L)",
    )

    heures_initiales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Heures initiales",
    )

    heures_finales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Heures finales",
    )

    consommation_heure_litre = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Consommation (L/h)",
    )

    actif = models.BooleanField(
        default=True,
        verbose_name="Affectation active",
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-date_debut",
            "-id",
        ]

        constraints = [
            models.UniqueConstraint(
                fields=[
                    "projet",
                    "vehicule",
                ],
                name="unique_vehicule_projet",
            ),
        ]

        verbose_name = "Véhicule / Engin affecté au projet"
        verbose_name_plural = "Véhicules / Engins affectés aux projets"

    def __str__(self):

        chauffeur = (
            str(self.chauffeur)
            if self.chauffeur_id
            else "Sans chauffeur"
        )

        return (
            f"{self.vehicule} - "
            f"{self.projet.titre} - "
            f"{chauffeur}"
        )

    def clean(self):

        errors = {}

        if (
            self.date_debut
            and self.date_fin
            and self.date_fin < self.date_debut
        ):
            errors["date_fin"] = (
                "La fin de l'affectation doit être "
                "postérieure ou égale au début."
            )

        if self.projet_id:

            projet = self.projet

            if (
                self.date_debut
                and self.date_debut < projet.date_debut
            ):
                errors["date_debut"] = (
                    "L'affectation du véhicule ne peut pas "
                    "commencer avant le début du projet."
                )

            if (
                self.date_fin
                and self.date_fin > projet.date_fin
            ):
                errors["date_fin"] = (
                    "L'affectation du véhicule ne peut pas "
                    "dépasser la date de fin du projet."
                )

        # ----------------------------------------------------
        # KILOMÉTRAGE
        # ----------------------------------------------------

        if self.kilometrage_initial < Decimal("0.00"):
            errors["kilometrage_initial"] = (
                "Le kilométrage initial ne peut pas être négatif."
            )

        if self.kilometrage_final < Decimal("0.00"):
            errors["kilometrage_final"] = (
                "Le kilométrage final ne peut pas être négatif."
            )

        if self.kilometrage_final < self.kilometrage_initial:
            errors["kilometrage_final"] = (
                "Le kilométrage final doit être supérieur "
                "ou égal au kilométrage initial."
            )

        # ----------------------------------------------------
        # HEURES
        # ----------------------------------------------------

        if self.heures_initiales < Decimal("0.00"):
            errors["heures_initiales"] = (
                "Les heures initiales ne peuvent pas être négatives."
            )

        if self.heures_finales < Decimal("0.00"):
            errors["heures_finales"] = (
                "Les heures finales ne peuvent pas être négatives."
            )

        if self.heures_finales < self.heures_initiales:
            errors["heures_finales"] = (
                "Les heures finales doivent être supérieures "
                "ou égales aux heures initiales."
            )

        if errors:
            raise ValidationError(errors)

    @property
    def acces_actif(self):

        if not self.actif:
            return False

        if not self.date_debut or not self.date_fin:
            return False

        aujourd_hui = timezone.localdate()

        return (
            self.date_debut
            <= aujourd_hui
            <= self.date_fin
        )

    @property
    def periode_terminee(self):

        if not self.date_fin:
            return False

        return timezone.localdate() > self.date_fin

    @property
    def kilometres_parcourus(self):

        if self.type_vehicule == "ENGIN":
            return Decimal("0.00")

        return max(
            Decimal("0.00"),
            self.kilometrage_final
            - self.kilometrage_initial,
        )

    @property
    def heures_travail(self):

        if self.type_vehicule != "ENGIN":
            return Decimal("0.00")

        return max(
            Decimal("0.00"),
            self.heures_finales
            - self.heures_initiales,
        )

    @property
    def carburant_estime(self):

        if self.type_vehicule == "ENGIN":

            if (
                not self.consommation_heure_litre
                or self.consommation_heure_litre
                <= Decimal("0.00")
            ):
                return Decimal("0.00")

            return (
                self.heures_travail
                * self.consommation_heure_litre
            ).quantize(
                Decimal("0.01")
            )

        if (
            not self.consommation_km_litre
            or self.consommation_km_litre
            <= Decimal("0.00")
        ):
            return Decimal("0.00")

        return (
            self.kilometres_parcourus
            / self.consommation_km_litre
        ).quantize(
            Decimal("0.01")
        )

    @property
    def unite_travail(self):

        if self.type_vehicule == "ENGIN":
            return "heures"

        return "km"

    @property
    def travail_total(self):

        if self.type_vehicule == "ENGIN":
            return self.heures_travail

        return self.kilometres_parcourus



# ============================================================
# MOUVEMENT DU VÉHICULE / ENGIN SUR LE PROJET
# ============================================================

class MouvementVehiculeProjet(models.Model):

    vehicule_projet = models.ForeignKey(
        "projet.VehiculeProjet",
        on_delete=models.PROTECT,
        related_name="mouvements",
        verbose_name="Véhicule / Engin",
    )

    date_mouvement = models.DateTimeField(
        default=timezone.now,
        verbose_name="Date du mouvement",
    )

    heure_depart = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Heure de départ",
    )

    heure_arrivee = models.TimeField(
        null=True,
        blank=True,
        verbose_name="Heure d'arrivée",
    )

    point_depart = models.ForeignKey(
        "projet.PointProjet",
        on_delete=models.PROTECT,
        related_name="mouvements_vehicules_depart",
        null=True,
        blank=True,
        verbose_name="Lieu de départ",
    )

    point_arrivee = models.ForeignKey(
        "projet.PointProjet",
        on_delete=models.PROTECT,
        related_name="mouvements_vehicules_arrivee",
        null=True,
        blank=True,
        verbose_name="Destination",
    )

    # --------------------------------------------------------
    # COMPTEUR KILOMÉTRIQUE : VÉHICULE ROUTIER
    # --------------------------------------------------------

    kilometrage_initial = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Kilométrage initial (km)",
    )

    kilometrage_final = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Kilométrage final (km)",
    )

    # --------------------------------------------------------
    # COMPTEUR HORAIRE : ENGIN DE CHANTIER
    # Le compteur final doit être inférieur ou égal à l'initial.
    # --------------------------------------------------------

    heures_initiales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Compteur initial",
    )

    heures_finales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Compteur final",
    )

    # --------------------------------------------------------
    # CARBURANT
    # --------------------------------------------------------

    carburant_litre = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Carburant consommé (litres)",
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    enregistre_par = models.ForeignKey(
        "users.AppUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mouvements_vehicules_enregistres",
        verbose_name="Enregistré par",
    )

    class Meta:
        ordering = ["-date_mouvement", "-id"]
        verbose_name = "Mouvement véhicule / engin"
        verbose_name_plural = "Mouvements véhicules / engins"

    def __str__(self):
        return (
            f"{self.vehicule_projet.vehicule} - "
            f"{self.date_mouvement:%d/%m/%Y}"
        )

    # --------------------------------------------------------
    # TYPE DE VÉHICULE
    # --------------------------------------------------------

    @property
    def type_vehicule(self):
        return self.vehicule_projet.type_vehicule

    # --------------------------------------------------------
    # DISTANCE PARCOURUE
    # --------------------------------------------------------

    @property
    def kilometres_parcourus(self):
        if self.type_vehicule == "ENGIN":
            return Decimal("0.00")

        return max(
            Decimal("0.00"),
            self.kilometrage_final - self.kilometrage_initial,
        )

    # --------------------------------------------------------
    # HEURES DE TRAVAIL DE L'ENGIN
    # --------------------------------------------------------

    @property
    def heures_travail(self):
        """
        Calcul : compteur horaire initial - compteur horaire final.
        Exemple : initial = 4, final = 2, résultat = 2 heures.
        """
        if self.type_vehicule != "ENGIN":
            return Decimal("0.00")

        return max(
            Decimal("0.00"),
            self.heures_initiales - self.heures_finales,
        )

    # --------------------------------------------------------
    # DURÉE ENTRE LE DÉPART ET L'ARRIVÉE
    # --------------------------------------------------------

    @property
    def duree_minutes(self):
        """Durée écoulée entre départ et arrivée, en minutes."""

        if self.heure_depart is None or self.heure_arrivee is None:
            return 0

        depart = (
            self.heure_depart.hour * 60
            + self.heure_depart.minute
            + self.heure_depart.second / 60
        )

        arrivee = (
            self.heure_arrivee.hour * 60
            + self.heure_arrivee.minute
            + self.heure_arrivee.second / 60
        )

        # Prise en compte d'une arrivée après minuit.
        if arrivee < depart:
            arrivee += 24 * 60

        return int(arrivee - depart)

    @property
    def duree_formatee(self):
        minutes = self.duree_minutes
        heures, reste = divmod(minutes, 60)

        return f"{heures} h {reste:02d} min"

    # --------------------------------------------------------
    # TRAVAIL TOTAL
    # --------------------------------------------------------

    @property
    def travail_total(self):
        """Heures moteur pour un engin, kilomètres pour un véhicule."""

        if self.type_vehicule == "ENGIN":
            return self.heures_travail

        return self.kilometres_parcourus

    @property
    def unite_travail(self):
        return (
            "heures moteur"
            if self.type_vehicule == "ENGIN"
            else "km"
        )

    # --------------------------------------------------------
    # VALIDATION DES DONNÉES
    # --------------------------------------------------------

    def clean(self):
        super().clean()

        erreurs = {}

        # Validation des kilomètres.
        if (
            self.kilometrage_initial is not None
            and self.kilometrage_initial < 0
        ):
            erreurs["kilometrage_initial"] = (
                "Le kilométrage initial ne peut pas être négatif."
            )

        if (
            self.kilometrage_final is not None
            and self.kilometrage_final < 0
        ):
            erreurs["kilometrage_final"] = (
                "Le kilométrage final ne peut pas être négatif."
            )

        if (
            self.kilometrage_initial is not None
            and self.kilometrage_final is not None
            and self.kilometrage_final < self.kilometrage_initial
        ):
            erreurs["kilometrage_final"] = (
                "Le kilométrage final doit être supérieur "
                "ou égal au kilométrage initial."
            )

        # Validation des compteurs horaires.
        if (
            self.heures_initiales is not None
            and self.heures_initiales < 0
        ):
            erreurs["heures_initiales"] = (
                "Le compteur horaire initial ne peut pas être négatif."
            )

        if (
            self.heures_finales is not None
            and self.heures_finales < 0
        ):
            erreurs["heures_finales"] = (
                "Le compteur horaire final ne peut pas être négatif."
            )

        # RÈGLE MÉTIER :
        # Le compteur final doit être inférieur ou égal à l'initial.
        if (
            self.heures_initiales is not None
            and self.heures_finales is not None
            and self.heures_finales > self.heures_initiales
        ):
            erreurs["heures_finales"] = (
                "Le compteur final doit être inférieur "
                "ou égal au compteur initial."
            )

        # Validation du carburant.
        if (
            self.carburant_litre is not None
            and self.carburant_litre < 0
        ):
            erreurs["carburant_litre"] = (
                "La quantité de carburant ne peut pas être négative."
            )

        if erreurs:
            raise ValidationError(erreurs)


# ============================================================
# MOUVEMENT DU PERSONNEL D'EXÉCUTION
# ============================================================
class MouvementPersonnelProjet(models.Model):
    personnel_execution = models.ForeignKey(
        "PersonnelExecutionProjet",
        on_delete=models.PROTECT,
        related_name="mouvements",
        verbose_name="Personnel",
    )

    date_mouvement = models.DateTimeField(
        default=timezone.now,
        verbose_name="Date du mouvement",
    )

    point = models.ForeignKey(
        PointProjet,
        on_delete=models.PROTECT,
        related_name="mouvements_personnel",
        null=True,
        blank=True,
        verbose_name="Point de chantier",
    )

    activite = models.CharField(
        max_length=255,
        verbose_name="Activité",
    )

    date_debut = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Début",
    )

    date_fin = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Fin",
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    enregistre_par = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mouvements_personnel_enregistres",
        verbose_name="Enregistré par",
    )

    class Meta:
        ordering = [
            "-date_mouvement",
            "-id",
        ]
        verbose_name = "Mouvement du personnel"
        verbose_name_plural = "Mouvements du personnel"

    def __str__(self):

        return (
            f"{self.personnel_execution.nom} - "
            f"{self.date_mouvement:%d/%m/%Y %H:%M}"
        )

    def clean(self):

        errors = {}

        if not self.personnel_execution_id:
            return

        personnel = self.personnel_execution

        if self.point_id:

            if self.point.projet_id != personnel.projet_id:
                errors["point"] = (
                    "Le point sélectionné n'appartient "
                    "pas au projet du personnel."
                )

        if self.date_mouvement:

            if (
                self.date_mouvement.date()
                < personnel.projet.date_debut
            ):
                errors["date_mouvement"] = (
                    "La date du mouvement est avant "
                    "le début du projet."
                )

            elif (
                self.date_mouvement.date()
                > personnel.projet.date_fin
            ):
                errors["date_mouvement"] = (
                    "La date du mouvement dépasse "
                    "la fin du projet."
                )

        if (
            self.date_debut
            and self.date_fin
            and self.date_fin < self.date_debut
        ):
            errors["date_fin"] = (
                "La fin doit être postérieure au début."
            )

        if errors:
            raise ValidationError(errors)


# ============================================================
# ÉQUIPAGE DU PROJET
# ============================================================
class EquipageProjet(models.Model):
    """
    Affectation d'un Chef d'équipe à un point de chantier.

    Le Chef d'équipe doit obligatoirement être une inscription
    PersonnelExecutionProjet avec type_class = CHEF_EQUIPE.
    """

    personnel_execution = models.ForeignKey(
        "PersonnelExecutionProjet",
        on_delete=models.PROTECT,
        related_name="equipages",
        verbose_name="Chef d'équipe",
    )

    lieu = models.ForeignKey(
        PointProjet,
        on_delete=models.PROTECT,
        related_name="equipages",
        verbose_name="Point de chantier",
    )

    montant = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Montant",
    )

    date_debut = models.DateTimeField(
        verbose_name="Date de début",
    )

    date_fin = models.DateTimeField(
        null=True,
        blank=True,
        verbose_name="Date de fin",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    enregistre_par = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipages_projet_enregistres",
        verbose_name="Enregistré par",
    )

    class Meta:
        ordering = [
            "-date_debut",
            "-id",
        ]
        verbose_name = "Équipage du projet"
        verbose_name_plural = "Équipages du projet"

    def __str__(self):

        return (
            f"{self.personnel_execution.nom} - "
            f"{self.lieu.nom}"
        )

    def clean(self):

        errors = {}

        # ----------------------------------------------------
        # CHEF D'ÉQUIPE
        # ----------------------------------------------------

        if self.personnel_execution_id:

            chef = self.personnel_execution

            if chef.type_class != "CHEF_EQUIPE":

                errors["personnel_execution"] = (
                    "La personne sélectionnée doit être enregistrée comme Chef d'équipe."
                )

            if self.lieu_id:

                if chef.projet_id != self.lieu.projet_id:

                    errors["personnel_execution"] = (
                        "Le Chef d'équipe et le point doivent appartenir au même projet."
                    )

        # ----------------------------------------------------
        # MONTANT
        # ----------------------------------------------------

        if (
            self.montant is not None
            and self.montant < Decimal("0.00")
        ):

            errors["montant"] = (
                "Le montant ne peut pas être négatif."
            )

        # ----------------------------------------------------
        # DATES
        # ----------------------------------------------------

        if (
            self.date_debut
            and self.date_fin
            and self.date_fin < self.date_debut
        ):

            errors["date_fin"] = (
                "La date de fin doit être "
                "postérieure ou égale au début."
            )

        if errors:
            raise ValidationError(errors)


# ============================================================
# AVANCE ÉQUIPE PROJET
# ============================================================
class AvanceEquipeProjet(models.Model):

    personnel_execution = models.ForeignKey(
        "PersonnelExecutionProjet",
        on_delete=models.PROTECT,
        related_name="avances",
        verbose_name="Travailleur",
    )

    montant = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Montant de l'avance",
    )

    date_avance = models.DateTimeField(
        default=timezone.now,
        verbose_name="Date de l'avance",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    enregistre_par = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="avances_equipe_enregistrees",
        verbose_name="Enregistré par",
    )

    class Meta:
        ordering = [
            "-date_avance",
            "-id",
        ]
        verbose_name = "Avance d'équipe"
        verbose_name_plural = "Avances d'équipe"

    def __str__(self):

        return (
            f"{self.personnel_execution.nom} - "
            f"{self.montant}"
        )

    def clean(self):

        errors = {}

        if (
            self.montant is not None
            and self.montant < Decimal("0.00")
        ):

            errors["montant"] = (
                "Le montant de l'avance ne peut pas être négatif."
            )

        if errors:
            raise ValidationError(errors)


# ============================================================
# MATÉRIAUX UTILISÉS PAR L'ÉQUIPE
# ============================================================

class EquipeMateriauProjet(models.Model):

    personnel_execution = models.ForeignKey(
        "PersonnelExecutionProjet",
        on_delete=models.PROTECT,
        related_name="materiaux_utilises",
        verbose_name="Travailleur",
    )

    point = models.ForeignKey(
        PointProjet,
        on_delete=models.PROTECT,
        related_name="materiaux_equipe",
        verbose_name="Point de chantier",
    )

    typemateriaux = models.ForeignKey(
        "materiaux.Materiaux",
        on_delete=models.PROTECT,
        related_name="equipes_projet",
        verbose_name="Type de matériau",
    )

    quantite = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Quantité",
    )

    unite = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Unité",
    )

    prix_unitaire = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Prix unitaire",
    )

    date_debut = models.DateTimeField(
        verbose_name="Date",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    enregistre_par = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="materiaux_equipe_enregistres",
        verbose_name="Enregistré par",
    )

    class Meta:
        ordering = [
            "-date_debut",
            "-id",
        ]
        verbose_name = "Matériau de l'équipe"
        verbose_name_plural = "Matériaux des équipes"

    def __str__(self):

        return (
            f"{self.typemateriaux} - "
            f"{self.quantite} - "
            f"{self.point.nom}"
        )

    def clean(self):

        errors = {}

        if (
            self.quantite is not None
            and self.quantite < Decimal("0.00")
        ):

            errors["quantite"] = (
                "La quantité ne peut pas être négative."
            )

        if (
            self.prix_unitaire is not None
            and self.prix_unitaire < Decimal("0.00")
        ):

            errors["prix_unitaire"] = (
                "Le prix unitaire ne peut pas être négatif."
            )

        if (
            self.personnel_execution_id
            and self.point_id
            and self.personnel_execution.projet_id
            != self.point.projet_id
        ):

            errors["point"] = (
                "Le point et le personnel doivent "
                "appartenir au même projet."
            )

        if errors:
            raise ValidationError(errors)

    @property
    def montant_total(self):

        return (
            self.quantite
            * self.prix_unitaire
        ).quantize(
            Decimal("0.01")
        )


# ============================================================
# VÉHICULES LOURDS / ENGINS DU PROJET
# ============================================================
class VehiculeLourdsProjet(models.Model):

    TYPE_ENGIN_CHOICES = [
        ("PELLE", "Pelle hydraulique"),
        ("BULLDOZER", "Bulldozer"),
        ("CHARGEUSE", "Chargeuse"),
        ("COMPACTEUR", "Compacteur"),
        ("GRUE", "Grue"),
        ("TRACTOPELLE", "Tractopelle"),
        ("NIVELEUSE", "Niveleuse"),
        ("AUTRE", "Autre"),
    ]

    projet = models.ForeignKey(
        Projet,
        on_delete=models.PROTECT,
        related_name="vehicules_lourds",
        verbose_name="Projet",
    )

    type_engin = models.CharField(
        max_length=30,
        choices=TYPE_ENGIN_CHOICES,
        null=True,
        blank=True,
        verbose_name="Type d'engin",
    )

    matricule = models.CharField(
        max_length=30,
        verbose_name="Numéro matricule",
    )

    conducteur = models.ForeignKey(
        "PersonnelExecutionProjet",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="engins_conduits",
        verbose_name="Conducteur",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        super().clean()

        if self.conducteur:
            if self.conducteur.projet_id != self.projet_id:
                raise ValidationError({
                    "conducteur": (
                        "Le conducteur doit appartenir au même projet "
                        "que l'engin."
                    )
                })

            if self.conducteur.type_class != "CHAUFFEUR_ENGIN":
                raise ValidationError({
                    "conducteur": (
                        "Le conducteur doit être enregistré comme "
                        "CHAUFFEUR_ENGIN."
                    )
                })

    def __str__(self):
        type_engin = self.get_type_engin_display() if self.type_engin else "Engin"
        return f"{type_engin} - {self.matricule}"
# ============================================================
# ACTIVITÉ TRANSPORT DU PROJET
# ============================================================

class ActiviteTransportProjet(models.Model):

    TYPE_TRANSPORT_CHOICES = [
        (
            "MATERIAUX",
            "Matériaux",
        ),
        (
            "MATERIEL",
            "Matériel",
        ),
        (
            "PERSONNEL",
            "Personnel",
        ),
        (
            "MATERIAUX_MATERIEL",
            "Matériaux + Matériel",
        ),
        (
            "AUTRE",
            "Autre",
        ),
    ]

    projet = models.ForeignKey(
        Projet,
        on_delete=models.PROTECT,
        related_name="activites_transport_projet",
        verbose_name="Projet",
    )

    vehicule = models.ForeignKey(
        "materiaux.Vehicule",
        on_delete=models.PROTECT,
        related_name="activites_transport_projet",
        verbose_name="Véhicule",
    )

    chauffeur = models.ForeignKey(
        Personnel,
        on_delete=models.PROTECT,
        related_name="activites_transport_projet",
        verbose_name="Chauffeur",
    )

    type_transport = models.CharField(
        max_length=30,
        choices=TYPE_TRANSPORT_CHOICES,
        default="MATERIAUX",
        verbose_name="Type de transport",
    )

    mission = models.CharField(
        max_length=255,
        verbose_name="Mission",
    )

    lieu_depart = models.CharField(
        max_length=255,
        verbose_name="Lieu de départ",
    )

    destination = models.CharField(
        max_length=255,
        verbose_name="Destination",
    )

    distance_km = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Distance (km)",
    )

    kilometrage_initial = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Kilométrage initial",
    )

    kilometrage_final = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Kilométrage final",
    )

    consommation_km_litre = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Consommation (km/L)",
    )

    quantite = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Quantité transportée",
    )

    unite = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Unité",
    )

    date_transport = models.DateField(
        default=timezone.localdate,
        verbose_name="Date du transport",
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation",
    )

    enregistre_par = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="activites_transport_projet_enregistrees",
        verbose_name="Enregistré par",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-date_transport",
            "-id",
        ]
        verbose_name = "Activité transport du projet"
        verbose_name_plural = "Activités transport du projet"

    def __str__(self):

        return (
            f"{self.date_transport} - "
            f"{self.vehicule} - "
            f"{self.destination}"
        )

    def clean(self):

        errors = {}

        if (
            self.distance_km is not None
            and self.distance_km < Decimal("0.00")
        ):

            errors["distance_km"] = (
                "La distance ne peut pas être négative."
            )

        if self.kilometrage_initial < Decimal("0.00"):

            errors["kilometrage_initial"] = (
                "Le kilométrage initial ne peut pas être négatif."
            )

        if self.kilometrage_final < Decimal("0.00"):

            errors["kilometrage_final"] = (
                "Le kilométrage final ne peut pas être négatif."
            )

        if self.kilometrage_final < self.kilometrage_initial:

            errors["kilometrage_final"] = (
                "Le kilométrage final doit être supérieur "
                "ou égal au kilométrage initial."
            )

        if (
            self.consommation_km_litre is not None
            and self.consommation_km_litre < Decimal("0.00")
        ):

            errors["consommation_km_litre"] = (
                "La consommation ne peut pas être négative."
            )

        if (
            self.quantite is not None
            and self.quantite < Decimal("0.00")
        ):

            errors["quantite"] = (
                "La quantité ne peut pas être négative."
            )

        if self.projet_id and self.date_transport:

            projet = self.projet

            if self.date_transport < projet.date_debut:

                errors["date_transport"] = (
                    "La date du transport ne peut pas "
                    "être avant le début du projet."
                )

            elif self.date_transport > projet.date_fin:

                errors["date_transport"] = (
                    "La date du transport ne peut pas "
                    "dépasser la fin du projet."
                )

        # ----------------------------------------------------
        # CHAUFFEUR
        # ----------------------------------------------------

        if self.chauffeur_id:

            chauffeur = self.chauffeur

            if chauffeur.typeTravail != "Construction":

                errors["chauffeur"] = (
                    "Le chauffeur doit appartenir "
                    "au personnel Construction."
                )

            if self.projet_id:

                affectation = (
                    EquipeProjet.objects
                    .filter(
                        projet_id=self.projet_id,
                        personnel_id=self.chauffeur_id,
                        fonction="CHAUFFEUR",
                        actif=True,
                    )
                    .exists()
                )

                if not affectation:

                    errors["chauffeur"] = (
                        "Ce personnel n'est pas affecté "
                        "comme chauffeur à ce projet."
                    )

        # ----------------------------------------------------
        # VÉHICULE
        # ----------------------------------------------------

        if self.projet_id and self.vehicule_id:

            vehicule = self.vehicule

            affectation = (
                VehiculeProjet.objects
                .filter(
                    projet_id=self.projet_id,
                    vehicule=str(vehicule),
                    actif=True,
                )
                .exists()
            )

            if not affectation:

                errors["vehicule"] = (
                    "Ce véhicule n'est pas actuellement "
                    "affecté à ce projet."
                )

        if errors:
            raise ValidationError(errors)

    @property
    def kilometres_parcourus(self):

        return max(
            Decimal("0.00"),
            self.kilometrage_final
            - self.kilometrage_initial,
        )

    @property
    def carburant_estime(self):

        if (
            not self.consommation_km_litre
            or self.consommation_km_litre
            <= Decimal("0.00")
        ):
            return Decimal("0.00")

        return (
            self.kilometres_parcourus
            / self.consommation_km_litre
        ).quantize(
            Decimal("0.01")
        )


# ============================================================
# RAPPORT ÉTAT DU VÉHICULE
# ============================================================

class RapportVehicule(models.Model):

    projet = models.ForeignKey(
        Projet,
        on_delete=models.PROTECT,
        related_name="rapports_vehicules",
        verbose_name="Projet",
    )

    vehicule = models.ForeignKey(
        "materiaux.Vehicule",
        on_delete=models.PROTECT,
        related_name="rapports_projets",
        verbose_name="Véhicule",
    )

    chauffeur = models.ForeignKey(
        Personnel,
        on_delete=models.PROTECT,
        related_name="rapports_vehicules",
        verbose_name="Chauffeur",
    )

    date_rapport = models.DateField(
        default=timezone.localdate,
        verbose_name="Date",
    )

    kilometrage = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Kilométrage",
    )

    etat = models.CharField(
        max_length=100,
        verbose_name="État",
    )

    description = models.TextField(
        blank=True,
        verbose_name="Description",
    )

    photo = models.ImageField(
        upload_to="projets/vehicules/",
        blank=True,
        null=True,
        verbose_name="Photo",
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "-date_rapport",
            "-id",
        ]
        verbose_name = "Rapport véhicule"
        verbose_name_plural = "Rapports véhicules"

    def __str__(self):

        vehicule = (
            self.vehicule
            if self.vehicule_id
            else "Véhicule non défini"
        )

        projet = (
            self.projet.titre
            if self.projet_id
            else "Projet non défini"
        )

        return (
            f"{vehicule} - "
            f"{self.date_rapport} - "
            f"{projet}"
        )

    def clean(self):

        errors = {}

        if (
            self.kilometrage is not None
            and self.kilometrage < Decimal("0.00")
        ):

            errors["kilometrage"] = (
                "Le kilométrage ne peut pas être négatif."
            )

        if self.projet_id and self.date_rapport:

            projet = self.projet

            if (
                projet.date_debut
                and self.date_rapport < projet.date_debut
            ):

                errors["date_rapport"] = (
                    "La date du rapport ne peut pas "
                    "être avant le début du projet."
                )

            elif (
                projet.date_fin
                and self.date_rapport > projet.date_fin
            ):

                errors["date_rapport"] = (
                    "La date du rapport ne peut pas "
                    "dépasser la fin du projet."
                )

        if self.chauffeur_id:

            chauffeur = self.chauffeur

            if chauffeur.typeTravail != "Construction":

                errors["chauffeur"] = (
                    "Le chauffeur doit appartenir "
                    "au personnel Construction."
                )

            if self.projet_id:

                affectation = (
                    EquipeProjet.objects
                    .filter(
                        projet_id=self.projet_id,
                        personnel_id=self.chauffeur_id,
                        fonction="CHAUFFEUR",
                        actif=True,
                    )
                    .exists()
                )

                if not affectation:

                    errors["chauffeur"] = (
                        "Ce personnel n'est pas affecté "
                        "comme chauffeur à ce projet."
                    )

        if self.projet_id and self.vehicule_id:

            vehicule = self.vehicule

            affectation = (
                VehiculeProjet.objects
                .filter(
                    projet_id=self.projet_id,
                    vehicule=str(vehicule),
                    actif=True,
                )
                .exists()
            )

            if not affectation:

                errors["vehicule"] = (
                    "Ce véhicule n'est pas actuellement "
                    "affecté à ce projet."
                )

        if errors:
            raise ValidationError(errors)