from django.db import models

from personnel.models import Personnel, H_Personnel


# ============================================================
# UTILISATEUR PRINCIPAL
# Source : Personnel
# ============================================================
class AppUser(models.Model):

    ROLE_CHOICES = [
        ("Admin", "Administrateur"),
        ("ChauffeurEntreprise", "Chauffeur Entreprise"),
        ("ChauffeurMica", "Chauffeur Mica"),
        ("ChefMagasin", "Chef Magasiné"),
        ("Magasin", "Magasiné"),
        ("SuperviseurMica", "Superviseur Mica"),
        ("SuperviseurEntreprise", "Superviseur Entreprise"),
        ("UserMica", "Comptable Mica"),
        ("UserEntreprise", "Comptable Entreprise"),
        ("UserProjet", "Utilisateur Projet"),
    ]

    personnel = models.OneToOneField(
        Personnel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user",
        verbose_name="Personnel",
    )

    username = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nom d'utilisateur",
    )

    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Adresse e-mail",
    )

    password = models.CharField(
        max_length=255,
        verbose_name="Mot de passe",
    )

    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default="UserMica",
        verbose_name="Rôle",
    )

    photo = models.ImageField(
        upload_to="images/users/",
        blank=True,
        null=True,
        verbose_name="Photo",
    )

    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création",
    )

    def __str__(self):
        return self.username

    @property
    def type_travail(self):
        """Retourne le type de travail du personnel associé."""
        if self.personnel_id:
            return self.personnel.typeTravail
        return None

    @classmethod
    def limite_role(cls, role):
        limites = {
            "Admin": 2,
            "UserMica": 10,
            "UserEntreprise": 10,
        }
        return limites.get(role)

    @classmethod
    def limite_superviseur(cls, type_travail):
        if type_travail in ("Mica", "Construction"):
            return 2
        return 0


# ============================================================
# UTILISATEUR H
# Source : H_Personnel
# ============================================================
class H_AppUser(models.Model):

    ROLE_CHOICES = [
        ("Dir", "Administrateur"),
        ("Compta", "Comptable"),
    ]

    personnel = models.OneToOneField(
        H_Personnel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="historique_user",
        verbose_name="Personnel H",
    )

    username = models.CharField(
        max_length=100,
        unique=True,
        verbose_name="Nom d'utilisateur",
    )

    email = models.EmailField(
        blank=True,
        null=True,
        verbose_name="Adresse e-mail",
    )

    password = models.CharField(
        max_length=255,
        verbose_name="Mot de passe",
    )

    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default="Compta",
        verbose_name="Rôle",
    )

    photo = models.ImageField(
        upload_to="images/users/",
        blank=True,
        null=True,
        verbose_name="Photo",
    )

    date_creation = models.DateTimeField(
        auto_now_add=True,
        verbose_name="Date de création",
    )

    def __str__(self):
        return self.username

    @property
    def type_travail(self):
        """Retourne le type de travail du personnel H associé."""
        if self.personnel_id:
            return self.personnel.typeTravail
        return None
