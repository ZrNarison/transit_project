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
        ordering = ["-date_debut", "-id"]
        verbose_name = "Projet"
        verbose_name_plural = "Projets"

    def __str__(self):
        return f"{self.titre} - {self.localisation}"

    def clean(self):
            errors = {}

            # ============================================================
            # KILOMÉTRAGE
            # ============================================================

            if (
                self.kilometrage is not None
                and self.kilometrage < 0
            ):
                errors["kilometrage"] = (
                    "Le kilométrage ne peut pas être négatif."
                )

            # ============================================================
            # PROJET / DATE
            # ============================================================

            projet = None

            if self.projet_id:

                projet = self.projet

                if self.date_rapport:

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

            # ============================================================
            # CHAUFFEUR
            # ============================================================
            #
            # IMPORTANT :
            # Ne jamais faire :
            #
            #     if self.chauffeur:
            #
            # car chauffeur peut être NULL/non défini pendant
            # la validation du ModelForm.
            #
            # On utilise chauffeur_id avant d'accéder à self.chauffeur.
            # ============================================================

            chauffeur = None

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

            # ============================================================
            # VÉHICULE
            # ============================================================

            if (
                self.projet_id
                and self.vehicule_id
            ):

                affectation = (
                    VehiculeProjet.objects
                    .filter(
                        projet_id=self.projet_id,
                        vehicule_id=self.vehicule_id,
                        actif=True,
                    )
                    .exists()
                )

                if not affectation:

                    errors["vehicule"] = (
                        "Ce véhicule n'est pas actuellement "
                        "affecté à ce projet."
                    )

            # ============================================================
            # ERREURS
            # ============================================================

            if errors:
                raise ValidationError(errors)

        
    @property
    def est_actif(self):
        """
        Projet considéré actif uniquement pendant sa période
        contractuelle et lorsque son statut est EN_COURS.
        """

        aujourd_hui = timezone.localdate()

        if not self.date_debut or not self.date_fin:
            return False

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


# ============================================================
# EQUIPE DU PROJET
# ============================================================

