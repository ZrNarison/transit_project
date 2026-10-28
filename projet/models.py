from datetime import timedelta
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator, MinValueValidator
from django.db import models
from django.urls import path, reverse, reverse_lazy
from django.utils import timezone
from materiels.models import Materiels, Vehicule
# from .models import Materiaux, Vehicule
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
                    "La date de fin doit être postérieure ou égale à la date de début."
                )

        # ----------------------------------------------------
        # BUDGET
        # ----------------------------------------------------

        if self.budget_previsionnel is not None and self.budget_previsionnel < Decimal(
            "0.00"
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
            self.date_debut <= aujourd_hui <= self.date_fin
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
    # PÃ‰RIODE
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
    # MATÃ‰RIAU DU PROJET
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

        verbose_name = "Personnel d'exécution du projet"

        verbose_name_plural = "Personnels d'exécution des projets"

    # ============================================================
    # AFFICHAGE
    # ============================================================

    def __str__(self):

        if self.type_class == "MINIER":

            if self.materiau_projet_id:
                materiau = str(self.materiau_projet)
            else:
                materiau = "Sans matériau"

            return f"{self.nom} - " f"Minier - " f"{materiau}"

        if self.type_class == "CHEF_EQUIPE":

            if self.point_projet_id:
                point = str(self.point_projet)
            else:
                point = "Sans point"

            return f"{self.nom} - " f"Chef d'équipe - " f"{point}"

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
        quantite = self.quantite or Decimal("0.00")
        prix_unitaire = self.prix_unitaire or Decimal("0.00")

        return (quantite * prix_unitaire).quantize(Decimal("0.01"))
    
    # ============================================================
    # MONTANT TOTAL DU PAIEMENT
    # ============================================================

    @property
    def montant_total_paiement(self):

        if self.type_class == "MINIER":
            return self.montant_total_production

        return self.montant if self.montant is not None else Decimal("0.00")

    # ============================================================
    # ACCÃˆS ACTIF
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

            return self.date_production == aujourd_hui

        # --------------------------------------------------------
        # AUTRES TYPES
        # --------------------------------------------------------

        if not self.date_debut:
            return False

        if not self.date_fin:
            return aujourd_hui >= self.date_debut

        return self.date_debut <= aujourd_hui <= self.date_fin

    # ============================================================
    # PÃ‰RIODE TERMINÃ‰E
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

            return aujourd_hui > self.date_production

        # --------------------------------------------------------
        # AUTRES TYPES
        # --------------------------------------------------------

        if not self.date_fin:
            return False

        return aujourd_hui > self.date_fin

    # ============================================================
    # VALIDATION
    # ============================================================

    def clean(self):

        errors = {}

        # ========================================================
        # PROJET
        # ========================================================

        projet = self.projet if self.projet_id else None

        # ========================================================
        # VALIDATION DES DATES
        # ========================================================

        if self.date_debut and self.date_fin and self.date_fin < self.date_debut:
            errors["date_fin"] = (
                "La date de fin doit être postérieure ou égale à la date de début."
            )

        # ========================================================
        # LIMITES PAR RAPPORT AU PROJET
        # ========================================================

        if projet:

            if (
                self.date_debut
                and projet.date_debut
                and self.date_debut < projet.date_debut
            ):
                errors["date_debut"] = (
                    "La date de début du personnel ne peut pas être antérieure au début du projet."
                )

            if self.date_fin and projet.date_fin and self.date_fin > projet.date_fin:
                errors["date_fin"] = (
                    "La date de fin du personnel ne peut pas dépasser la date de fin du projet."
                )

        # ========================================================
        # MONTANT
        # ========================================================

        if self.montant is not None and self.montant < Decimal("0.00"):
            errors["montant"] = "Le montant ne peut pas être négatif."

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
                    "Ce type de personnel est externe et ne doit pas être lié à un personnel interne."
                )

            if not self.nom or not self.nom.strip():
                errors["nom"] = "Le nom est obligatoire pour ce type de personnel."

        else:

            # Pour un Ã©ventuel type interne.
            if not self.personnel_id:

                errors["personnel"] = "Un personnel interne doit être sélectionné."

        # ========================================================
        # CHEF D'EQUIPE
        # ========================================================

        if self.type_class == "CHEF_EQUIPE":

            if not self.point_projet_id:

                errors["point_projet"] = (
                    "Le point du projet est obligatoire pour un chef d'équipe."
                )

            if self.materiau_projet_id:

                errors["materiau_projet"] = (
                    "Un chef d'équipe ne peut pas être associé à un matériau."
                )

            if self.montant is None or self.montant <= Decimal("0.00"):

                errors["montant"] = (
                    "Le montant est obligatoire et doit Ãªtre supérieur à 0 pour un chef d'équipe."
                )

            if self.quantite and self.quantite > Decimal("0.00"):

                errors["quantite"] = "La quantité est réservée aux miniers."

            if self.prix_unitaire and self.prix_unitaire > Decimal("0.00"):

                errors["prix_unitaire"] = "Le prix unitaire est réservé aux miniers."

            if self.date_production:

                errors["date_production"] = (
                    "La date de production est réservée aux miniers."
                )

        # ========================================================
        # MINIER
        # ========================================================

        elif self.type_class == "MINIER":

            # ----------------------------------------------------
            # MATERIAU OBLIGATOIRE
            # ----------------------------------------------------

            if not self.materiau_projet_id:

                errors["materiau_projet"] = (
                    "Le matériau est obligatoire pour un minier."
                )

            # ----------------------------------------------------
            # PAS DE POINT
            # ----------------------------------------------------

            if self.point_projet_id:

                errors["point_projet"] = (
                    "Un minier ne peut pas être associé à un point du projet."
                )

            # ----------------------------------------------------
            # QUANTITÃ‰
            # ----------------------------------------------------

            if self.quantite is None:

                errors["quantite"] = "La quantité est obligatoire pour un minier."

            elif self.quantite <= Decimal("0.00"):

                errors["quantite"] = "La quantité doit être supérieure à 0."

            # ----------------------------------------------------
            # PRIX UNITAIRE
            # ----------------------------------------------------

            if self.prix_unitaire is None:

                errors["prix_unitaire"] = (
                    "Le prix unitaire est obligatoire pour un minier."
                )

            elif self.prix_unitaire <= Decimal("0.00"):

                errors["prix_unitaire"] = (
                    "Le prix unitaire doit être supérieur à 0."
                )

            # ----------------------------------------------------
            # DATE DE PRODUCTION
            # ----------------------------------------------------
            if not self.date_production:

                errors["date_production"] = (
                    "La date de production est obligatoire pour un minier."
                )

            # ----------------------------------------------------
            # DATE PAR RAPPORT AU PROJET
            # ----------------------------------------------------

            if projet and self.date_production:

                if projet.date_debut and self.date_production < projet.date_debut:

                    errors["date_production"] = (
                        "La date de production ne peut pas être antérieure au début du projet."
                    )

                if projet.date_fin and self.date_production > projet.date_fin:

                    errors["date_production"] = (
                        "La date de production ne peut pas dépasser la fin du projet."
                    )

            # ----------------------------------------------------
            # MONTANT AUTOMATIQUE
            # ----------------------------------------------------

            if self.montant and self.montant > Decimal("0.00"):

                errors["montant"] = (
                    "Pour un minier, le montant est calculé automatiquement avec la quantité et le prix unitaire."
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
                    "Ce type de personnel ne peut pas être associé à un point du projet."
                )

            if self.materiau_projet_id:

                errors["materiau_projet"] = (
                    "Ce type de personnel ne peut pas Ãªtre associé à un matériau."
                )

            if self.quantite and self.quantite > Decimal("0.00"):

                errors["quantite"] = (
                    "La quantité de production est réservée aux miniers."
                )

            if self.prix_unitaire and self.prix_unitaire > Decimal("0.00"):

                errors["prix_unitaire"] = "Le prix unitaire est réservé aux miniers."

            if self.date_production:

                errors["date_production"] = (
                    "La date de production est réservée aux miniers."
                )

        # ========================================================
        # VÃ‰RIFICATION MATÃ‰RIAU / PROJET
        # ========================================================
        #
        # IMPORTANT :
        # MateriauProjet NE posséde PAS de champ "actif".
        #
        # On vérifie uniquement que le matériau appartient
        # au même projet.
        #

        if self.materiau_projet_id and self.projet_id:

            if self.materiau_projet.projet_id != self.projet_id:

                errors["materiau_projet"] = (
                    "Le matériau sélectionné n'appartient pas à ce projet."
                )

        # ========================================================
        # VÃ‰RIFICATION POINT / PROJET
        # ========================================================
        if self.point_projet_id and self.projet_id:

            if self.point_projet.projet_id != self.projet_id:

                errors["point_projet"] = (
                    "Le point sélectionné n'appartient pas à ce projet."
                )

            elif not self.point_projet.actif:

                errors["point_projet"] = (
                    "Le point sélectionné n'est plus actif pour ce projet."
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
            "INGENIEUR","Ingénieur Responsable du Chantier",
        ),
        (
            "CHEF_CHANTIER","Chef de Chantier",
        ),
        (
            "CHEF_MAGASIN","Chef Magasinier",
        ),
        (
            "MAGASINIER","Magasinier",
        ),
        (
            "CHAUFFEUR","Chauffeur",
        ),
        (
            "OUVRIER","Ouvrier",
        ),
        (
            "CHEF_EQUIPE","Chef d'équipe",
        ),
        (
            "MINIER","Minier",
        ),
        (
            "AUTRE","Autre",
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
        verbose_name = "Equipe de projet"
        verbose_name_plural = "Equipe des projets"

    def __str__(self):

        if self.personnel_execution_id:
            personne = self.personnel_execution.nom

        elif self.personnel_id:
            personne = str(self.personnel)

        else:
            personne = "Personne non définie"

        return (
            f"{personne} - " f"{self.get_fonction_display()} - " f"{self.projet.titre}"
        )

    def clean(self):
        errors = {}

        # ----------------------------------------------------
        # UNE SEULE SOURCE DE PERSONNE
        # ----------------------------------------------------

        if not self.personnel_id and not self.personnel_execution_id:

            errors["personnel"] = (
                "Sélectionnez soit un personnel de l'entreprise, soit une personne inscrite pour l'exécution du projet."
            )

        if self.personnel_id and self.personnel_execution_id:

            errors["personnel"] = (
                "Une affectation ne peut pas avoir simultanément un personnel entreprise et un personnel d'exécution."
            )

        # ----------------------------------------------------
        # PERSONNEL ENTREPRISE
        # ----------------------------------------------------

        if self.personnel_id:

            personnel = self.personnel

            if personnel.typeTravail != "Construction":

                errors["personnel"] = (
                    "Le personnel affecté à un projet doit appartenir au personnel Construction."
                )

            # Les fonctions externes doivent utiliser
            # PersonnelExecutionProjet.
            if self.fonction in {
                "CHEF_EQUIPE",
                "MINIER",
            }:
                errors["personnel"] = (
                    "Pour cette fonction, utilisez l'inscription du Personnel d'exécution du projet."
                )

        # ----------------------------------------------------
        # PERSONNEL D'EXÃ‰CUTION
        # ----------------------------------------------------

        if self.personnel_execution_id:

            execution = self.personnel_execution

            if execution.projet_id != self.projet_id:

                errors["personnel_execution"] = (
                    "La personne inscrite doit appartenir au mÃªme projet."
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

            if type_attendu and execution.type_class != type_attendu:
                errors["personnel_execution"] = (
                    "La fonction de l'affectation ne correspond pas au type de l'inscription."
                )

        # ----------------------------------------------------
        # DATES
        # ----------------------------------------------------

        if self.date_debut and self.date_fin:

            if self.date_fin < self.date_debut:

                errors["date_fin"] = (
                    "La fin de l'affectation doit être posterieure ou egale au debut."
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
                    "L'affectation ne peut pas commencer avant le début du projet."
                )

            if self.date_fin and projet.date_fin and self.date_fin > projet.date_fin:
                errors["date_fin"] = (
                    "L'affectation ne peut pas dépasser la date de fin du projet."
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

        return self.date_debut <= aujourd_hui <= self.date_fin

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

    enregistre_par = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="points_enregistres",
        verbose_name="Enregistré par",
        null=True,
        blank=True,
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
        return f"{self.nom.upper()} - ({self.distance_km} km) : {self.localisation.upper()}"

    def clean(self):
        errors = {}

        if self.distance_km is not None and self.distance_km < Decimal("0.00"):
            errors["distance_km"] = "La distance ne peut pas Ãªtre négative."

        if errors:
            raise ValidationError(errors)


# =============================================================
# MATERIAU
# =============================================================
class MateriauProjet(models.Model):

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

    enregistre_par = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="materiaux_projet_enregistres",
        verbose_name="Enregistré par",
        null=True,
        blank=True,
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
        return f"{self.materiau} - " f"{self.projet.titre}"

    def clean(self):
        errors = {}

        if self.quantite_prevue is not None and self.quantite_prevue < Decimal("0.00"):
            errors["quantite_prevue"] = "La quantité prévue ne peut pas être négative."

        if errors:
            raise ValidationError(errors)


# ============================================================
# ACHATS DE MATÃ‰RIAUX DU PROJET
# ============================================================
class AchatMateriauProjet(models.Model):
    materiau_projet = models.ForeignKey(
        "MateriauProjet",
        on_delete=models.PROTECT,
        related_name="achats",
        verbose_name="Matériau prévu",
    )
    fournisseur = models.CharField(max_length=200, verbose_name="Fournisseur")

    date_achat = models.DateField(
        default=timezone.localdate, verbose_name="Date d'achat"
    )
    quantite_achetee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Quantité achetée",
    )
    prix_unitaire = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.00"))],
        default=Decimal("0.00"),
        verbose_name="Prix unitaire",
    )
    observation = models.TextField(blank=True)
    enregistre_par = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="achats_materiaux_projet",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_achat", "-id"]
        verbose_name = "Achat de matériau"
        verbose_name_plural = "Achats de matériaux"

    def __str__(self):
        return f"{self.materiau_projet.materiau} à {self.fournisseur}"

    @property
    def montant_total(self):
        return (self.quantite_achetee * self.prix_unitaire).quantize(Decimal("0.01"))

    def clean(self):
        if self.materiau_projet_id and self.date_achat:
            projet = self.materiau_projet.projet
            if not (projet.date_debut <= self.date_achat <= projet.date_fin):
                raise ValidationError(
                    {
                        "date_achat": "La date d'achat doit être comprise dans la période du projet."
                    }
                )


# ============================================================
# RECEPTION DE MATERIAUX AU DEPOT OU SUR UN POINT DU CHANTIER
# Le point indique le lieu. Aucun achat ni destination distincte.
# ============================================================
class ReceptionMateriauProjet(models.Model):
    materiau_projet = models.ForeignKey(
        "MateriauProjet",
        on_delete=models.PROTECT,
        related_name="receptions",
        verbose_name="Matériau",
    )

    date_reception = models.DateField(
        default=timezone.localdate,
        verbose_name="Date de réception",
    )

    quantite_recue = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Quantité reçue",
    )

    point = models.ForeignKey(
        "PointProjet",
        on_delete=models.PROTECT,
        related_name="receptions_materiaux_projet",
        null=True,
        blank=True,
        verbose_name="Point de réception / livraison",
    )

    piece_justificative = models.FileField(
        upload_to="materiaux/receptions/%Y/%m/",
        validators=[
            FileExtensionValidator(
                allowed_extensions=["pdf", "jpg", "jpeg", "png", "webp"]
            )
        ],
        blank=True,
        null=True,
        verbose_name="Pièce justificative",
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation",
    )

    enregistre_par = models.ForeignKey(
        "users.AppUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="receptions_materiaux_enregistrees",
        verbose_name="Enregistré par",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-date_reception", "-id"]
        verbose_name = "Réception de matériau"
        verbose_name_plural = "Réceptions de matériaux"

    def __str__(self):
        return f"{self.materiau_projet.materiau} — {self.quantite_recue}"

    def clean(self):
        errors = {}

        if self.materiau_projet_id and self.date_reception:
            projet = self.materiau_projet.projet

            date_debut = getattr(projet, "date_debut", None)
            date_fin = getattr(projet, "date_fin", None)

            if date_debut and self.date_reception < date_debut:
                errors["date_reception"] = (
                    "La date ne peut pas précéder le début du projet."
                )

            if date_fin and self.date_reception > date_fin:
                errors["date_reception"] = (
                    "La date ne peut pas dépasser la fin du projet."
                )

        if self.point_id and self.materiau_projet_id:
            if self.point.projet_id != self.materiau_projet.projet_id:
                errors["point"] = (
                    "Le point doit appartenir au même projet que le matériau."
                )

        if errors:
            raise ValidationError(errors)
# ============================================================
# DISTRIBUTION DU DEPOT VERS UNE EQUIPE
# ============================================================
class DistributionMateriauProjet(models.Model):
    materiau_projet = models.ForeignKey(
        "MateriauProjet",
        on_delete=models.PROTECT,
        related_name="distributions",
        verbose_name="Matériau",
    )

    vehicule = models.ForeignKey(
        "VehiculeProjet",
        on_delete=models.PROTECT,
        related_name="distributions_materiaux",
        null=True,
        blank=True,
        verbose_name="Véhicule / Engin",
        help_text="Facultatif : laisser vide si aucun véhicule n'est utilisé.",
    )

    point = models.ForeignKey(
        "PointProjet",
        on_delete=models.PROTECT,
        related_name="distributions_materiaux",
        verbose_name="Point de chantier",
    )

    date_distribution = models.DateField(
        default=timezone.localdate,
        verbose_name="Date de distribution",
    )

    quantite = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
        verbose_name="Quantité distribuée",
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation",
    )

    enregistre_par = models.ForeignKey(
        "users.AppUser",
        on_delete=models.PROTECT,
        related_name="distributions_materiaux_projet",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-date_distribution", "-id"]
        verbose_name = "Distribution de matériau"
        verbose_name_plural = "Distributions de matériaux"

    def __str__(self):
        return (
            f"{self.materiau_projet.materiau} â€” "
            f"{self.quantite} {self.materiau_projet.unite} â€” "
            f"{self.point}"
        )

    def clean(self):
        errors = {}

        if self.materiau_projet_id and self.point_id:
            if self.materiau_projet.projet_id != self.point.projet_id:
                errors["point"] = (
                    "Le point doit appartenir au même projet que le matériau."
                )

        if self.vehicule_id and self.materiau_projet_id:
            if self.vehicule.projet_id != self.materiau_projet.projet_id:
                errors["vehicule"] = (
                    "Le véhicule ou l'engin doit être affecté au même projet que le matériau."
                )

        if errors:
            raise ValidationError(errors)


# ============================================================
# CONSOMMATION DE MATERIAUX
# ============================================================
class ConsommationMateriauProjet(models.Model):
    distribution = models.ForeignKey(
        "DistributionMateriauProjet",
        on_delete=models.PROTECT,
        related_name="consommations",
        null=True,
        blank=True,
        verbose_name="Distribution du dépôt",
    )

    reception_directe = models.ForeignKey(
        "ReceptionMateriauProjet",
        on_delete=models.PROTECT,
        related_name="consommations_directes",
        null=True,
        blank=True,
        verbose_name="Réception directe",
    )

    date_consommation = models.DateField(
        default=timezone.localdate,
        verbose_name="Date de consommation",
    )

    quantite_utilisee = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Quantité utilisée",
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation",
    )

    enregistre_par = models.ForeignKey(
        "users.AppUser",
        on_delete=models.PROTECT,
        related_name="consommations_materiaux_projet",
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date_consommation", "-id"]
        verbose_name = "Consommation de matériau"
        verbose_name_plural = "Consommations de matériaux"

    def clean(self):
        super().clean()

        errors = {}

        # Une consommation ne peut pas provenir des deux sources.
        if self.distribution_id and self.reception_directe_id:
            errors["__all__"] = (
                "Choisissez une seule source : distribution ou réception directe."
            )

        # VÃ©rification de la distribution.
        if self.distribution_id:
            distribution = self.distribution

            if not distribution.materiau_projet_id:
                errors["__all__"] = (
                    "La distribution ne posséde pas de matériau associé."
                )

            if not distribution.point_id:
                errors["__all__"] = (
                    "La distribution ne posséde pas de point de stockage."
                )

        # Vérification de la réception directe.
        if self.reception_directe_id:
            reception = self.reception_directe

            if not reception.point_id:
                errors["__all__"] = (
                    "La réception directe ne posséde pas de point de stockage."
                )

        # Vérification de la quantité.
        if self.quantite_utilisee is not None and self.quantite_utilisee <= Decimal(
            "0"
        ):
            errors["quantite_utilisee"] = (
                "La quantité utilisée doit être supérieure à 0."
            )

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        if self.distribution_id:
            source = f"Distribution : {self.distribution}"
        elif self.reception_directe_id:
            source = f"Réception directe : {self.reception_directe}"
        else:
            source = "Source non définie"

        return (
            f"Consommation du {self.date_consommation} â€” "
            f"{self.quantite_utilisee} â€” {source}"
        )


# ============================================================
# RETOUR DE MATÃ‰RIAUX NON UTILISÃ‰S
# ============================================================
class RetourMateriauProjet(models.Model):
    distribution = models.ForeignKey(
        "DistributionMateriauProjet",
        on_delete=models.PROTECT,
        related_name="retours",
        null=True,
        blank=True,
        verbose_name="Distribution du dépôt",
    )

    reception_directe = models.ForeignKey(
        "ReceptionMateriauProjet",
        on_delete=models.PROTECT,
        related_name="retours_directs",
        null=True,
        blank=True,
        verbose_name="Réception directe",
    )

    date_retour = models.DateField(
        default=timezone.localdate,
        verbose_name="Date du retour",
    )

    quantite = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name="Quantité retournée",
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation",
    )

    enregistre_par = models.ForeignKey(
        "users.AppUser",
        on_delete=models.PROTECT,
        related_name="retours_materiaux_projet",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-date_retour", "-id"]
        verbose_name = "Retour de matériau"
        verbose_name_plural = "Retours de matériaux"

    def clean(self):
        errors = {}

        # Une distribution et une réception directe ne peuvent pas être renseignées simultanément.
        if self.distribution_id and self.reception_directe_id:
            errors["__all__"] = (
                "Sélectionnez une distribution ou une réception directe, mais pas les deux."
            )

        # Une réception directe doit obligatoirement être associée
        # Ã  un point du projet.
        if self.reception_directe_id and self.reception_directe.point_id is None:
            errors["__all__"] = "La réception sélectionnée n'a pas de point associé."

        if errors:
            raise ValidationError(errors)

    def __str__(self):
        if self.distribution_id:
            source = str(self.distribution)
        elif self.reception_directe_id:
            source = str(self.reception_directe)
        else:
            source = "Source non définie"

        return f"Retour du {self.date_retour} â€” " f"{self.quantite} â€” {source}"


# ============================================================
# RAPPORT DE L'INGENIEUR
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

            if self.avancement < Decimal("0.00") or self.avancement > Decimal("100.00"):
                errors["avancement"] = (
                    "L'avancement doit être compris entre 0 et 100 %."
                )

        if self.projet_id and self.date_rapport:

            projet = self.projet

            if self.date_rapport < projet.date_debut:

                errors["date_rapport"] = (
                    "La date du rapport ne peut pas être avant le début du projet."
                )

            elif self.date_rapport > projet.date_fin:

                errors["date_rapport"] = (
                    "La date du rapport ne peut pas dépasser la fin du projet."
                )

        if self.auteur_id:

            if self.auteur.typeTravail != "Construction":

                errors["auteur"] = (
                    "L'auteur doit appartenir au personnel Construction."
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

    date_debut = models.DateField(verbose_name="Date de début",    )

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

        if self.date_debut and self.date_fin and self.date_fin < self.date_debut:
            errors["date_fin"] = (
                "La date de fin doit Ãªtre postérieure ou égale à la date de début."
            )

        if self.projet_id:

            projet = self.projet

            if self.date_debut and self.date_debut < projet.date_debut:
                errors["date_debut"] = (
                    "La date de début du travail ne peut pas être avant le projet."
                )

            if self.date_fin and self.date_fin > projet.date_fin:
                errors["date_fin"] = (
                    "La date de fin du travail ne peut pas dépasser le projet."
                )

        if self.point_id and self.projet_id:

            if self.point.projet_id != self.projet_id:
                errors["point"] = (
                    "Le point sélectionné n'appartient pas à ce projet."
                )

        if self.auteur_id:

            if self.auteur.typeTravail != "Construction":
                errors["auteur"] = (
                    "Le chef de chantier doit appartenir au personnel Construction."
                )

        if errors:
            raise ValidationError(errors)


# ============================================================
# RAPPORT MATERIAUX
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
        return f"{self.materiau} - " f"{self.quantite} - " f"{self.projet.titre}"

    def clean(self):
        errors = {}

        if self.quantite is not None and self.quantite <= Decimal("0.00"):
            errors["quantite"] = "La quantitée doit être supérieure à 0."

        if self.projet_id and self.point_id:

            if self.point.projet_id != self.projet_id:
                errors["point"] = (
                    "Le point sélectionné n'appartient pas à ce projet."
                )

        if self.projet_id and self.date_ravitaillement:

            projet = self.projet

            if self.date_ravitaillement < projet.date_debut:
                errors["date_ravitaillement"] = (
                    "La date de ravitaillement ne peut pas Ãªtre avant le début du projet."
                )

            elif self.date_ravitaillement > projet.date_fin:
                errors["date_ravitaillement"] = (
                    "La date de ravitaillement ne peut pas dépasser la fin du projet."
                )

        if self.auteur_id:

            if self.auteur.typeTravail != "Construction":
                errors["auteur"] = (
                    "Le magasinier doit appartenir au personnel Construction."
                )

        if errors:
            raise ValidationError(errors)


# ============================================================
# ENGIN AFFECTER AU PROJET
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
        conducteur = str(self.conducteur) if self.conducteur_id else "Sans conducteur"

        return f"{self.engin} - " f"{self.projet.titre} - " f"{conducteur}"

    def clean(self):
        errors = {}

        # ----------------------------------------------------
        # DATES
        # ----------------------------------------------------
        if self.date_debut and self.date_fin:
            if self.date_fin < self.date_debut:
                errors["date_fin"] = (
                    "La date de fin doit être postérieure ou égale à la date de début."
                )

        # ----------------------------------------------------
        # PÃ‰RIODE DU PROJET
        # ----------------------------------------------------
        if self.projet_id:
            projet = self.projet

            if (
                self.date_debut
                and projet.date_debut
                and self.date_debut < projet.date_debut
            ):
                errors["date_debut"] = (
                    "L'affectation ne peut pas commencer avant le début du projet."
                )

            if self.date_fin and projet.date_fin and self.date_fin > projet.date_fin:
                errors["date_fin"] = (
                    "L'affectation ne peut pas dépasser la date de fin du projet."
                )

                # ----------------------------------------------------
        # COMPTEUR D'HEURES
        # Le compteur initial doit Ãªtre supérieur ou égal
        # au compteur final.
        # ----------------------------------------------------

        if self.heures_initiales is not None and self.heures_initiales < Decimal(
            "0.00"
        ):
            errors["heures_initiales"] = (
                "Les heures initiales ne peuvent pas être négatives."
            )

        if self.heures_finales is not None and self.heures_finales < Decimal("0.00"):
            errors["heures_finales"] = (
                "Les heures finales ne peuvent pas être négatives."
            )

        if (
            self.heures_initiales is not None
            and self.heures_finales is not None
            and self.heures_initiales < self.heures_finales
        ):
            errors["heures_finales"] = (
                "Le compteur initial doit être supérieur ou égal au compteur final."
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
        if self.heures_initiales is None or self.heures_finales is None:
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

        return (self.heures_travail * self.consommation_heure_litre).quantize(
            Decimal("0.01")
        )

    @property
    def unite_travail(self):
        return "heures"

    @property
    def travail_total(self):
        return self.heures_travail


# ============================================================
# VEHICULE / ENGIN AFFECTER AU PROJET
# ============================================================
class VehiculeProjet(models.Model):
    TYPE_VEHICULE_CHOICES = [
        ("ROUTIER", "Véhicule routier"),
        ("ENGIN", "Engin de chantier"),
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
        related_name="affectations_vehicules_galaxy",
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_debut", "-id"]
        constraints = [
            models.UniqueConstraint(
                fields=["projet", "vehicule"],
                name="unique_vehicule_projet_galaxy",
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
        return f"{self.vehicule} - {self.projet.titre} - {chauffeur}"

    def clean(self):
        super().clean()
        errors = {}

        if (
            self.date_debut
            and self.date_fin
            and self.date_fin < self.date_debut
        ):
            errors["date_fin"] = (
                "La fin de l'affectation doit être postérieure ou égale au début."
            )

        if self.projet_id:
            projet = self.projet

            if self.date_debut and self.date_debut < projet.date_debut:
                errors["date_debut"] = (
                    "L'affectation du véhicule ne peut pas commencer avant le début du projet."
                )

            if self.date_fin and self.date_fin > projet.date_fin:
                errors["date_fin"] = (
                    "L'affectation du véhicule ne peut pas dépasser la date de fin du projet."
                )

        if self.kilometrage_initial is not None:
            if self.kilometrage_initial < Decimal("0.00"):
                errors["kilometrage_initial"] = (
                    "Le kilométrage initial ne peut pas Ãªtre négatif."
                )

        if self.kilometrage_final is not None:
            if self.kilometrage_final < Decimal("0.00"):
                errors["kilometrage_final"] = (
                    "Le kilométrage final ne peut pas Ãªtre négatif."
                )

        if (
            self.kilometrage_initial is not None
            and self.kilometrage_final is not None
            and self.kilometrage_final < self.kilometrage_initial
        ):
            errors["kilometrage_final"] = (
                "Le kilométrage final doit être supérieur "
                "ou égal au kilométrage initial."
            )

        if self.heures_initiales is not None:
            if self.heures_initiales < Decimal("0.00"):
                errors["heures_initiales"] = (
                    "Les heures initiales ne peuvent pas être négatives."
                )

        if self.heures_finales is not None:
            if self.heures_finales < Decimal("0.00"):
                errors["heures_finales"] = (
                    "Les heures finales ne peuvent pas être négatives."
                )

        if (
            self.heures_initiales is not None
            and self.heures_finales is not None
            and self.heures_finales < self.heures_initiales
        ):
            errors["heures_finales"] = (
                "Les heures finales doivent être supérieures ou égales aux heures initiales."
            )

        if errors:
            raise ValidationError(errors)

    @property
    def acces_actif(self):
        if not self.actif or not self.date_debut or not self.date_fin:
            return False

        aujourd_hui = timezone.localdate()
        return self.date_debut <= aujourd_hui <= self.date_fin

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
            self.kilometrage_final - self.kilometrage_initial,
        )

    @property
    def heures_travail(self):
        if self.type_vehicule != "ENGIN":
            return Decimal("0.00")

        return max(
            Decimal("0.00"),
            self.heures_finales - self.heures_initiales,
        )

    @property
    def carburant_estime(self):
        if self.type_vehicule == "ENGIN":
            consommation = self.consommation_heure_litre
            if not consommation or consommation <= Decimal("0.00"):
                return Decimal("0.00")

            return (
                self.heures_travail * consommation
            ).quantize(Decimal("0.01"))

        consommation = self.consommation_km_litre
        if not consommation or consommation <= Decimal("0.00"):
            return Decimal("0.00")

        return (
            self.kilometres_parcourus / consommation
        ).quantize(Decimal("0.01"))

    @property
    def unite_travail(self):
        return "heures" if self.type_vehicule == "ENGIN" else "km"

    @property
    def travail_total(self):
        if self.type_vehicule == "ENGIN":
            return self.heures_travail
        return self.kilometres_parcourus

class MouvementVehiculeProjet(models.Model):
    """Rapport de déplacement d'un véhicule ou d'un engin de chantier."""

    vehicule_projet = models.ForeignKey(
        "projet.VehiculeProjet",
        on_delete=models.PROTECT,
        related_name="mouvements",
        null=True,
        blank=True,
        verbose_name="Véhicule routier",
    )

    engin_projet = models.ForeignKey(
        "projet.EnginProjet",
        on_delete=models.PROTECT,
        related_name="mouvements",
        null=True,
        blank=True,
        verbose_name="Engin de chantier",
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
    # COMPTEURS KILOMÃ‰TRIQUES : VÃ‰HICULE ROUTIER
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
    # COMPTEURS HORAIRES : ENGIN
    # Le compteur final doit être inférieur ou égal Ã  l'initial.
    # --------------------------------------------------------

    heures_initiales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Compteur horaire initial",
    )

    heures_finales = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Compteur horaire final",
    )

    # --------------------------------------------------------
    # CARBURANT ET OBSERVATIONS
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

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
        if self.engin_projet_id:
            materiel = str(self.engin_projet)
        elif self.vehicule_projet_id:
            materiel = str(self.vehicule_projet)
        else:
            materiel = "Matériel non défini"

        return f"{materiel} - {self.date_mouvement:%d/%m/%Y}"

    # --------------------------------------------------------
    # TYPE DE MATÃ‰RIEL
    # --------------------------------------------------------

    @property
    def type_vehicule(self):
        if self.engin_projet_id:
            return "ENGIN"

        if self.vehicule_projet_id:
            return self.vehicule_projet.type_vehicule

        return None

    @property
    def materiel(self):
        """Retourne le véhicule ou l'engin concerné."""
        return self.engin_projet or self.vehicule_projet

    @property
    def designation_materiel(self):
        if self.engin_projet_id:
            return str(self.engin_projet)

        if self.vehicule_projet_id:
            return str(self.vehicule_projet)

        return "Matériel non défini"

    # --------------------------------------------------------
    # DISTANCE PARCOURUE
    # --------------------------------------------------------

    @property
    def kilometres_parcourus(self):
        if self.engin_projet_id or self.type_vehicule == "ENGIN":
            return Decimal("0.00")

        initial = self.kilometrage_initial or Decimal("0.00")
        final = self.kilometrage_final or Decimal("0.00")

        return max(Decimal("0.00"), final - initial)

    # --------------------------------------------------------
    # HEURES MOTEUR
    # --------------------------------------------------------

    @property
    def heures_travail(self):
        if not self.engin_projet_id:
            return Decimal("0.00")

        initial = self.heures_initiales or Decimal("0.00")
        final = self.heures_finales or Decimal("0.00")

        return max(Decimal("0.00"), initial - final)

    # --------------------------------------------------------
    # DUREE DU DEPLACEMENT
    # --------------------------------------------------------

    @property
    def duree_minutes(self):
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

        # Arrivée le lendemain si elle est aprés minuit.
        if arrivee < depart:
            arrivee += 24 * 60

        return int(arrivee - depart)

    @property
    def duree_formatee(self):
        heures, minutes = divmod(self.duree_minutes, 60)
        return f"{heures} h {minutes:02d} min"

    # --------------------------------------------------------
    # TRAVAIL TOTAL
    # --------------------------------------------------------

    @property
    def travail_total(self):
        if self.engin_projet_id or self.type_vehicule == "ENGIN":
            return self.heures_travail

        return self.kilometres_parcourus

    @property
    def unite_travail(self):
        if self.engin_projet_id or self.type_vehicule == "ENGIN":
            return "heures moteur"

        return "km"

    # --------------------------------------------------------
    # VALIDATION
    # --------------------------------------------------------

    def clean(self):
        super().clean()

        erreurs = {}

        # Un seul matériel doit Ãªtre sélectionné.
        if bool(self.vehicule_projet_id) == bool(self.engin_projet_id):
            erreurs["vehicule_projet"] = (
                "Sélectionnez un véhicule routier ou un engin, mais pas les deux."
            )

        # Kilométrage.
        if self.kilometrage_initial is not None:
            if self.kilometrage_initial < 0:
                erreurs["kilometrage_initial"] = (
                    "Le kilometrage initial ne peut pas être négatif."
                )

        if self.kilometrage_final is not None:
            if self.kilometrage_final < 0:
                erreurs["kilometrage_final"] = (
                    "Le kilométrage final ne peut pas être négatif."
                )

        if (
            self.kilometrage_initial is not None
            and self.kilometrage_final is not None
            and self.kilometrage_final < self.kilometrage_initial
        ):
            erreurs["kilometrage_final"] = (
                "Le kilométrage final doit être supérieur ou égal "
                "au kilométrage initial."
            )

        # Compteurs horaires.
        if self.heures_initiales is not None:
            if self.heures_initiales < 0:
                erreurs["heures_initiales"] = (
                    "Le compteur horaire initial ne peut pas être négatif."
                )

        if self.heures_finales is not None:
            if self.heures_finales < 0:
                erreurs["heures_finales"] = (
                    "Le compteur horaire final ne peut pas être négatif."
                )

        if (
            self.heures_initiales is not None
            and self.heures_finales is not None
            and self.heures_finales > self.heures_initiales
        ):
            erreurs["heures_finales"] = (
                "Le compteur final doit être inférieur ou égal au compteur initial."
            )

        # Carburant.
        if self.carburant_litre is not None and self.carburant_litre < 0:
            erreurs["carburant_litre"] = (
                "La quantité de carburant ne peut pas être négative."
            )

        if erreurs:
            raise ValidationError(erreurs)





class ReparationVehicule(models.Model):
    """Réparation d'un véhicule ou engin affecté à un chantier GALAXY."""

    REPARATION = "REPARATION"
    CHANGEMENT = "CHANGEMENT"

    TYPE_REPARATION_CHOICES = [
        (REPARATION, "Réparation"),
        (CHANGEMENT, "Changement"),
    ]

    projet = models.ForeignKey(
        "projet.Projet",
        on_delete=models.PROTECT,
        related_name="reparations_vehicules_galaxy",
        verbose_name="Projet",
    )

    date_reparation = models.DateField(
        verbose_name="Date de réparation",
    )

    vehicule = models.ForeignKey(
        "projet.VehiculeProjet",
        on_delete=models.PROTECT,
        related_name="reparations",
        verbose_name="Véhicule / Engin du chantier",
    )

    chauffeur = models.CharField(
        max_length=150,
        blank=True,
        verbose_name="Chauffeur (texte historique)",
    )

    chauffeur_personnel = models.ForeignKey(
        "personnel.Personnel",
        on_delete=models.PROTECT,
        related_name="reparations_vehicules_galaxy",
        null=True,
        blank=True,
        verbose_name="Chauffeur GALAXY",
    )

    designation = models.CharField(
        max_length=255,
        verbose_name="Désignation",
    )

    type_reparation = models.CharField(
        max_length=20,
        choices=TYPE_REPARATION_CHOICES,
        default=REPARATION,
        verbose_name="Type",
    )

    garage = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Garage",
    )

    quantite = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("1.00"),
        verbose_name="Quantité",
    )

    unite = models.CharField(
        max_length=50,
        blank=True,
        verbose_name="Unité",
    )

    prix_unitaire = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Prix unitaire",
    )

    montant_main_oeuvre = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Main-d'Oeuvre",
    )

    total = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        default=Decimal("0.00"),
        editable=False,
        verbose_name="Total de la réparation",
    )

    enregistre_par = models.ForeignKey(
        "users.AppUser",
        on_delete=models.PROTECT,
        related_name="reparations_vehicules_enregistrees_galaxy",
        null=True,
        blank=True,
        verbose_name="Enregistré par",
    )

    photo_piece_remplacee = models.ImageField(
        upload_to="projet/reparations/pieces_remplacees/",
        blank=True,
        null=True,
        verbose_name="Photo de la pièce remplacée",
    )

    photo_piece_remplacante = models.ImageField(
        upload_to="projet/reparations/pieces_remplacantes/",
        blank=True,
        null=True,
        verbose_name="Photo de la pièce de remplacement",
    )

    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_reparation", "-id"]
        verbose_name = "Réparation de véhicule de chantier"
        verbose_name_plural = "Réparations des véhicules de chantier"

    @property
    def montant_piece(self):
        return (
            (self.quantite or Decimal("0.00"))
            * (self.prix_unitaire or Decimal("0.00"))
        )

    @property
    def montant_total_calcule(self):
        return self.montant_piece + (
            self.montant_main_oeuvre or Decimal("0.00")
        )

    @property
    def montant_total(self):
        return self.montant_total_calcule

    def clean(self):
        super().clean()
        errors = {}

        if self.quantite is not None and self.quantite <= 0:
            errors["quantite"] = (
                "La quantité doit être supérieure à 0."
            )

        if self.prix_unitaire is not None and self.prix_unitaire < 0:
            errors["prix_unitaire"] = (
                "Le prix unitaire ne peut pas être négatif."
            )

        if (
            self.montant_main_oeuvre is not None
            and self.montant_main_oeuvre < 0
        ):
            errors["montant_main_oeuvre"] = (
                "La main-d'oeuvre ne peut pas être négative."
            )

        if self.projet_id and self.vehicule_id:
            if self.vehicule.projet_id != self.projet_id:
                errors["vehicule"] = (
                    "Le véhicule doit être affecté au projet sélectionné."
                )

        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        self.full_clean()
        self.total = self.montant_total_calcule
        return super().save(*args, **kwargs)

    def __str__(self):
        return (
            f"{self.designation} - {self.projet} - "
            f"{self.date_reparation}"
        )


