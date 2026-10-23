from django.db import models

from categorie.models import Categorie


class Personnel(models.Model):

    TYPE_TRAVAIL_CHOICES = [
        ("Mica", "Mica"),
        ("Construction", "Construction"),
    ]

    TYPE_CONTRAT_CHOICES = [
        ("CDI", "CDI"),
        ("CDD", "CDD"),
        ("Journalier", "Journalier"),
        ("Stage", "Stage"),
    ]

    nom = models.CharField(max_length=100)

    prenom = models.CharField(max_length=100, blank=True)

    adresse = models.TextField(blank=True)

    telephone = models.CharField(max_length=10)

    psalaire = models.DecimalField(max_digits=10, decimal_places=2)

    fonction = models.CharField(max_length=50, default="Employé")

    typeTravail = models.CharField(
        max_length=30, choices=TYPE_TRAVAIL_CHOICES, default="Construction"
    )

    typeContrat = models.CharField(
        max_length=30, choices=TYPE_CONTRAT_CHOICES, default="CDI"
    )

    debutContrat = models.DateField()

    finContrat = models.DateField(null=True, blank=True)

    lieuTravail = models.CharField(max_length=100, blank=True)

    categorie = models.ForeignKey(
        Categorie,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="personnels",
    )

    photo = models.ImageField(upload_to="images/Personnel/", blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return " ".join(
            filter(None, [self.nom.upper(), self.prenom.title() if self.prenom else ""])
        )


class H_Personnel(models.Model):

    TYPE_CONTRAT_CHOICES = [
        ("CDI", "CDI"),
        ("CDD", "CDD"),
        ("Journalier", "Journalier"),
        ("Stage", "Stage"),
    ]
    CATEGORIES_CHOICES = [
        ("DIRECTEUR", "Directeur"),
        ("COMPTABLE", "Comptable"),
        ("CHAFFEUR", "Chauffeur"),
        ("MANOEUVRE", "Manoeuvre"),
        ("MACON", "Maçon"),
        ("ELECTRICIEN", "Eléctricien"),
        ("MPIASA", "Employé"),
    ]

    nom = models.CharField(
        max_length=100,
        verbose_name="Nom",
    )

    prenom = models.CharField(
        max_length=100,
        blank=True,
        verbose_name="Prénom",
    )

    adresse = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Adresse",
    )

    salaire = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name="Salaire",
    )

    cin = models.CharField(
        max_length=12,
        unique=True,
        verbose_name="CIN",
    )

    telephone = models.CharField(
        max_length=10,
        verbose_name="Téléphone",
    )

    typeContrat = models.CharField(
        max_length=30,
        choices=TYPE_CONTRAT_CHOICES,
        default="CDI",
        verbose_name="Type de contrat",
    )

    debutContrat = models.DateField(
        verbose_name="Début du contrat",
    )

    finContrat = models.DateField(
        null=True,
        blank=True,
        verbose_name="Fin du contrat",
    )

    categorie = models.CharField(
        max_length=30,
        choices=CATEGORIES_CHOICES,
        default="MPIASA",
        verbose_name="Catégorie",
    )

    class Meta:
        ordering = ["nom", "prenom"]
        verbose_name = "Personnel"
        verbose_name_plural = "Personnels"

    def __str__(self):
        return f"{self.nom} {self.prenom}".strip()