class EquipeProjet(models.Model):
    """
    Personnel affecté à un projet.

    Le même personnel peut participer à plusieurs projets.

    L'accès est considéré actif uniquement lorsque :

        actif = True
        ET
        date_debut <= aujourd'hui <= date_fin

    Après date_fin, l'historique reste conservé mais
    l'affectation n'est plus considérée comme active.
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

        if self.projet:

            if (
                self.date_debut
                and self.projet.date_debut
                and self.date_debut < self.projet.date_debut
            ):
                errors["date_debut"] = (
                    "L'affectation ne peut pas commencer "
                    "avant le début du projet."
                )

            if (
                self.date_fin
                and self.projet.date_fin
                and self.date_fin > self.projet.date_fin
            ):
                errors["date_fin"] = (
                    "L'affectation ne peut pas dépasser "
                    "la date de fin du projet."
                )

        # ----------------------------------------------------
        # TYPE DE PERSONNEL
        # ----------------------------------------------------

        if self.personnel:

            if self.personnel.typeTravail != "Construction":
                errors["personnel"] = (
                    "Le personnel affecté à un projet doit "
                    "appartenir au personnel Construction."
                )

        if errors:
            raise ValidationError(errors)

    @property
    def acces_actif(self):
        """
        Détermine si l'affectation est actuellement active.

        Important :
        même si actif=True, l'accès est automatiquement
        désactivé après date_fin.
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
        Retourne le compte utilisateur lié au personnel.

        Compatible avec un Personnel possédant une relation
        user.
        """

        return getattr(
            self.personnel,
            "user",
            None,
        )

    @property
    def periode_terminee(self):
        """
        True lorsque l'affectation est terminée.
        """

        if not self.date_fin:
            return False

        return timezone.localdate() > self.date_fin


# ============================================================
# POINT DE CHANTIER
# ============================================================

class PointProjet(models.Model):
    """
    Point de travail / point de ravitaillement d'un projet.
    """

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

    # responsable = models.ForeignKey(
    #     Personnel,
    #     on_delete=models.PROTECT,
    #     related_name="points_responsables",
    #     verbose_name="Responsable",
    # )

    localisation = models.CharField(
        max_length=200,
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
        return (
            f"{self.nom} - "
            f"({self.distance_km} km)"
        )

    def clean(self):
        errors = {}

        if (
            self.distance_km is not None
            and self.distance_km < 0
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
    """
    Rapport général du projet.

    Utilisé notamment par l'Ingénieur Responsable du Chantier.
    """

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
        return (
            f"{self.titre} - "
            f"{self.projet.titre}"
        )

    def clean(self):
        errors = {}

        if self.avancement is not None:

            if (
                self.avancement < 0
                or self.avancement > 100
            ):
                errors["avancement"] = (
                    "L'avancement doit être compris "
                    "entre 0 et 100 %."
                )

        if self.projet and self.date_rapport:

            if self.date_rapport < self.projet.date_debut:
                errors["date_rapport"] = (
                    "La date du rapport ne peut pas "
                    "être avant le début du projet."
                )

            elif self.date_rapport > self.projet.date_fin:
                errors["date_rapport"] = (
                    "La date du rapport ne peut pas "
                    "dépasser la fin du projet."
                )

        if self.auteur:

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
    """
    Rapport d'un travail effectué sur un point de chantier.
    """

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
        return (
            f"{self.titre} - "
            f"{self.projet.titre}"
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

        if self.projet:

            if (
                self.date_debut
                and self.date_debut < self.projet.date_debut
            ):
                errors["date_debut"] = (
                    "La date de début du travail "
                    "ne peut pas être avant le projet."
                )

            if (
                self.date_fin
                and self.date_fin > self.projet.date_fin
            ):
                errors["date_fin"] = (
                    "La date de fin du travail "
                    "ne peut pas dépasser le projet."
                )

        if self.point and self.projet:

            if self.point.projet_id != self.projet_id:
                errors["point"] = (
                    "Le point sélectionné "
                    "n'appartient pas à ce projet."
                )

        if self.auteur:

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
    """
    Suivi des matériaux approvisionnés sur un projet.
    """

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
            and self.quantite <= 0
        ):
            errors["quantite"] = (
                "La quantité doit être supérieure à zéro."
            )

        if self.projet and self.point:

            if self.point.projet_id != self.projet_id:
                errors["point"] = (
                    "Le point sélectionné "
                    "n'appartient pas à ce projet."
                )

        if self.projet and self.date_ravitaillement:

            if (
                self.date_ravitaillement
                < self.projet.date_debut
            ):
                errors["date_ravitaillement"] = (
                    "La date de ravitaillement "
                    "ne peut pas être avant le début du projet."
                )

            elif (
                self.date_ravitaillement
                > self.projet.date_fin
            ):
                errors["date_ravitaillement"] = (
                    "La date de ravitaillement "
                    "ne peut pas dépasser la fin du projet."
                )

        if self.auteur:

            if self.auteur.typeTravail != "Construction":
                errors["auteur"] = (
                    "Le magasinier doit appartenir "
                    "au personnel Construction."
                )

        if errors:
            raise ValidationError(errors)


# ============================================================
# VÉHICULE AFFECTÉ AU PROJET
# ============================================================

class VehiculeProjet(models.Model):
    """
    Véhicule affecté à un projet.

    Tous les membres du Personnel peuvent être désignés
    comme chauffeur du véhicule.

    Le véhicule est actuellement identifié par son numéro
    matricule sous forme de texte.
    """

    projet = models.ForeignKey(
        Projet,
        on_delete=models.PROTECT,
        related_name="vehicules_projet",
        verbose_name="Projet",
    )

    vehicule = models.CharField(
        max_length=30,
        verbose_name="Véhicule",
    )

    chauffeur = models.ForeignKey(
        Personnel,
        on_delete=models.PROTECT,
        related_name="affectations_vehicules_projets",
        verbose_name="Chauffeur",
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
        verbose_name="Consommation (km/l)",
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

        verbose_name = "Véhicule affecté au projet"
        verbose_name_plural = "Véhicules affectés aux projets"

    def __str__(self):
        chauffeur = (
            str(self.chauffeur)
            if self.chauffeur
            else "Sans chauffeur"
        )

        return (
            f"{self.vehicule} - "
            f"{self.projet.titre} - "
            f"{chauffeur}"
        )

    # =========================================================
    # VALIDATION
    # =========================================================

    def clean(self):
        errors = {}

        # -----------------------------------------------------
        # DATES
        # -----------------------------------------------------

        if (
            self.date_debut
            and self.date_fin
            and self.date_fin < self.date_debut
        ):
            errors["date_fin"] = (
                "La fin de l'affectation doit être "
                "postérieure ou égale au début."
            )

        # -----------------------------------------------------
        # RESPECT DES DATES DU PROJET
        # -----------------------------------------------------

        if self.projet:

            if (
                self.date_debut
                and self.projet.date_debut
                and self.date_debut < self.projet.date_debut
            ):
                errors["date_debut"] = (
                    "L'affectation du véhicule ne peut pas "
                    "commencer avant le début du projet."
                )

            if (
                self.date_fin
                and self.projet.date_fin
                and self.date_fin > self.projet.date_fin
            ):
                errors["date_fin"] = (
                    "L'affectation du véhicule ne peut pas dépasser la date de fin du projet."
                )

        # -----------------------------------------------------
        # KILOMÉTRAGE INITIAL
        # -----------------------------------------------------

        if (
            self.kilometrage_initial is not None
            and self.kilometrage_initial < 0
        ):
            errors["kilometrage_initial"] = (
                "Le kilométrage initial ne peut pas être négatif."
            )

        # -----------------------------------------------------
        # KILOMÉTRAGE FINAL
        # -----------------------------------------------------

        if (
            self.kilometrage_final is not None
            and self.kilometrage_final < 0
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
                "Le kilométrage final doit être supérieur ou égal au kilométrage initial."
            )

        # -----------------------------------------------------
        # CONSOMMATION
        # -----------------------------------------------------

        if (
            self.consommation_km_litre is not None
            and self.consommation_km_litre < 0
        ):
            errors["consommation_km_litre"] = (
                "La consommation ne peut pas être négative."
            )

        if errors:
            raise ValidationError(errors)

    # =========================================================
    # ACCÈS ACTIF
    # =========================================================

    @property
    def acces_actif(self):
        """
        True si l'affectation du véhicule est active
        à la date actuelle.
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

    # =========================================================
    # PÉRIODE TERMINÉE
    # =========================================================

    @property
    def periode_terminee(self):
        if not self.date_fin:
            return False

        return timezone.localdate() > self.date_fin

    # =========================================================
    # KILOMÈTRES PARCOURUS
    # =========================================================

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

    # =========================================================
    # CARBURANT ESTIMÉ
    # =========================================================

    @property
    def carburant_estime(self):
        consommation = self.consommation_km_litre

        if (
            not consommation
            or consommation <= 0
        ):
            return Decimal("0.00")

        return (
            self.kilometres_parcourus
            / consommation
        ).quantize(
            Decimal("0.01")
        )
