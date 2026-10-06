from decimal import Decimal

from django.db import models
from django.db.models import Sum

from personnel.models import Personnel
from users.models import AppUser


class Avance(models.Model):

    TYPE_AVANCE = [
        ("ESPECE", "Espèce"),
        ("CHEQUE", "Chèque"),
        ("MOBILE_MONEY", "Mobile Money"),
    ]

    # =========================================================
    # PERSONNEL
    # =========================================================

    personnel = models.ForeignKey(
        Personnel,
        on_delete=models.CASCADE,
        related_name="avances",
        null=True,
        blank=True
    )

    # =========================================================
    # DISTRIBUTION
    # =========================================================

    distribution = models.ForeignKey(
        "depot.Distribution",
        on_delete=models.CASCADE,
        related_name="avances",
        null=True,
        blank=True
    )

    # =========================================================
    # MOTIF
    # =========================================================

    motifAv = models.CharField(
        max_length=255
    )

    # =========================================================
    # MONTANT INITIAL
    # =========================================================

    montantAv = models.DecimalField(
        max_digits=12,
        decimal_places=0
    )

    # =========================================================
    # MONTANT DÉJÀ RÉCUPÉRÉ
    # =========================================================

    montant_recupere = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0")
    )

    # =========================================================
    # RESTE DE L'AVANCE
    # =========================================================

    reste = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=Decimal("0")
    )

    # =========================================================
    # TYPE
    # =========================================================

    typeAv = models.CharField(
        max_length=20,
        choices=TYPE_AVANCE,
        default="ESPECE"
    )

    # =========================================================
    # DATE
    # =========================================================

    dateAv = models.DateField()

    dateEnregistremeny = models.DateTimeField(
        auto_now_add=True
    )

    # =========================================================
    # ENREGISTREUR
    # =========================================================

    enregistre_par = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="avances_enregistrees"
    )

    # =========================================================
    # CALCUL DU RESTE
    # =========================================================

    def recalculer_reste(self):
        """
        Calcule le montant réellement récupéré sur les salaires.
        """

        total = self.affectations_salaires.aggregate(
            total=Sum("montant")
        )["total"]

        total = total or Decimal("0")

        montant = Decimal(str(self.montantAv or 0))

        self.montant_recupere = total

        reste = montant - total

        if reste < Decimal("0"):
            reste = Decimal("0")

        self.reste = reste

        Avance.objects.filter(
            pk=self.pk
        ).update(
            montant_recupere=self.montant_recupere,
            reste=self.reste
        )

        return self.reste

    # =========================================================
    # SAVE
    # =========================================================

    def save(self, *args, **kwargs):

        if self._state.adding:
            self.reste = Decimal(
                str(self.montantAv or 0)
            )

        super().save(*args, **kwargs)

    # =========================================================
    # AFFICHAGE
    # =========================================================

    def __str__(self):

        if self.personnel:
            return (
                f"{self.personnel.nom} "
                f"{self.personnel.prenom} - "
                f"{self.montantAv} Ar"
            )

        return f"Avance {self.montantAv} Ar"