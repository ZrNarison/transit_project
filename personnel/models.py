from django.db import models
from categorie.models import Categorie


class Personnel(models.Model):

    nom = models.CharField(max_length=100)

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

    debutContrat = models.DateField()

    categorie = models.ForeignKey(
    Categorie,
    on_delete=models.CASCADE,
    null=True,
    blank=True,
    related_name="personnels"
)

    photo = models.ImageField(
        upload_to='images/Personnel/',
        blank=True,
        null=True
    )


    def __str__(self):
        return " ".join(
            filter(
                None,
                [
                    self.nom.upper(),
                    self.prenom.title()
                ]
            )
        )