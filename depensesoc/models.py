from django.db import models
from django.utils import timezone

from users.models import AppUser


class DepenseSoc(models.Model):

    titre = models.CharField(
        max_length=50
    )

    montant = models.DecimalField(
        max_digits=50,
        decimal_places=0
    )

    description = models.TextField(
        blank=True,
        null=True
    )

    # Date saisie par l'utilisateur
    date = models.DateField(
        default=timezone.now
    )

    # Date et heure réelle de création
    created_at = models.DateTimeField(
        auto_now_add=True
    )

    # Utilisateur qui a enregistré la dépense
    enregistre_par = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="depenses_soc_enregistrees"
    )

    class Meta:
        ordering = ["-date", "-created_at"]
        verbose_name = "Dépense Soc"
        verbose_name_plural = "Dépenses Soc"

    def __str__(self):
        return f"{self.titre} - {self.montant} Ar"
