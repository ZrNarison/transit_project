from django.db import models

from users.models import AppUser, H_AppUser


class DepotSoc(models.Model):

    montant = models.DecimalField(max_digits=50, decimal_places=2)

    date = models.DateField()

    date_enregistrement = models.DateTimeField(auto_now_add=True)

    enregistreur = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="depots_soc_enregistres",
    )

    def __str__(self):
        return f"{self.montant} Ar - {self.date}"


class H_DepotSoc(models.Model):
    montant = models.DecimalField(max_digits=50, decimal_places=2)
    date = models.DateField()
    date_enregistrement = models.DateTimeField(auto_now_add=True)

    enregistreur = models.ForeignKey(
        H_AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="h_depots_soc_enregistres",
    )

    def __str__(self):
        return f"{self.montant} Ar - {self.date}"