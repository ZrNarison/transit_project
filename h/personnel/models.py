from django.db import models
from categorie.models import h_Categorie


class h_Personnel(models.Model):

    TYPE_CONTRAT_CHOICES = [
        ("CDI", "CDI"),
        ("CDD", "CDD"),
        ("Journalier", "Journalier"),
        ("Stage", "Stage"),
    ]

    nom = models.CharField(
        max_length=100
    )

    prenom = models.CharField(
        max_length=100,
        blank=True
    )

    adresse = models.TextField(
        blank=True
    )

    telephone = models.CharField(
        max_length=10
    )

    psalaire = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    fonction = models.CharField(
        max_length=50,
        default="Employé"
    )

    typeTravail = models.CharField(
        max_length=30,
        choices=TYPE_TRAVAIL_CHOICES,
        default="Construction"
    )

    typeContrat = models.CharField(
        max_length=30,
        choices=TYPE_CONTRAT_CHOICES,
        default="CDI"
    )

    debutContrat = models.DateField()

    finContrat = models.DateField(
        null=True,
        blank=True
    )

    lieuTravail = models.CharField(
        max_length=100,
        blank=True
    )

    categorie = models.ForeignKey(
        Categorie,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="personnels"
    )

    photo = models.ImageField(
        upload_to="images/Personnel/",
        blank=True,
        null=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return " ".join(
            filter(
                None,
                [
                    self.nom.upper(),
                    self.prenom.title() if self.prenom else ""
                ]
            )
        )
