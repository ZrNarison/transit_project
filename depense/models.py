from django.db import models
from users.models import AppUser
from depot.models import Distribution


class Depense(models.Model):

    titre = models.CharField(
        max_length=150
    )


    distribution = models.ForeignKey(
        Distribution,
        on_delete=models.PROTECT,
        related_name="depenses",
        null=True,
        blank=True
    )


    montant = models.DecimalField(
        max_digits=12,
        decimal_places=0
    )


    description = models.TextField(
        blank=True,
        null=True
    )


    date = models.DateField(
        auto_now_add=True
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    enregistre_par = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="depenses_enregistrees"
    )


    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = "Dépense"
        verbose_name_plural = "Dépenses"


    def __str__(self):
        return f"{self.titre} - {self.montant} Ar"