# ============================================================
# MOUVEMENT DU PERSONNEL D'EXÃ‰CUTION
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
            f"{self.personnel_execution.nom} - " f"{self.date_mouvement:%d/%m/%Y %H:%M}"
        )

    def clean(self):

        errors = {}

        if not self.personnel_execution_id:
            return

        personnel = self.personnel_execution

        if self.point_id:

            if self.point.projet_id != personnel.projet_id:
                errors["point"] = (
                    "Le point sélectionné n'appartient pas au projet du personnel."
                )

        if self.date_mouvement:

            if self.date_mouvement.date() < personnel.projet.date_debut:
                errors["date_mouvement"] = (
                    "La date du mouvement est avant le début du projet."
                )

            elif self.date_mouvement.date() > personnel.projet.date_fin:
                errors["date_mouvement"] = (
                    "La date du mouvement dépasse la fin du projet."
                )

        if self.date_debut and self.date_fin and self.date_fin < self.date_debut:
            errors["date_fin"] = "La fin doit être postérieure au début."

        if errors:
            raise ValidationError(errors)


# ============================================================
# Ã‰QUIPAGE DU PROJET
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
        verbose_name = "équipage du projet"
        verbose_name_plural = "équipages du projet"

    def __str__(self):

        return f"{self.personnel_execution.nom} - " f"{self.lieu.nom}"

    def clean(self):

        errors = {}

        # ----------------------------------------------------
        # CHEF D'Ã‰QUIPE
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

        if self.montant is not None and self.montant < Decimal("0.00"):

            errors["montant"] = "Le montant ne peut pas Ãªtre négatif."

        # ----------------------------------------------------
        # DATES
        # ----------------------------------------------------

        if self.date_debut and self.date_fin and self.date_fin < self.date_debut:

            errors["date_fin"] = (
                "La date de fin doit être postérieure ou égale au début."
            )

        if errors:
            raise ValidationError(errors)


