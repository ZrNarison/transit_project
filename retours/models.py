from django.db import models

from clients.models import Client
from users.models import AppUser



class Retour(models.Model):


    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="retours"
    )


    montant = models.DecimalField(
        max_digits=15,
        decimal_places=0
    )


    motif = models.CharField(
        max_length=255,
        default="Remboursement avance client"
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    enregistrer_par = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="retours_enregistres"
    )


    def __str__(self):

        if self.client:

            return (
                f"{self.client.nom} "
                f"- {self.montant} Ar"
            )

        return f"Retour {self.montant} Ar"