# ============================================================
# PERSONNEL D'EXEUCUTION
# ===========================================================
class PersonnelExecutionProjet(models.Model):
   TYPE_CLASS_CHOICES = [
       0("INGENIEUR","Ingenieur Responsable de Projet"),
       0("CHEF_CHANTIER","Chef de Chanatier"),
       ("CHEF_EQUIPE","Chef d'équipe"),
       ("CHAUFFEUR_ENGIN","Conducteur"),
       0("CHAUFFEUR","Chauffeur"),
       0("CHEF_MAGASIN","Chef Magasinier"),
       0("MAGASIN","Magasinier"),
       ("MINIER","Mpamaky vato"),
       ("AUTRE","Autres"),
       ]
   
   nom = le nom apres la presedante, quand il select l'un que je marque 0'
   'on recherche dépuis personnel (
       s'il est Ingenieur Responsable de Projet ou Chef de Chantier ou Chef Magasinier ou Magasinier on la chercher depui le Personnel
    # mais s'il est autre que dans la liste on le saisisse
   )
    
    TYPE_CONTRAT_CHOICES = [ 
        s'il est CHEF_EQUIPE son contrat est
           ("FORFAITAIRE","Forfaitaire"), c-a-d le contrat se fait par le projet qu'il doit faire
        s'il est MINIER son contrat est pré_payer
           ("PRE_PAYER","Pré Payer"), c-a-d le contrat se fait par la projet qu'il fait
           ]
   salaire = seul le forfaitaire et pre_payer son salaire dont le reste son salarié mensuel au projet mais ce deux son payer par le Projet
   
    datedebut = models.DateTimeField()
    datefin = models.DateTimeField()
    photo = models.ImageField(
        upload_to="images/EquipeExecution/",
        blank=True,
        null=True
    )
    created_at = models.DateTimeField()
        
    updated_at = models.DateTimeField()

    enregistre_par = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipe_projet"
    )

