from decimal import Decimal

from django.db import models

from depot.models import Distribution



class Depense(models.Model):

    class Meta:

        ordering = [
            '-date',
            '-created_at'
        ]

        verbose_name = "Dépense"
        verbose_name_plural = "Dépenses"



    titre = models.CharField(
        max_length=150
    )


    # La dépense vient de l'argent reçu par un distributeur
    distribution = models.ForeignKey(
        Distribution,
        on_delete=models.CASCADE,
        related_name="depenses"
    )


    montant = models.DecimalField(
        max_digits=12,
        decimal_places=2
    )


    description = models.TextField(
        blank=True
    )


    date = models.DateField(
        auto_now_add=True
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )



    def __str__(self):

        return (
            f"{self.titre} - "
            f"{self.montant} Ar"
        )