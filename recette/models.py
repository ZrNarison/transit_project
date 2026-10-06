from django.db import models

from users.models import AppUser


class Recette(models.Model):

    TYPE_VIREMENT_CHOICES = [
        ("Banque", "Virement bancaire"),
        ("Cheque", "Chèque"),
        ("Espece", "Espèces"),
        ("Mobile", "Mobile money"),
    ]

    montant = models.DecimalField(
        max_digits=50,
        decimal_places=2
    )

    type_virement = models.CharField(
        max_length=100,
        choices=TYPE_VIREMENT_CHOICES
    )

    date = models.DateField()

    source = models.CharField(
        max_length=100
    )

    date_enregistrement = models.DateTimeField(
        auto_now_add=True
    )

    enregistreur = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recettes_enregistrees"
    )

    def __str__(self):
        return f"{self.montant} Ar - {self.source}"
