from decimal import Decimal

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


# ============================================================
# EQUIPE DU PROJET
# ============================================================

class EquipeProjet(models.Model):
    """
    Personnel Construction affecté à un projet.

    Cette table représente l'équipe générale du projet.
    """

    FONCTION_CHOICES = [
        ("INGENIEUR","Ingénieur Responsable du Chantier",),
        ("CHEF_CHANTIER","Chef de Chantier",),
        ("CHEF_MAGASIN","Chef Magasinier",),
        ("MAGASINIER","Magasinier",),
        ("CHAUFFEUR","Chauffeur",),
        ("OUVRIER","Ouvrier",),
        ("AUTRE","Autre",),
    ]

    projet = models.ForeignKey(
        Projet,
        on_delete=models.PROTECT,
        related_name="equipe",
        verbose_name="Projet",
    )

    personnel = models.ForeignKey(
        Personnel,
        on_delete=models.PROTECT,
        related_name="affectations_projets",
        verbose_name="Personnel",
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
            "personnel__nom",
        ]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "projet",
                    "personnel",
                ],
                name="unique_personnel_projet",
            ),
        ]
        verbose_name = "Équipe de projet"
        verbose_name_plural = "Équipe des projets"

    def __str__(self):
        return (
            f"{self.personnel} - "
            f"{self.get_fonction_display()} - "
            f"{self.projet.titre}"
        )

    def clean(self):
        errors = {}

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

        # ----------------------------------------------------
        # TYPE DE PERSONNEL
        # ----------------------------------------------------

        if self.personnel_id:

            personnel = self.personnel

            if personnel.typeTravail != "Construction":
                errors["personnel"] = (
                    "Le personnel affecté à un projet doit "
                    "appartenir au personnel Construction."
                )

        if errors:
            raise ValidationError(errors)

    @property
    def acces_actif(self):
        """
        True si l'affectation est actuellement active.
        """

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
        """
        Retourne le compte utilisateur lié au personnel,
        si la relation existe.
        """

        return getattr(
            self.personnel,
            "user",
            None,
        )

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
# VÉHICULE / ENGIN AFFECTÉ AU PROJET
# ============================================================