# ============================================================
# AVANCE Ã‰QUIPE PROJET
# ============================================================
class AvanceEquipeProjet(models.Model):

    equipe_execution = models.ForeignKey(
        "projet.EquipeProjet",
        on_delete=models.PROTECT,
        related_name="avances_equipe",
        null=True,
        blank=True,
        verbose_name="Equipe d'exécution",
    )

    miniers_execution = models.ForeignKey(
        "projet.EquipeProjet",
        on_delete=models.PROTECT,
        related_name="avances_miniers",
        null=True,
        blank=True,
        verbose_name="Equipe de miniers",
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
        "users.AppUser",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="avances_equipe_enregistrees",
        verbose_name="Enregistré par",
    )

    class Meta:
        ordering = ["-date_avance", "-id"]
        verbose_name = "Avance d'équipe"
        verbose_name_plural = "Avances d'équipe"

    def __str__(self):
        equipe = self.equipe_execution or self.miniers_execution

        if equipe:
            return f"Avance - {equipe} - {self.montant}"

        return f"Avance d'équipe - {self.montant}"

    def clean(self):
        super().clean()
        errors = {}

        if self.montant is not None and self.montant < Decimal("0.00"):
            errors["montant"] = "Le montant de l'avance ne peut pas être négatif."

        if bool(self.equipe_execution_id) == bool(self.miniers_execution_id):
            message = (
                "Sélectionnez une seule équipe : équipe d'exécution "
                "ou équipe de miniers."
            )
            errors["equipe_execution"] = message
            errors["miniers_execution"] = message

        if errors:
            raise ValidationError(errors)


