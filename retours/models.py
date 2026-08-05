from django.db import models
from users.models import AppUser


class Retour(models.Model):

    montant = models.DecimalField(
        max_digits=10,
        decimal_places=0
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
        return f"{self.montant} Ar"