class VehiculeProjet(models.Model):
    """
    Véhicule ou engin affecté à un projet.

    ROUTIER :
        - suivi par kilométrage
        - consommation en km/L

    ENGIN :
        - suivi par heures de fonctionnement
        - consommation en L/h

    Exemple d'ENGIN :
        - Pelle
        - Bulldozer
        - Chargeuse
        - Compacteur
        - Grue
        - etc.
    """

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

    # ========================================================
    # KILOMÉTRAGE
    # ========================================================

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

    # ========================================================
    # HEURES DE FONCTIONNEMENT DES ENGINS
    # ========================================================

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

    # ========================================================
    # VALIDATION
    # ========================================================

    def clean(self):

        errors = {}

        # ----------------------------------------------------
        # DATES
        # ----------------------------------------------------

        if (
            self.date_debut
            and self.date_fin
            and self.date_fin < self.date_debut
        ):
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
                    "L'affectation du véhicule ne peut pas "
                    "commencer avant le début du projet."
                )

            if (
                self.date_fin
                and projet.date_fin
                and self.date_fin > projet.date_fin
            ):
                errors["date_fin"] = (
                    "L'affectation du véhicule ne peut pas "
                    "dépasser la date de fin du projet."
                )

        # ----------------------------------------------------
        # KILOMÉTRAGE
        # ----------------------------------------------------

        if (
            self.kilometrage_initial is not None
            and self.kilometrage_initial < Decimal("0.00")
        ):
            errors["kilometrage_initial"] = (
                "Le kilométrage initial ne peut pas être négatif."
            )

        if (
            self.kilometrage_final is not None
            and self.kilometrage_final < Decimal("0.00")
        ):
            errors["kilometrage_final"] = (
                "Le kilométrage final ne peut pas être négatif."
            )

        if (
            self.kilometrage_initial is not None
            and self.kilometrage_final is not None
            and self.kilometrage_final
            < self.kilometrage_initial
        ):
            errors["kilometrage_final"] = (
                "Le kilométrage final doit être supérieur "
                "ou égal au kilométrage initial."
            )

        if (
            self.consommation_km_litre is not None
            and self.consommation_km_litre < Decimal("0.00")
        ):
            errors["consommation_km_litre"] = (
                "La consommation km/L ne peut pas être négative."
            )

        # ----------------------------------------------------
        # HEURES DES ENGINS
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

        if (
            self.consommation_heure_litre is not None
            and self.consommation_heure_litre < Decimal("0.00")
        ):
            errors["consommation_heure_litre"] = (
                "La consommation L/h ne peut pas être négative."
            )

        if errors:
            raise ValidationError(errors)

    # ========================================================
    # PROPRIÉTÉS
    # ========================================================

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

    # ========================================================
    # KILOMÈTRES PARCOURUS
    # ========================================================

    @property
    def kilometres_parcourus(self):

        if self.type_vehicule == "ENGIN":
            return Decimal("0.00")

        if (
            self.kilometrage_initial is None
            or self.kilometrage_final is None
        ):
            return Decimal("0.00")

        return max(
            Decimal("0.00"),
            self.kilometrage_final
            - self.kilometrage_initial,
        )

    # ========================================================
    # HEURES DE TRAVAIL
    # ========================================================

    @property
    def heures_travail(self):

        if self.type_vehicule != "ENGIN":
            return Decimal("0.00")

        if (
            self.heures_initiales is None
            or self.heures_finales is None
        ):
            return Decimal("0.00")

        return max(
            Decimal("0.00"),
            self.heures_finales
            - self.heures_initiales,
        )

    # ========================================================
    # CARBURANT ESTIMÉ
    # ========================================================

    @property
    def carburant_estime(self):

        # ----------------------------------------------------
        # ENGIN : heures × L/h
        # ----------------------------------------------------

        if self.type_vehicule == "ENGIN":

            consommation = self.consommation_heure_litre

            if (
                not consommation
                or consommation <= Decimal("0.00")
            ):
                return Decimal("0.00")

            return (
                self.heures_travail
                * consommation
            ).quantize(
                Decimal("0.01")
            )

        # ----------------------------------------------------
        # ROUTIER : kilomètres ÷ km/L
        # ----------------------------------------------------

        consommation = self.consommation_km_litre

        if (
            not consommation
            or consommation <= Decimal("0.00")
        ):
            return Decimal("0.00")

        return (
            self.kilometres_parcourus
            / consommation
        ).quantize(
            Decimal("0.01")
        )

    # ========================================================
    # LIBELLÉ DE L'UNITÉ DE TRAVAIL
    # ========================================================

    @property
    def unite_travail(self):

        if self.type_vehicule == "ENGIN":
            return "heures"

        return "km"

    # ========================================================
    # VALEUR DE TRAVAIL À AFFICHER
    # ========================================================

    @property
    def travail_total(self):

        if self.type_vehicule == "ENGIN":
            return self.heures_travail

        return self.kilometres_parcourus


# ============================================================
# MOUVEMENT D'UN VÉHICULE / ENGIN SUR LE PROJET
# ============================================================