# =============================================================
# CHEF D'EQUIPE
# =============================================================
class EquipageProjet(models.Model):
    nom = models.ForeignKey(
        PersonnelExecutionProjet,
        on_delete=models.PROTECT,
        related_name="personnelExecution_class",
        verbose_name="travaux à faire",
    )
    lieu = models.ForeignKey(
        PointProjet,
        on_delete=models.PROTECT,
        related_name="points_nom",
        verbose_name="travaux à faire",
    )
    montant = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=Decimal("0"),
        verbose_name="Montant du travail",
    )
    dadedebut = models.DateTimeField(
        max_length=5,
    )

    created_at = models.DateTimeField()
    
    updated_at = models.DateTimeField()

    enregistre_par = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipe_projet"
    )
    
# ============================================================
# AVANCE EQUIPE PROJET
# ============================================================
class AvanceEquipeProjet(models.Model):
    Nom =  models.ForeignKey(
            PointProjet,
            on_delete=models.PROTECT,
            related_name="PersonnelExecution_nom",
            verbose_name="Nom du travailleur",
        )
    montant = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=Decimal("0"),
        verbose_name="Montant de l'avance",
    )
    dateAvanceEquipe = models.DateTimeField()

    created_at = models.DateTimeField()
        
    updated_at = models.DateTimeField()

    enregistre_par = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="avace_equipe_projet"
    )

# ==========================================================
# EQUIPE MATERIAUX
# ===========================================================
class EquipeMateriauProjet(models.Model):
    Nom = models.ForeignKey(
        PointProjet,
        on_delete=models.PROTECT,
        related_name="PersonnelExecution_nom",
        verbose_name="Nom du travailleur",
    )
    
    typemateriaux = models.ForeignKey(
            materiauxProjet,
            on_delete=models.PROTECT,
            related_name="points_nom",
            verbose_name="Type",
        )
    quantite = models.DecimalField(
        max_digits=5,
        decimal_places=0,
        default=Decimal("0")
    )
    # unite = unité selon materiaux
    prix_unitaire = models.DecimalField(
        max_digits=5,
        decimal_places=0,
        default=Decimal("0")
    )

    datedebut = models.DateTimeField()
    
    created_at = models.DateTimeField()
        
    updated_at = models.DateTimeField()

    enregistre_par = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="avace_equipe_projet"
    )
    

#  ==========================================================
# VEHICULE LOURD
# ===========================================================
class VehiculeLourdsProjet(models.Model):
    matricule = models.CharField(
        max_length=10,
        verbose_name="Numéro matricule ",
    )
    conducteur = models.CharField(
        max_length=255,
        verbose_name="Nom du conducteur", 
    )
    



# ============================================================
# ACTIVITÉ TRANSPORT DU PROJET
# ============================================================

