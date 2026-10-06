from django.db import models
from users.models import AppUser


class Entretien(models.Model):

    num_vehicule = models.CharField(
        max_length=8,
        verbose_name="Numéro véhicule"
    )

    piece_acheter = models.CharField(
        max_length=150,
        verbose_name="Pièce achetée"
    )

    nombre = models.PositiveIntegerField(
        default=1,
        verbose_name="Nombre"
    )

    prix_du_piece = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Prix de la pièce"
    )

    observation = models.TextField(
            blank=True,
            null=True
        )

    date_cree = models.DateField(
        auto_now_add=True,
        verbose_name="Date création"
    )

    enregistrer_par = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="entretiens",
        verbose_name="Enregistré par"
    )


    def __str__(self):
        return f"{self.num_vehicule} - {self.piece_acheter}"