class MouvementVehiculeProjet(models.Model):

    vehicule_projet = models.ForeignKey(
        VehiculeProjet,
        on_delete=models.PROTECT,
        related_name="mouvements",
        verbose_name="Véhicule / Engin",
    )

    date_mouvement = models.DateTimeField(
        default=timezone.now,
        verbose_name="Date du mouvement",
    )

    point_depart = models.ForeignKey(
        PointProjet,
        on_delete=models.PROTECT,
        related_name="mouvements_vehicules_depart",
        null=True,
        blank=True,
        verbose_name="Point de départ",
    )

    point_arrivee = models.ForeignKey(
        PointProjet,
        on_delete=models.PROTECT,
        related_name="mouvements_vehicules_arrivee",
        null=True,
        blank=True,
        verbose_name="Point d'arrivée",
    )

    # ========================================================
    # ROUTIER : KILOMÉTRAGE
    # ========================================================

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

    # ========================================================
    # ENGIN : HEURES
    # ========================================================

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
        related_name="mouvements_vehicules_enregistres",
        verbose_name="Enregistré par",
    )

    class Meta:
        ordering = [
            "-date_mouvement",
            "-id",
        ]

        verbose_name = "Mouvement véhicule"
        verbose_name_plural = "Mouvements véhicules"

    def __str__(self):
        return (
            f"{self.vehicule_projet.vehicule} - "
            f"{self.date_mouvement:%d/%m/%Y %H:%M}"
        )

    def clean(self):

        errors = {}

        vehicule = self.vehicule_projet if self.vehicule_projet_id else None

        if not vehicule:
            return

        # ----------------------------------------------------
        # PROJET
        # ----------------------------------------------------

        if self.point_depart_id:
            if self.point_depart.projet_id != vehicule.projet_id:
                errors["point_depart"] = (
                    "Le point de départ n'appartient pas "
                    "au projet du véhicule."
                )

        if self.point_arrivee_id:
            if self.point_arrivee.projet_id != vehicule.projet_id:
                errors["point_arrivee"] = (
                    "Le point d'arrivée n'appartient pas "
                    "au projet du véhicule."
                )

        # ----------------------------------------------------
        # DATE
        # ----------------------------------------------------

        if self.date_mouvement:

            if self.date_mouvement.date() < vehicule.date_debut:
                errors["date_mouvement"] = (
                    "La date du mouvement est avant "
                    "le début de l'affectation."
                )

            elif self.date_mouvement.date() > vehicule.date_fin:
                errors["date_mouvement"] = (
                    "La date du mouvement dépasse "
                    "la fin de l'affectation."
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
    def kilometres(self):

        return max(
            Decimal("0.00"),
            self.kilometrage_final
            - self.kilometrage_initial,
        )

    @property
    def heures(self):

        return max(
            Decimal("0.00"),
            self.heures_finales
            - self.heures_initiales,
        )

    @property
    def travail(self):

        if self.vehicule_projet.type_vehicule == "ENGIN":
            return self.heures

        return self.kilometres

    @property
    def unite_travail(self):

        if self.vehicule_projet.type_vehicule == "ENGIN":
            return "h"

        return "km"

    @property
    def carburant_estime(self):

        vehicule = self.vehicule_projet

        if vehicule.type_vehicule == "ENGIN":

            if vehicule.consommation_heure_litre <= Decimal("0.00"):
                return Decimal("0.00")

            return (
                self.heures
                * vehicule.consommation_heure_litre
            ).quantize(
                Decimal("0.01")
            )

        if vehicule.consommation_km_litre <= Decimal("0.00"):
            return Decimal("0.00")

        return (
            self.kilometres
            / vehicule.consommation_km_litre
        ).quantize(
            Decimal("0.01")
        )


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

        personnel = (
            self.personnel_execution
            if self.personnel_execution_id
            else None
        )

        if not personnel:
            return

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
# PERSONNEL D'EXÉCUTION DU PROJET
# ============================================================

class PersonnelExecutionProjet(models.Model):
    """
    Personnel réellement utilisé pour l'exécution d'un projet.

    Certains profils proviennent de la table Personnel :
        - Ingénieur
        - Chef de chantier
        - Chauffeur
        - Chef magasinier
        - Magasinier

    D'autres profils peuvent être saisis manuellement :
        - Chef d'équipe
        - Conducteur d'engin
        - Minier
        - Autre
    """

    TYPE_CLASS_CHOICES = [
        (
            "INGENIEUR",
            "Ingénieur Responsable de Projet",
        ),
        (
            "CHEF_CHANTIER",
            "Chef de Chantier",
        ),
        (
            "CHEF_EQUIPE",
            "Chef d'équipe",
        ),
        (
            "CHAUFFEUR_ENGIN",
            "Conducteur d'engin",
        ),
        (
            "CHAUFFEUR",
            "Chauffeur",
        ),
        (
            "CHEF_MAGASIN",
            "Chef Magasinier",
        ),
        (
            "MAGASIN",
            "Magasinier",
        ),
        (
            "MINIER",
            "Mpamaky vato",
        ),
        (
            "AUTRE",
            "Autre",
        ),
    ]

    TYPE_CONTRAT_CHOICES = [
        (
            "MENSUEL",
            "Salarié mensuel",
        ),
        (
            "FORFAITAIRE",
            "Forfaitaire",
        ),
        (
            "PRE_PAYER",
            "Pré-payé",
        ),
    ]

    projet = models.ForeignKey(
        Projet,
        on_delete=models.PROTECT,
        related_name="personnels_execution",
        verbose_name="Projet",
    )

    type_class = models.CharField(
        max_length=30,
        choices=TYPE_CLASS_CHOICES,
        verbose_name="Classe",
    )

    personnel = models.ForeignKey(
        Personnel,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="executions_projets",
        verbose_name="Personnel",
    )

    nom = models.CharField(
        max_length=255,
        verbose_name="Nom",
    )

    type_contrat = models.CharField(
        max_length=20,
        choices=TYPE_CONTRAT_CHOICES,
        default="MENSUEL",
        verbose_name="Type de contrat",
    )

    salaire = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0.00"),
        verbose_name="Salaire / Montant",
    )

    date_debut = models.DateTimeField(
        verbose_name="Date de début",
    )

    date_fin = models.DateTimeField(
        verbose_name="Date de fin",
    )

    photo = models.ImageField(
        upload_to="images/EquipeExecution/",
        blank=True,
        null=True,
        verbose_name="Photo",
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
        related_name="personnels_execution_enregistres",
        verbose_name="Enregistré par",
    )

    class Meta:
        ordering = [
            "date_debut",
            "nom",
        ]
        verbose_name = "Personnel d'exécution"
        verbose_name_plural = "Personnel d'exécution"

    def __str__(self):
        return (
            f"{self.nom} - "
            f"{self.get_type_class_display()} - "
            f"{self.projet.titre}"
        )

    def clean(self):
        errors = {}

        # ====================================================
        # TYPES UTILISANT PERSONNEL
        # ====================================================

        types_personnel = {
            "INGENIEUR",
            "CHEF_CHANTIER",
            "CHAUFFEUR",
            "CHEF_MAGASIN",
            "MAGASIN",
        }

        # ====================================================
        # TYPES À SAISIE MANUELLE
        # ====================================================

        types_manuels = {
            "CHEF_EQUIPE",
            "CHAUFFEUR_ENGIN",
            "MINIER",
            "AUTRE",
        }

        # ====================================================
        # PERSONNEL EXISTANT
        # ====================================================

        if self.type_class in types_personnel:

            if not self.personnel_id:

                errors["personnel"] = (
                    "Veuillez sélectionner un personnel."
                )

            else:

                personnel = self.personnel

                if personnel.typeTravail != "Construction":

                    errors["personnel"] = (
                        "Le personnel sélectionné doit "
                        "appartenir à Construction."
                    )

                else:

                    # Nom automatiquement récupéré
                    # depuis Personnel.
                    self.nom = str(personnel)

        # ====================================================
        # NOM MANUEL
        # ====================================================

        elif self.type_class in types_manuels:

            self.personnel = None

            if not self.nom or not self.nom.strip():

                errors["nom"] = (
                    "Veuillez saisir le nom du travailleur."
                )

        # ====================================================
        # CONTRAT
        # ====================================================

        if self.type_class == "CHEF_EQUIPE":

            if self.type_contrat != "FORFAITAIRE":

                errors["type_contrat"] = (
                    "Le Chef d'équipe doit avoir "
                    "un contrat forfaitaire."
                )

        elif self.type_class == "MINIER":

            if self.type_contrat != "PRE_PAYER":

                errors["type_contrat"] = (
                    "Le Minier doit avoir "
                    "un contrat pré-payé."
                )

        else:

            if self.type_contrat != "MENSUEL":

                errors["type_contrat"] = (
                    "Ce type de personnel doit avoir "
                    "un contrat mensuel."
                )

        # ====================================================
        # SALAIRE / MONTANT
        # ====================================================

        if (
            self.salaire is not None
            and self.salaire < Decimal("0.00")
        ):

            errors["salaire"] = (
                "Le salaire ou montant ne peut pas "
                "être négatif."
            )

        # ====================================================
        # DATES
        # ====================================================

        if (
            self.date_debut
            and self.date_fin
            and self.date_fin < self.date_debut
        ):

            errors["date_fin"] = (
                "La date de fin doit être "
                "postérieure ou égale à la date de début."
            )

        # ====================================================
        # LIMITES DU PROJET
        # ====================================================

        if self.projet_id:

            projet = self.projet

            if (
                self.date_debut
                and projet.date_debut
                and self.date_debut.date() < projet.date_debut
            ):

                errors["date_debut"] = (
                    "La date de début ne peut pas "
                    "être avant le début du projet."
                )

            if (
                self.date_fin
                and projet.date_fin
                and self.date_fin.date() > projet.date_fin
            ):

                errors["date_fin"] = (
                    "La date de fin ne peut pas "
                    "dépasser la fin du projet."
                )

        if errors:
            raise ValidationError(errors)

    @property
    def periode_terminee(self):

        if not self.date_fin:
            return False

        return timezone.now() > self.date_fin

    @property
    def actif(self):

        if not self.date_debut or not self.date_fin:
            return False

        maintenant = timezone.now()

        return (
            self.date_debut
            <= maintenant
            <= self.date_fin
        )