# ============================================================
# MATERIAUX UTILISEES PAR L'EQUIPE
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

        return f"{self.typemateriaux} - " f"{self.quantite} - " f"{self.point.nom}"

    def clean(self):

        errors = {}

        if self.quantite is not None and self.quantite < Decimal("0.00"):

            errors["quantite"] = "La quantité ne peut pas être négative."

        if self.prix_unitaire is not None and self.prix_unitaire < Decimal("0.00"):

            errors["prix_unitaire"] = "Le prix unitaire ne peut pas être négatif."

        if (
            self.personnel_execution_id
            and self.point_id
            and self.personnel_execution.projet_id != self.point.projet_id
        ):

            errors["point"] = (
                "Le point et le personnel doivent appartenir au même projet."
            )

        if errors:
            raise ValidationError(errors)

    @property
    def montant_total(self):

        return (self.quantite * self.prix_unitaire).quantize(Decimal("0.01"))


# ============================================================
# VÃ‰HICULES LOURDS / ENGINS DU PROJET
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
                raise ValidationError(
                    {
                        "conducteur": (
                            "Le conducteur doit appartenir au même projet que l'engin."
                        )
                    }
                )

            if self.conducteur.type_class != "CHAUFFEUR_ENGIN":
                raise ValidationError(
                    {
                        "conducteur": (
                            "Le conducteur doit Ãªtre enregistré comme CHAUFFEUR_ENGIN."
                        )
                    }
                )

    def __str__(self):
        type_engin = self.get_type_engin_display() if self.type_engin else "Engin"
        return f"{type_engin} - {self.matricule}"


