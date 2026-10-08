from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from users.models import AppUser
from personnel.models import Personnel


# ============================================================
# OUTILS
# ============================================================

def date_locale(valeur):
    """
    Convertit un DateTimeField en date locale.

    Evite le décalage UTC : un enregistrement tard le soir
    ne doit pas être rejeté à cause du fuseau horaire.
    Fonctionne aussi si USE_TZ = False.
    """
    if valeur is None:
        return None

    if timezone.is_aware(valeur):
        return timezone.localtime(valeur).date()

    return valeur.date()


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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_debut", "-id"]
        verbose_name = "Projet"
        verbose_name_plural = "Projets"

    def __str__(self):
        return f"{self.titre} - {self.localisation}"

    def clean(self):
        errors = {}

        # DATES
        if self.date_debut and self.date_fin:
            if self.date_fin < self.date_debut:
                errors["date_fin"] = (
                    "La date de fin doit être "
                    "postérieure ou égale à la date de début."
                )

        # BUDGET
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
# PERSONNEL D'EXÉCUTION DU PROJET
# ============================================================

class PersonnelExecutionProjet(models.Model):
    """
    Personne réellement engagée dans l'exécution d'un projet.

    Elle peut être :

    1. Un personnel de l'entreprise :
       - Ingénieur
       - Chef de chantier
       - Chauffeur
       - Chef magasinier
       - Magasinier

    2. Une personne externe intégrée temporairement au projet :
       - Chef d'équipe   (doit être rattaché à un point : EquipageProjet)
       - Conducteur d'engin
       - Minier          (doit avoir des matériaux : EquipeMateriauProjet)
       - Autre

    Une personne externe n'est donc pas obligée d'exister
    dans la table Personnel de l'entreprise.

    NB : les règles "le chef d'équipe doit avoir un point" et
    "le minier doit avoir des matériaux" ne peuvent pas être
    vérifiées dans clean() : à la création, l'objet n'a pas encore
    de pk et ses équipages / matériaux ne peuvent pas exister avant lui.
    Elles sont donc exposées via `inscription_complete` et doivent être
    imposées à la création (voir services, transaction.atomic).
    """

    TYPE_CLASS_CHOICES = [
        ("INGENIEUR", "Ingénieur Responsable de Projet"),
        ("CHEF_CHANTIER", "Chef de Chantier"),
        ("CHEF_EQUIPE", "Chef d'équipe"),
        ("CHAUFFEUR_ENGIN", "Conducteur d'engin"),
        ("CHAUFFEUR", "Chauffeur"),
        ("CHEF_MAGASIN", "Chef Magasinier"),
        ("MAGASIN", "Magasinier"),
        ("MINIER", "Minier / Mpamaky vato"),
        ("AUTRE", "Autre"),
    ]

    TYPE_CONTRAT_CHOICES = [
        ("MENSUEL", "Mensuel"),
        ("FORFAITAIRE", "Forfaitaire"),
        ("PRE_PAYER", "Pré-payé"),
    ]

    # Types qui doivent venir de la table Personnel
    TYPES_PERSONNEL = {
        "INGENIEUR",
        "CHEF_CHANTIER",
        "CHAUFFEUR",
        "CHEF_MAGASIN",
        "MAGASIN",
    }

    # Types qui peuvent être externes
    TYPES_EXTERNES = {
        "CHEF_EQUIPE",
        "CHAUFFEUR_ENGIN",
        "MINIER",
        "AUTRE",
    }

    projet = models.ForeignKey(
        Projet,
        on_delete=models.PROTECT,
        related_name="personnels_execution",
        verbose_name="Projet",
    )

    # PERSONNEL ENTREPRISE
    personnel = models.ForeignKey(
        Personnel,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="executions_projets",
        verbose_name="Personnel de l'entreprise",
    )

    # NOM
    nom = models.CharField(
        max_length=255,
        verbose_name="Nom",
    )

    # FONCTION
    type_class = models.CharField(
        max_length=30,
        choices=TYPE_CLASS_CHOICES,
        verbose_name="Fonction",
    )

    # CONTRAT
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
        verbose_name="Salaire / Montant du contrat",
    )

    # PÉRIODE
    date_debut = models.DateTimeField(
        verbose_name="Date de début",
    )

    date_fin = models.DateTimeField(
        verbose_name="Date de fin",
    )

    # PHOTO
    photo = models.ImageField(
        upload_to="images/EquipeExecution/",
        blank=True,
        null=True,
        verbose_name="Photo",
    )

    # AUDIT
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    enregistre_par = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="personnels_execution_enregistres",
        verbose_name="Enregistré par",
    )

    class Meta:
        ordering = ["date_debut", "nom"]
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

        # ----------------------------------------------------
        # PERSONNEL ENTREPRISE
        # ----------------------------------------------------

        if self.type_class in self.TYPES_PERSONNEL:

            if not self.personnel_id:
                errors["personnel"] = (
                    "Veuillez sélectionner un personnel "
                    "de l'entreprise."
                )

            else:
                personnel = self.personnel

                if personnel.typeTravail != "Construction":
                    errors["personnel"] = (
                        "Le personnel sélectionné doit "
                        "appartenir à Construction."
                    )

                else:
                    # On récupère automatiquement le nom.
                    nom_personnel = (
                        f"{personnel.nom} {personnel.prenom}"
                    ).strip()

                    if nom_personnel:
                        self.nom = nom_personnel

        # ----------------------------------------------------
        # PERSONNE EXTERNE
        # ----------------------------------------------------

        elif self.type_class in self.TYPES_EXTERNES:

            # Pour une personne externe, le FK Personnel
            # doit rester vide.
            self.personnel = None

            if not self.nom or not self.nom.strip():
                errors["nom"] = (
                    "Veuillez saisir le nom de la personne "
                    "externe au personnel de l'entreprise."
                )

        # ----------------------------------------------------
        # CONTRAT
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # SALAIRE
        # ----------------------------------------------------

        if (
            self.salaire is not None
            and self.salaire < Decimal("0.00")
        ):
            errors["salaire"] = (
                "Le salaire ou montant du contrat "
                "ne peut pas être négatif."
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
                "postérieure ou égale à la date de début."
            )

        # ----------------------------------------------------
        # LIMITES DU PROJET
        # ----------------------------------------------------

        if self.projet_id:

            projet = self.projet

            if (
                self.date_debut
                and projet.date_debut
                and date_locale(self.date_debut) < projet.date_debut
            ):
                errors["date_debut"] = (
                    "La date de début ne peut pas "
                    "être avant le début du projet."
                )

            if (
                self.date_fin
                and projet.date_fin
                and date_locale(self.date_fin) > projet.date_fin
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

        return self.date_debut <= maintenant <= self.date_fin

    @property
    def est_externe(self):
        """
        True si la personne n'est pas issue du personnel
        permanent de l'entreprise.
        """
        return self.personnel_id is None

    @property
    def inscription_complete(self):
        """
        CHEF_EQUIPE -> au moins un équipage (point de chantier).
        MINIER      -> au moins un matériau enregistré.
        Les autres types n'ont pas d'exigence supplémentaire.
        """
        if not self.pk:
            return False

        if self.type_class == "CHEF_EQUIPE":
            return self.equipages.exists()

        if self.type_class == "MINIER":
            return self.materiaux_utilises.exists()

        return True

    @property
    def element_manquant(self):
        """
        Message décrivant ce qui manque à l'inscription.
        """
        if self.inscription_complete:
            return ""

        if self.type_class == "CHEF_EQUIPE":
            return "Aucun point de chantier (équipage) enregistré."

        if self.type_class == "MINIER":
            return "Aucun matériau enregistré."

        return ""


# ============================================================
# EQUIPE DU PROJET
# ============================================================

class EquipeProjet(models.Model):
    """
    Affectation d'une personne à l'équipe du projet.

    Une personne affectée peut être :

    - un personnel de l'entreprise ;
    OU
    - une personne externe inscrite dans
      PersonnelExecutionProjet.
    """

    FONCTION_CHOICES = [
        ("INGENIEUR", "Ingénieur Responsable du Chantier"),
        ("CHEF_CHANTIER", "Chef de Chantier"),
        ("CHEF_MAGASIN", "Chef Magasinier"),
        ("MAGASINIER", "Magasinier"),
        ("CHAUFFEUR", "Chauffeur"),
        ("OUVRIER", "Ouvrier"),
        ("CHEF_EQUIPE", "Chef d'équipe"),
        ("MINIER", "Minier"),
        ("AUTRE", "Autre"),
    ]

    projet = models.ForeignKey(
        Projet,
        on_delete=models.PROTECT,
        related_name="equipe",
        verbose_name="Projet",
    )

    # PERSONNEL ENTREPRISE
    personnel = models.ForeignKey(
        Personnel,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="affectations_projets",
        verbose_name="Personnel de l'entreprise",
    )

    # PERSONNE INSCRITE POUR LE PROJET
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["projet", "fonction"]
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
            if self.fonction in {"CHEF_EQUIPE", "MINIER"}:
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

            # Correspondance fonction / inscription
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

        return self.date_debut <= aujourd_hui <= self.date_fin

    @property
    def utilisateur(self):
        if self.personnel_id:
            return getattr(self.personnel, "user", None)

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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["projet", "nom"]
        constraints = [
            models.UniqueConstraint(
                fields=["projet", "nom"],
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_rapport", "-id"]
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_debut", "-id"]
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

            if self.date_debut and self.date_debut < projet.date_debut:
                errors["date_debut"] = (
                    "La date de début du travail "
                    "ne peut pas être avant le projet."
                )

            if self.date_fin and self.date_fin > projet.date_fin:
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_ravitaillement", "-id"]
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
# VÉHICULE ROUTIER AFFECTÉ AU PROJET
# ============================================================

class VehiculeProjet(models.Model):

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

    actif = models.BooleanField(
        default=True,
        verbose_name="Affectation active",
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    updated_at = models.DateTimeField(
        auto_now=True
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

        verbose_name = (
            "Véhicule affecté au projet"
        )

        verbose_name_plural = (
            "Véhicules affectés aux projets"
        )

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
        # KILOMÉTRAGE
        # ----------------------------------------------------

        if self.kilometrage_initial < Decimal("0.00"):

            errors["kilometrage_initial"] = (
                "Le kilométrage initial "
                "ne peut pas être négatif."
            )

        if self.kilometrage_final < Decimal("0.00"):

            errors["kilometrage_final"] = (
                "Le kilométrage final "
                "ne peut pas être négatif."
            )

        if (
            self.kilometrage_final
            < self.kilometrage_initial
        ):

            errors["kilometrage_final"] = (
                "Le kilométrage final doit être "
                "supérieur ou égal au kilométrage initial."
            )

        if self.consommation_km_litre < Decimal("0.00"):

            errors["consommation_km_litre"] = (
                "La consommation ne peut pas être négative."
            )

        if errors:
            raise ValidationError(errors)

    @property
    def acces_actif(self):

        if not self.actif:
            return False

        if (
            not self.date_debut
            or not self.date_fin
        ):
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

        return (
            timezone.localdate()
            > self.date_fin
        )

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

    @property
    def unite_travail(self):

        return "km"

    @property
    def travail_total(self):

        return self.kilometres_parcourus

# ============================================================
# MOUVEMENT VÉHICULE / ENGIN
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    enregistre_par = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mouvements_vehicules_enregistres",
        verbose_name="Enregistré par",
    )

    class Meta:
        ordering = ["-date_mouvement", "-id"]
        verbose_name = "Mouvement véhicule"
        verbose_name_plural = "Mouvements véhicules"

    def __str__(self):
        return (
            f"{self.vehicule_projet.vehicule} - "
            f"{self.date_mouvement:%d/%m/%Y %H:%M}"
        )

    def clean(self):
        errors = {}

        if not self.vehicule_projet_id:
            return

        vehicule = self.vehicule_projet

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

        if self.date_mouvement:

            date_mvt = date_locale(self.date_mouvement)

            if date_mvt < vehicule.date_debut:
                errors["date_mouvement"] = (
                    "La date du mouvement est avant "
                    "le début de l'affectation."
                )

            elif date_mvt > vehicule.date_fin:
                errors["date_mouvement"] = (
                    "La date du mouvement dépasse "
                    "la fin de l'affectation."
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
            self.kilometrage_final - self.kilometrage_initial,
        )

    @property
    def heures(self):
        return max(
            Decimal("0.00"),
            self.heures_finales - self.heures_initiales,
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
                self.heures * vehicule.consommation_heure_litre
            ).quantize(Decimal("0.01"))

        if vehicule.consommation_km_litre <= Decimal("0.00"):
            return Decimal("0.00")

        return (
            self.kilometres / vehicule.consommation_km_litre
        ).quantize(Decimal("0.01"))


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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    enregistre_par = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mouvements_personnel_enregistres",
        verbose_name="Enregistré par",
    )

    class Meta:
        ordering = ["-date_mouvement", "-id"]
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

            date_mvt = date_locale(self.date_mouvement)

            if date_mvt < personnel.projet.date_debut:
                errors["date_mouvement"] = (
                    "La date du mouvement est avant "
                    "le début du projet."
                )

            elif date_mvt > personnel.projet.date_fin:
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

    Un Chef d'équipe doit avoir au moins un équipage
    (voir PersonnelExecutionProjet.inscription_complete).
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    enregistre_par = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="equipages_projet_enregistres",
        verbose_name="Enregistré par",
    )

    class Meta:
        ordering = ["-date_debut", "-id"]
        verbose_name = "Équipage du projet"
        verbose_name_plural = "Équipages du projet"

    def __str__(self):
        return f"{self.personnel_execution.nom} - {self.lieu.nom}"

    def clean(self):
        errors = {}

        # ----------------------------------------------------
        # CHEF D'ÉQUIPE
        # ----------------------------------------------------

        chef = None

        if self.personnel_execution_id:

            chef = self.personnel_execution

            if chef.type_class != "CHEF_EQUIPE":
                errors["personnel_execution"] = (
                    "La personne sélectionnée doit être "
                    "enregistrée comme Chef d'équipe."
                )

            if self.lieu_id:
                if chef.projet_id != self.lieu.projet_id:
                    errors["personnel_execution"] = (
                        "Le Chef d'équipe et le point doivent "
                        "appartenir au même projet."
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

        # ----------------------------------------------------
        # LIMITES DU PROJET
        # ----------------------------------------------------

        if chef is not None:

            projet = chef.projet

            if (
                self.date_debut
                and projet.date_debut
                and date_locale(self.date_debut) < projet.date_debut
            ):
                errors["date_debut"] = (
                    "L'équipage ne peut pas commencer "
                    "avant le début du projet."
                )

            if (
                self.date_fin
                and projet.date_fin
                and date_locale(self.date_fin) > projet.date_fin
            ):
                errors["date_fin"] = (
                    "L'équipage ne peut pas dépasser "
                    "la date de fin du projet."
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    enregistre_par = models.ForeignKey(
        AppUser,
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
        return f"{self.personnel_execution.nom} - {self.montant}"

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
    """
    Matériaux remis / utilisés par un Minier.

    Un Minier doit avoir au moins un enregistrement ici
    (voir PersonnelExecutionProjet.inscription_complete).
    """

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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    enregistre_par = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="materiaux_equipe_enregistres",
        verbose_name="Enregistré par",
    )

    class Meta:
        ordering = ["-date_debut", "-id"]
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

        # Seul un Minier peut recevoir des matériaux
        if (
            self.personnel_execution_id
            and self.personnel_execution.type_class != "MINIER"
        ):
            errors["personnel_execution"] = (
                "La personne doit être enregistrée comme Minier."
            )

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
            self.quantite * self.prix_unitaire
        ).quantize(Decimal("0.01"))


# ============================================================
# ACTIVITÉ TRANSPORT DU PROJET
# ============================================================

class ActiviteTransportProjet(models.Model):

    TYPE_TRANSPORT_CHOICES = [
        ("MATERIAUX", "Matériaux"),
        ("MATERIEL", "Matériel"),
        ("PERSONNEL", "Personnel"),
        ("MATERIAUX_MATERIEL", "Matériaux + Matériel"),
        ("AUTRE", "Autre"),
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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_transport", "-id"]
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

                affectation = EquipeProjet.objects.filter(
                    projet_id=self.projet_id,
                    personnel_id=self.chauffeur_id,
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

        if self.projet_id and self.vehicule_id:

            affectation = VehiculeProjet.objects.filter(
                projet_id=self.projet_id,
                vehicule=str(self.vehicule),
                actif=True,
            ).exists()

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
            self.kilometrage_final - self.kilometrage_initial,
        )

    @property
    def carburant_estime(self):
        if (
            not self.consommation_km_litre
            or self.consommation_km_litre <= Decimal("0.00")
        ):
            return Decimal("0.00")

        return (
            self.kilometres_parcourus / self.consommation_km_litre
        ).quantize(Decimal("0.01"))


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

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_rapport", "-id"]
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

        return f"{vehicule} - {self.date_rapport} - {projet}"

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

                affectation = EquipeProjet.objects.filter(
                    projet_id=self.projet_id,
                    personnel_id=self.chauffeur_id,
                    fonction="CHAUFFEUR",
                    actif=True,
                ).exists()

                if not affectation:
                    errors["chauffeur"] = (
                        "Ce personnel n'est pas affecté "
                        "comme chauffeur à ce projet."
                    )

        if self.projet_id and self.vehicule_id:

            affectation = VehiculeProjet.objects.filter(
                projet_id=self.projet_id,
                vehicule=str(self.vehicule),
                actif=True,
            ).exists()

            if not affectation:
                errors["vehicule"] = (
                    "Ce véhicule n'est pas actuellement "
                    "affecté à ce projet."
                )

        if errors:
            raise ValidationError(errors)