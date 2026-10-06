from django.db import models
from personnel.models import Personnel


class AppUser(models.Model):

    ROLE_CHOICES = [
            ("Admin", "Administrateur"),
            ("ChauffeurEntreprise", "Chauffeur Entreprise"),
            ("ChauffeurMica", "Chauffeur Mica"),
            ("ChefMagasin", "Chef Magasiné"),
            ("Magasin", "Magasiné"),
            ("Superviseur", "Superviseur"),
            ("UserMica", "Comptable Mica"),
            ("UserEntreprise", "Comptable Entreprise"),
            ("UserProjet", "Utilisateur Projet"),        
    ]

    personnel = models.OneToOneField(
        Personnel,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="user"
    )

    username = models.CharField(
        max_length=100,
        unique=True
    )

    email = models.EmailField(
        blank=True,
        null=True
    )

    password = models.CharField(
        max_length=255
    )

    role = models.CharField(
        max_length=50,
        choices=ROLE_CHOICES,
        default="UserMica"
    )

    photo = models.ImageField(
        upload_to="images/users/",
        blank=True,
        null=True
    )

    date_creation = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return self.username

    # =========================================================
    # TYPE DE TRAVAIL DU PERSONNEL
    # =========================================================

    @property
    def type_travail(self):
        """
        Retourne le typeTravail du personnel lié.
        Exemple : Mica ou Construction.
        """
        if self.personnel:
            return self.personnel.typeTravail
        return None

    # =========================================================
    # LIMITES
    # =========================================================

    @classmethod
    def limite_role(cls, role):
        """
        Retourne la limite maximale pour un rôle.
        """

        limites = {
            "Admin": 2,
            "UserMica": 10,
            "UserEntreprise": 10,
        }

        return limites.get(role)

    @classmethod
    def limite_superviseur(cls, type_travail):
        """
        Limite des superviseurs par type de travail.
        2 Mica + 2 Construction.
        """

        if type_travail in ["Mica", "Construction"]:
            return 2

        return 0