# ============================================================
# CHEF D'ÉQUIPE / ÉQUIPAGE DU PROJET
# ============================================================

class EquipageProjet(models.Model):

    personnel_execution = models.ForeignKey(
        "PersonnelExecutionProjet",
        on_delete=models.PROTECT,
        related_name="equipages",
        verbose_name="Personnel d'exécution",
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
        verbose_name="Montant du travail",
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

        if (
            self.date_debut
            and self.date_fin
            and self.date_fin < self.date_debut
        ):
            errors["date_fin"] = (
                "La date de fin doit être "
                "postérieure ou égale à la date de début."
            )

        if self.personnel_execution_id and self.lieu_id:

            if (
                self.personnel_execution.projet_id
                != self.lieu.projet_id
            ):
                errors["lieu"] = (
                    "Le point de chantier et le personnel "
                    "doivent appartenir au même projet."
                )

        if self.montant is not None and self.montant < 0:

            errors["montant"] = (
                "Le montant ne peut pas être négatif."
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
        PersonnelExecutionProjet,
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
# VÉHICULES LOURDS DU PROJET
# ============================================================

class VehiculeLourdsProjet(models.Model):

    projet = models.ForeignKey(
        Projet,
        on_delete=models.PROTECT,
        related_name="vehicules_lourds",
        verbose_name="Projet",
    )

    matricule = models.CharField(
        max_length=30,
        verbose_name="Numéro matricule",
    )

    conducteur = models.CharField(
        max_length=255,
        verbose_name="Nom du conducteur",
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
    )

    updated_at = models.DateTimeField(
        auto_now=True,
    )

    class Meta:
        ordering = [
            "matricule",
        ]
        verbose_name = "Véhicule lourd du projet"
        verbose_name_plural = "Véhicules lourds du projet"

    def __str__(self):
        return (
            f"{self.matricule} - "
            f"{self.conducteur}"
        )


# ============================================================
# ACTIVITÉ TRANSPORT DU PROJET
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

        # ----------------------------------------------------
        # DISTANCE
        # ----------------------------------------------------

        if (
            self.distance_km is not None
            and self.distance_km < Decimal("0.00")
        ):
            errors["distance_km"] = (
                "La distance ne peut pas être négative."
            )

        # ----------------------------------------------------
        # KILOMÉTRAGE
        # ----------------------------------------------------

        if (
            self.kilometrage_initial is not None
            and self.kilometrage_initial < Decimal("0.00")
        ):
            errors["kilometrage_initial"] = (
                "Le kilométrage initial ne peut pas être négatif."
            )

        if (
            self.kilometrage_final is not None
            and self.kilometrage_final < Decimal("0.00")
        ):
            errors["kilometrage_final"] = (
                "Le kilométrage final ne peut pas être négatif."
            )

        if (
            self.kilometrage_initial is not None
            and self.kilometrage_final is not None
            and self.kilometrage_final
            < self.kilometrage_initial
        ):
            errors["kilometrage_final"] = (
                "Le kilométrage final doit être supérieur "
                "ou égal au kilométrage initial."
            )

        # ----------------------------------------------------
        # CONSOMMATION
        # ----------------------------------------------------

        if (
            self.consommation_km_litre is not None
            and self.consommation_km_litre < Decimal("0.00")
        ):
            errors["consommation_km_litre"] = (
                "La consommation ne peut pas être négative."
            )

        # ----------------------------------------------------
        # QUANTITÉ
        # ----------------------------------------------------

        if (
            self.quantite is not None
            and self.quantite < Decimal("0.00")
        ):
            errors["quantite"] = (
                "La quantité ne peut pas être négative."
            )

        # ----------------------------------------------------
        # DATE
        # ----------------------------------------------------

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
        
        # On compare donc le matricule du vrai véhicule avec
        # le texte enregistré dans VehiculeProjet.
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

        if (
            self.kilometrage_initial is None
            or self.kilometrage_final is None
        ):
            return Decimal("0.00")

        return max(
            Decimal("0.00"),
            self.kilometrage_final
            - self.kilometrage_initial,
        )

    @property
    def carburant_estime(self):

        consommation = self.consommation_km_litre

        if (
            not consommation
            or consommation <= Decimal("0.00")
        ):
            return Decimal("0.00")

        return (
            self.kilometres_parcourus
            / consommation
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

        date_rapport = (
            self.date_rapport
            if self.date_rapport
            else "Date non définie"
        )

        projet = (
            self.projet.titre
            if self.projet_id
            else "Projet non défini"
        )

        return (
            f"{vehicule} - "
            f"{date_rapport} - "
            f"{projet}"
        )

    def clean(self):
        errors = {}

        # ----------------------------------------------------
        # KILOMÉTRAGE
        # ----------------------------------------------------

        if (
            self.kilometrage is not None
            and self.kilometrage < Decimal("0.00")
        ):
            errors["kilometrage"] = (
                "Le kilométrage ne peut pas être négatif."
            )

        # ----------------------------------------------------
        # PROJET / DATE
        # ----------------------------------------------------

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