# ============================================================
# ACTIVITÃ‰ TRANSPORT DU PROJET
# ============================================================
class ActiviteTransportProjet(models.Model):

    TYPE_TRANSPORT_CHOICES = [
        ("MATERIAUX","Matériaux",),
        ("MATERIEL","Matériel",),
        ("PERSONNEL","Personnel",),
        ("MATERIAUX_MATERIEL","Matériaux + Matériel",),
        ("AUTRE","Autre",),
    ]

    projet = models.ForeignKey(
        Projet,
        on_delete=models.PROTECT,
        related_name="activites_transport_projet",
        verbose_name="Projet",
    )

    vehicule = models.ForeignKey(
        "materiels.Vehicule",
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

        return f"{self.date_transport} - " f"{self.vehicule} - " f"{self.destination}"

    def clean(self):

        errors = {}

        if self.distance_km is not None and self.distance_km < Decimal("0.00"):

            errors["distance_km"] = "La distance ne peut pas être négative."

        if self.kilometrage_initial < Decimal("0.00"):

            errors["kilometrage_initial"] = (
                "Le kilométrage initial ne peut pas Ãªtre négatif."
            )

        if self.kilometrage_final < Decimal("0.00"):

            errors["kilometrage_final"] = (
                "Le kilométrage final ne peut pas Ãªtre négatif."
            )

        if self.kilometrage_final < self.kilometrage_initial:

            errors["kilometrage_final"] = (
                "Le kilométrage final doit Ãªtre supérieur "
                "ou égal au kilométrage initial."
            )

        if (
            self.consommation_km_litre is not None
            and self.consommation_km_litre < Decimal("0.00")
        ):

            errors["consommation_km_litre"] = (
                "La consommation ne peut pas être négative."
            )

        if self.quantite is not None and self.quantite < Decimal("0.00"):

            errors["quantite"] = "La quantité ne peut pas Ãªtre négative."

        if self.projet_id and self.date_transport:

            projet = self.projet

            if self.date_transport < projet.date_debut:

                errors["date_transport"] = (
                    "La date du transport ne peut pas être avant le début du projet."
                )

            elif self.date_transport > projet.date_fin:

                errors["date_transport"] = (
                    "La date du transport ne peut pas dépasser la fin du projet."
                )

        # ----------------------------------------------------
        # CHAUFFEUR
        # ----------------------------------------------------

        if self.chauffeur_id:

            chauffeur = self.chauffeur

            if chauffeur.typeTravail != "Construction":

                errors["chauffeur"] = (
                    "Le chauffeur doit appartenir au personnel Construction."
                )

            if self.projet_id:

                affectation = EquipeProjet.objects.filter(
                    projet_id=self.projet_id,
                    personnel_id=self.chauffeur_id,
                    fonction="CHAUFFEUR",
                    actif=True,
                ).exists()

                if not affectation:

                    errors["chauffeur"] = (
                        "Ce personnel n'est pas affecté comme chauffeur à ce projet."
                    )

        # ----------------------------------------------------
        # VÃ‰HICULE
        # ----------------------------------------------------

        if self.projet_id and self.vehicule_id:

            vehicule = self.vehicule

            affectation = VehiculeProjet.objects.filter(
                projet_id=self.projet_id,
                vehicule=str(vehicule),
                actif=True,
            ).exists()

            if not affectation:

                errors["vehicule"] = (
                    "Ce véhicule n'est pas actuellement affecté à ce projet."
                )

        if errors:
            raise ValidationError(errors)

    @property
    def kilometres_parcourus(self):

        return max(
            Decimal("0.00"),
            self.kilometrage_final - self.kilometrage_initial,
        )

    @property
    def carburant_estime(self):

        if not self.consommation_km_litre or self.consommation_km_litre <= Decimal(
            "0.00"
        ):
            return Decimal("0.00")

        return (self.kilometres_parcourus / self.consommation_km_litre).quantize(
            Decimal("0.01")
        )


# ============================================================
# RAPPORT ETAT DU VEHICULE
# ============================================================
class RapportVehicule(models.Model):

    projet = models.ForeignKey(
        Projet,
        on_delete=models.PROTECT,
        related_name="rapports_vehicules",
        verbose_name="Projet",
    )

    vehicule = models.ForeignKey(
        "materiels.Vehicule",
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
        verbose_name="Etat",
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

        vehicule = self.vehicule if self.vehicule_id else "Véhicule non défini"

        projet = self.projet.titre if self.projet_id else "Projet non défini"

        return f"{vehicule} - " f"{self.date_rapport} - " f"{projet}"

    def clean(self):

        errors = {}

        if self.kilometrage is not None and self.kilometrage < Decimal("0.00"):

            errors["kilometrage"] = "Le kilométrage ne peut pas être négatif."

        if self.projet_id and self.date_rapport:

            projet = self.projet

            if projet.date_debut and self.date_rapport < projet.date_debut:

                errors["date_rapport"] = (
                    "La date du rapport ne peut pas êre avant le début du projet."
                )

            elif projet.date_fin and self.date_rapport > projet.date_fin:

                errors["date_rapport"] = (
                    "La date du rapport ne peut pas dépasser la fin du projet."
                )

        if self.chauffeur_id:

            chauffeur = self.chauffeur

            if chauffeur.typeTravail != "Construction":

                errors["chauffeur"] = (
                    "Le chauffeur doit appartenir au personnel Construction."
                )

            if self.projet_id:

                affectation = EquipeProjet.objects.filter(
                    projet_id=self.projet_id,
                    personnel_id=self.chauffeur_id,
                    fonction="CHAUFFEUR",
                    actif=True,
                ).exists()

                if not affectation:

                    errors["chauffeur"] = (
                        "Ce personnel n'est pas affecté comme chauffeur à ce projet."
                    )

        if self.projet_id and self.vehicule_id:

            vehicule = self.vehicule

            affectation = VehiculeProjet.objects.filter(
                projet_id=self.projet_id,
                vehicule=str(vehicule),
                actif=True,
            ).exists()

            if not affectation:

                errors["vehicule"] = (
                    "Ce véhicule n'est pas actuellement affecté à ce projet."
                )

        if errors:
            raise ValidationError(errors)


# ============================================================
# MOUVEMENTS UNIFIES DES MATERIAUX D'UN PROJET GALAXY
# ============================================================
class MouvementMateriauProjet(models.Model):

    class TypeMouvement(models.TextChoices):
        ENTREE = "ENTREE", "Entrée"
        SORTIE = "SORTIE", "Sortie"
        RETOUR = "RETOUR", "Retour"

    materiau_projet = models.ForeignKey(
        "MateriauProjet",
        on_delete=models.PROTECT,
        related_name="mouvements_unifies",
        verbose_name="Matériau",
    )

    vehicule_transport = models.ForeignKey(
        "VehiculeProjet",
        on_delete=models.PROTECT,
        related_name="mouvements_materiaux",
        null=True,
        blank=True,
        verbose_name="Véhicule / Engin de transport",
    )

    type_mouvement = models.CharField(
        max_length=10,
        choices=TypeMouvement.choices,
        verbose_name="Type de mouvement",
    )

    point_depart = models.ForeignKey(
        "PointProjet",
        on_delete=models.PROTECT,
        related_name="mouvements_materiaux_depart",
        null=True,
        blank=True,
        verbose_name="Point d'origine",
    )

    point_arrivee = models.ForeignKey(
        "PointProjet",
        on_delete=models.PROTECT,
        related_name="mouvements_materiaux_arrivee",
        null=True,
        blank=True,
        verbose_name="Point de destination",
    )

    date_mouvement = models.DateField(
        default=timezone.localdate,
        verbose_name="Date du mouvement",
    )

    quantite = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
        verbose_name="Quantité",
    )

    # Prix obligatoire uniquement pour une entrée.
    # Pour une sortie ou un retour, la valeur est NULL.
    prix_unitaire = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[
            MinValueValidator(Decimal("0.01")),
        ],
        null=True,
        blank=True,
        verbose_name="Prix unitaire",
        help_text="Renseigner uniquement pour une entrée.",
    )

    observation = models.TextField(
        blank=True,
        verbose_name="Observation",
    )

    enregistre_par = models.ForeignKey(
        "users.AppUser",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="mouvements_materiaux_projet",
        verbose_name="Enregistré par",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    class Meta:
        ordering = ["-date_mouvement", "-id"]
        verbose_name = "Mouvement de matériau"
        verbose_name_plural = "Mouvements des matériaux"

    def __str__(self):
        return (
            f"{self.get_type_mouvement_display()} â€” "
            f"{self.materiau_projet.materiau} é” "
            f"{self.quantite} "
            f"{self.materiau_projet.unite}"
        )

    @property
    def montant(self):
        """
        Montant direct du mouvement.
        Seules les entrées possédent un prix unitaire enregistré.
        La valorisation des sorties et retours utilise le prix
        moyen calculé dans le tableau de bord.
        """
        quantite = self.quantite or Decimal("0.00")
        prix = self.prix_unitaire or Decimal("0.00")

        return quantite * prix

    def clean(self):
        super().clean()

        errors = {}

        # --------------------------------------------------
        # 1. VERIFICATION DU MATERIAU
        # --------------------------------------------------
        if not self.materiau_projet_id:
            errors["materiau_projet"] = "Sélectionnez un matériau du projet."

        # --------------------------------------------------
        # 2. VERIFICATION DE LA QUANTITE
        # --------------------------------------------------
        if self.quantite is not None and self.quantite <= Decimal("0.00"):
            errors["quantite"] = "La quantité doit être supérieure à 0."

        # --------------------------------------------------
        # 3. PRIX UNITAIRE : ENTREE UNIQUEMENT
        # --------------------------------------------------
        if self.type_mouvement == self.TypeMouvement.ENTREE:
            if self.prix_unitaire is None or self.prix_unitaire <= Decimal("0.00"):
                errors["prix_unitaire"] = (
                    "Le prix unitaire est obligatoire pour une entrée."
                )
        elif self.type_mouvement in (
            self.TypeMouvement.SORTIE,
            self.TypeMouvement.RETOUR,
        ):
            # Aucune saisie de prix pour les sorties et les retours.
            self.prix_unitaire = None

        # --------------------------------------------------
        # 4. VERIFICATION DU PROJET ET DES POINTS
        # --------------------------------------------------
        projet_id = None

        if self.materiau_projet_id:
            projet_id = self.materiau_projet.projet_id

            if self.point_depart_id:
                if self.point_depart.projet_id != projet_id:
                    errors["point_depart"] = (
                        "Le point d'origine doit appartenir au même projet que le matériau."
                    )

            if self.point_arrivee_id:
                if self.point_arrivee.projet_id != projet_id:
                    errors["point_arrivee"] = (
                        "Le point de destination doit appartenir au même projet que le matériau."
                    )

        # --------------------------------------------------
        # 5. VERIFICATION DU VEHICULE
        # --------------------------------------------------
        if self.vehicule_transport_id and projet_id is not None:
            if self.vehicule_transport.projet_id != projet_id:
                errors["vehicule_transport"] = (
                    "Le véhicule ou l'engin doit être affecté au même projet que le matériau."
                )

        # --------------------------------------------------
        # 6. REGLES PROPRES A CHAQUE MOUVEMENT
        # --------------------------------------------------
        if self.type_mouvement == self.TypeMouvement.ENTREE:

            if self.point_depart_id:
                errors["point_depart"] = (
                    "Pour une entrée, laissez le point d'origine vide."
                )

            if not self.point_arrivee_id:
                errors["point_arrivee"] = "Indiquez le point qui reçoit le matériau."

        elif self.type_mouvement == self.TypeMouvement.SORTIE:

            if not self.point_depart_id:
                errors["point_depart"] = "Indiquez le point d'où sort le matériau."

            if not self.point_arrivee_id:
                errors["point_arrivee"] = (
                    "Indiquez le point de destination du matériau."
                )

            if (
                self.point_depart_id
                and self.point_arrivee_id
                and self.point_depart_id == self.point_arrivee_id
            ):
                errors["point_arrivee"] = (
                    "L'origine et la destination doivent être différentes."
                )

        elif self.type_mouvement == self.TypeMouvement.RETOUR:

            if not self.point_depart_id:
                errors["point_depart"] = "Indiquez le point d'où revient le matériau."

            if not self.point_arrivee_id:
                errors["point_arrivee"] = "Indiquez le point qui reçoit le retour."

            if (
                self.point_depart_id
                and self.point_arrivee_id
                and self.point_depart_id == self.point_arrivee_id
            ):
                errors["point_arrivee"] = (
                    "L'origine et la destination doivent être différentes."
                )

        elif self.type_mouvement:
            errors["type_mouvement"] = "Le type de mouvement sélectionné est invalide."

        if errors:
            raise ValidationError(errors)
