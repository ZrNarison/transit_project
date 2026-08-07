from django.db import models

from personnel.models import Personnel
from users.models import AppUser


class Avance(models.Model):

    TYPE_AVANCE = [
        ("ESPECE", "Espèce"),
        ("CHEQUE", "Chèque"),
        ("MOBILE_MONEY", "Mobile Money"),
    ]


    # Bénéficiaire personnel
    personnel = models.ForeignKey(
        Personnel,
        on_delete=models.CASCADE,
        related_name="avances",
        null=True,
        blank=True
    )


    # Distribution concernée
    distribution = models.ForeignKey(
        "depot.Distribution",
        on_delete=models.CASCADE,
        related_name="avances",
        null=True,
        blank=True
    )


    motifAv = models.CharField(
        max_length=255
    )


    montantAv = models.DecimalField(
        max_digits=12,
        decimal_places=0
    )


    typeAv = models.CharField(
        max_length=20,
        choices=TYPE_AVANCE,
        default="ESPECE"
    )


    dateAv = models.DateTimeField(
        auto_now_add=True
    )


    enregistre_par = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="avances_enregistrees"
    )


    def __str__(self):

        if self.personnel:

            return (
                f"{self.personnel.nom} "
                f"{self.personnel.prenom} - "
                f"{self.montantAv} Ar"
            )

        return f"Avance {self.montantAv} Ar"