class ActiviteTransportProjet(models.Model):
    """
    Activité de transport réalisée dans le cadre d'un projet.
    Le véhicule provient de materiaux.Vehicule.

    Le chauffeur doit être :
        - Personnel Construction
        - affecté au projet
        - affecté avec fonction CHAUFFEUR
        - actif

    Les historiques restent conservés après la fin du projet.
    """

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

        # ----------------------------------------------------
        # DISTANCE
        # ----------------------------------------------------

        if (
            self.distance_km is not None
            and self.distance_km < 0
        ):
            errors["distance_km"] = (
                "La distance ne peut pas être négative."
            )

        # ----------------------------------------------------
        # KILOMÉTRAGE
        # ----------------------------------------------------

        if (
            self.kilometrage_initial is not None
            and self.kilometrage_initial < 0
        ):
            errors["kilometrage_initial"] = (
                "Le kilométrage initial ne peut pas être négatif."
            )

        if (
            self.kilometrage_final is not None
            and self.kilometrage_final < 0
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
            and self.consommation_km_litre < 0
        ):
            errors["consommation_km_litre"] = (
                "La consommation ne peut pas être négative."
            )

        # ----------------------------------------------------
        # QUANTITÉ
        # ----------------------------------------------------

        if (
            self.quantite is not None
            and self.quantite < 0
        ):
            errors["quantite"] = (
                "La quantité ne peut pas être négative."
            )

        # ----------------------------------------------------
        # DATE TRANSPORT
        # ----------------------------------------------------

        if self.projet and self.date_transport:

            if self.date_transport < self.projet.date_debut:
                errors["date_transport"] = (
                    "La date du transport ne peut pas être "
                    "avant le début du projet."
                )

            elif self.date_transport > self.projet.date_fin:
                errors["date_transport"] = (
                    "La date du transport ne peut pas dépasser "
                    "la fin du projet."
                )

        # ----------------------------------------------------
        # CHAUFFEUR
        # ----------------------------------------------------

        if self.chauffeur:

            if self.chauffeur.typeTravail != "Construction":
                errors["chauffeur"] = (
                    "Le chauffeur doit appartenir "
                    "au personnel Construction."
                )

            if self.projet:

                affectation = EquipeProjet.objects.filter(
                    projet=self.projet,
                    personnel=self.chauffeur,
                    fonction="CHAUFFEUR",
                    actif=True,
                ).exists()

                if not affectation:
                    errors["chauffeur"] = (
                        "Ce personnel n'est pas affecté "
                        "comme chauffeur à ce projet."
                    )

        # ----------------------------------------------------
        # VÉHICULE
        # ----------------------------------------------------

        if self.projet and self.vehicule:

            affectation = VehiculeProjet.objects.filter(
                projet=self.projet,
                vehicule=self.vehicule,
                actif=True,
            ).exists()

            if not affectation:
                errors["vehicule"] = (
                    "Ce véhicule n'est pas affecté "
                    "à ce projet."
                )

        if errors:
            raise ValidationError(errors)

    @property
    def kilometres_parcourus(self):
        """
        Distance calculée à partir du compteur.
        """

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
        """
        Estimation du carburant consommé en litres.
        """

        consommation = self.consommation_km_litre

        if (
            not consommation
            or consommation <= 0
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
    """
    Rapport d'état du véhicule réalisé par un chauffeur.
    Le véhicule provient de materiaux.Vehicule.
    """

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

        # ====================================================
        # KILOMÉTRAGE
        # ====================================================

        if (
            self.kilometrage is not None
            and self.kilometrage < Decimal("0.00")
        ):
            errors["kilometrage"] = (
                "Le kilométrage ne peut pas être négatif."
            )

        # ====================================================
        # PROJET / DATE
        # ====================================================

        projet = None

        if self.projet_id:

            projet = self.projet

            if self.date_rapport:

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

        # ====================================================
        # CHAUFFEUR
        # ====================================================

        if self.chauffeur_id:

            chauffeur = self.chauffeur

            if chauffeur.typeTravail != "Construction":

                errors["chauffeur"] = (
                    "Le chauffeur doit appartenir "
                    "au personnel Construction."
                )

            if self.projet_id:

                affectation_chauffeur = (
                    EquipeProjet.objects
                    .filter(
                        projet_id=self.projet_id,
                        personnel_id=self.chauffeur_id,
                        fonction="CHAUFFEUR",
                        actif=True,
                    )
                    .exists()
                )

                if not affectation_chauffeur:

                    errors["chauffeur"] = (
                        "Ce personnel n'est pas affecté "
                        "comme chauffeur à ce projet."
                    )

        # ====================================================
        # VÉHICULE
        # ====================================================

        if (
            self.projet_id
            and self.vehicule_id
        ):

            affectation_vehicule = (
                VehiculeProjet.objects
                .filter(
                    projet_id=self.projet_id,
                    vehicule_id=self.vehicule_id,
                    actif=True,
                )
                .exists()
            )

            if not affectation_vehicule:

                errors["vehicule"] = (
                    "Ce véhicule n'est pas actuellement "
                    "affecté à ce projet."
                )

        # ====================================================
        # ERREURS
        # ====================================================

        if errors:
            raise ValidationError(errors)
    """
    Rapport d'état du véhicule réalisé par un chauffeur.

    Le véhicule provient de materiaux.Vehicule.
    """

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

        # ====================================================
        # KILOMÉTRAGE
        # ====================================================

        if (
            self.kilometrage is not None
            and self.kilometrage < 0
        ):
            errors["kilometrage"] = (
                "Le kilométrage ne peut pas être négatif."
            )

        # ====================================================
        # PROJET / DATE
        # ====================================================

        projet = None

        if self.projet_id:

            projet = self.projet

            if self.date_rapport:

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

        # ====================================================
        # CHAUFFEUR
        # ====================================================

        chauffeur = None

        if self.chauffeur_id:

            chauffeur = self.chauffeur

            # ------------------------------------------------
            # TYPE DE PERSONNEL
            # ------------------------------------------------

            if chauffeur.typeTravail != "Construction":

                errors["chauffeur"] = (
                    "Le chauffeur doit appartenir "
                    "au personnel Construction."
                )

            # ------------------------------------------------
            # AFFECTATION AU PROJET
            # ------------------------------------------------

            if self.projet_id:

                affectation_chauffeur = (
                    EquipeProjet.objects
                    .filter(
                        projet_id=self.projet_id,
                        personnel_id=self.chauffeur_id,
                        fonction="CHAUFFEUR",
                        actif=True,
                    )
                    .exists()
                )

                if not affectation_chauffeur:

                    errors["chauffeur"] = (
                        "Ce personnel n'est pas affecté "
                        "comme chauffeur à ce projet."
                    )

        # ====================================================
        # VÉHICULE
        # ====================================================

        if (
            self.projet_id
            and self.vehicule_id
        ):

            affectation_vehicule = (
                VehiculeProjet.objects
                .filter(
                    projet_id=self.projet_id,
                    vehicule_id=self.vehicule_id,
                    actif=True,
                )
                .exists()
            )

            if not affectation_vehicule:

                errors["vehicule"] = (
                    "Ce véhicule n'est pas actuellement "
                    "affecté à ce projet."
                )

        # ====================================================
        # ERREURS
        # ====================================================

        if errors:
            raise ValidationError(errors)
    """
    Rapport d'état du véhicule réalisé par un chauffeur.
    Le véhicule provient de materiaux.Vehicule.
    """

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
        """
        Représentation sécurisée du rapport.

        On utilise les *_id afin d'éviter les accès à une
        relation inexistante lors de la validation d'un objet
        incomplet.
        """

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
        """
        Validation complète du rapport véhicule.

        Vérifie :

        - kilométrage positif ;
        - date comprise dans la période du projet ;
        - chauffeur appartenant à Construction ;
        - chauffeur affecté au projet comme CHAUFFEUR ;
        - véhicule affecté au projet.

        Important :
        On teste toujours *_id avant d'accéder à une ForeignKey.
        """

        errors = {}

        # ====================================================
        # KILOMÉTRAGE
        # ====================================================

        if (
            self.kilometrage is not None
            and self.kilometrage < Decimal("0.00")
        ):
            errors["kilometrage"] = (
                "Le kilométrage ne peut pas être négatif."
            )

        # ====================================================
        # PROJET / DATE
        # ====================================================

        projet = None

        if self.projet_id:

            projet = self.projet

            if self.date_rapport:

                # ------------------------------------------------
                # Avant le début du projet
                # ------------------------------------------------

                if (
                    projet.date_debut
                    and self.date_rapport < projet.date_debut
                ):
                    errors["date_rapport"] = (
                        "La date du rapport ne peut pas "
                        "être avant le début du projet."
                    )

                # ------------------------------------------------
                # Après la fin du projet
                # ------------------------------------------------

                elif (
                    projet.date_fin
                    and self.date_rapport > projet.date_fin
                ):
                    errors["date_rapport"] = (
                        "La date du rapport ne peut pas "
                        "dépasser la fin du projet."
                    )

        # ====================================================
        # CHAUFFEUR
        # ====================================================

        chauffeur = None

        if self.chauffeur_id:

            chauffeur = self.chauffeur

            # ------------------------------------------------
            # Vérification du type de personnel
            # ------------------------------------------------

            if chauffeur.typeTravail != "Construction":

                errors["chauffeur"] = (
                    "Le chauffeur doit appartenir "
                    "au personnel Construction."
                )

            # ------------------------------------------------
            # Vérification de l'affectation au projet
            # ------------------------------------------------

            if self.projet_id:

                affectation_chauffeur = (
                    EquipeProjet.objects
                    .filter(
                        projet_id=self.projet_id,
                        personnel_id=self.chauffeur_id,
                        fonction="CHAUFFEUR",
                        actif=True,
                    )
                    .exists()
                )

                if not affectation_chauffeur:

                    errors["chauffeur"] = (
                        "Ce personnel n'est pas affecté "
                        "comme chauffeur à ce projet."
                    )

        # ====================================================
        # VÉHICULE
        # ====================================================

        if (
            self.projet_id
            and self.vehicule_id
        ):

            affectation_vehicule = (
                VehiculeProjet.objects
                .filter(
                    projet_id=self.projet_id,
                    vehicule_id=self.vehicule_id,
                    actif=True,
                )
                .exists()
            )

            if not affectation_vehicule:

                errors["vehicule"] = (
                    "Ce véhicule n'est pas actuellement "
                    "affecté à ce projet."
                )

        # ====================================================
        # ERREURS DE VALIDATION
        # ====================================================

        if errors:
            raise ValidationError(errors)
    """
    Rapport d'état du véhicule réalisé par un chauffeur.
    Le véhicule provient de materiaux.Vehicule.
    """

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
        return (
            f"{self.vehicule} - "
            f"{self.date_rapport} - "
            f"{self.projet.titre}"
        )

    def clean(self):
        errors = {}

        # ====================================================
        # KILOMÉTRAGE
        # ====================================================

        if (
            self.kilometrage is not None
            and self.kilometrage < 0
        ):
            errors["kilometrage"] = (
                "Le kilométrage ne peut pas être négatif."
            )

        # ====================================================
        # DATE DU RAPPORT
        # ====================================================

        if (
            self.projet_id
            and self.date_rapport
        ):
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

        # ====================================================
        # CHAUFFEUR
        # ====================================================
        if self.chauffeur_id:

            chauffeur = self.chauffeur

            # ------------------------------------------------
            # TYPE DE PERSONNEL
            # ------------------------------------------------

            if chauffeur.typeTravail != "Construction":
                errors["chauffeur"] = (
                    "Le chauffeur doit appartenir "
                    "au personnel Construction."
                )

            # ------------------------------------------------
            # AFFECTATION AU PROJET
            # ------------------------------------------------

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

        # ====================================================
        # VÉHICULE
        # ====================================================

        if (
            self.projet_id
            and self.vehicule_id
        ):

            affectation = (
                VehiculeProjet.objects
                .filter(
                    projet_id=self.projet_id,
                    vehicule_id=self.vehicule_id,
                    actif=True,
                )
                .exists()
            )

            if not affectation:
                errors["vehicule"] = (
                    "Ce véhicule n'est pas actuellement "
                    "affecté à ce projet."
                )

        # ====================================================
        # ERREURS
        # ====================================================

        if errors:
            raise ValidationError(errors)
    """
    Rapport d'état du véhicule réalisé par un chauffeur.
    Le véhicule provient de materiaux.Vehicule.
    """

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
        return (
            f"{self.vehicule} - "
            f"{self.date_rapport} - "
            f"{self.projet.titre}"
        )

    def clean(self):
        errors = {}

        # ----------------------------------------------------
        # KILOMÉTRAGE
        # ----------------------------------------------------

        if (
            self.kilometrage is not None
            and self.kilometrage < 0
        ):
            errors["kilometrage"] = (
                "Le kilométrage ne peut pas être négatif."
            )

        # ----------------------------------------------------
        # DATE
        # ----------------------------------------------------

        if self.projet and self.date_rapport:

            if self.date_rapport < self.projet.date_debut:
                errors["date_rapport"] = (
                    "La date du rapport ne peut pas "
                    "être avant le début du projet."
                )

            elif self.date_rapport > self.projet.date_fin:
                errors["date_rapport"] = (
                    "La date du rapport ne peut pas "
                    "dépasser la fin du projet."
                )

        # ----------------------------------------------------
        # CHAUFFEUR
        # ----------------------------------------------------

        if self.chauffeur:

            if self.chauffeur.typeTravail != "Construction":
                errors["chauffeur"] = (
                    "Le chauffeur doit appartenir "
                    "au personnel Construction."
                )

            if self.projet:

                affectation = EquipeProjet.objects.filter(
                    projet=self.projet,
                    personnel=self.chauffeur,
                    fonction="CHAUFFEUR",
                    actif=True,
                ).exists()

                if not affectation:
                    errors["chauffeur"] = (
                        "Ce personnel n'est pas affecté "
                        "comme chauffeur à ce projet."
                    )

        # ----------------------------------------------------
        # VÉHICULE
        # ----------------------------------------------------

        if self.projet and self.vehicule:

            affectation = VehiculeProjet.objects.filter(
                projet=self.projet,
                vehicule=self.vehicule,
                actif=True,
            ).exists()

            if not affectation:
                errors["vehicule"] = (
                    "Ce véhicule n'est pas actuellement "
                    "affecté à ce projet."
                )

        if errors:
            raise ValidationError(errors)