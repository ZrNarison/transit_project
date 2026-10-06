from decimal import Decimal

from django.db import models
from django.db.models import Sum
from personnel.models import Personnel
from transentrant.models import Transentrant

class Depot(models.Model):

    montantG = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        default=0
    )

    deposant = models.CharField(
        max_length=50,
        default="BANK",
        editable=False
    )

    nom = models.CharField(
        max_length=150,
        blank=True,
        default="Dépôt"
    )

    montant = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    personnel_1 = models.ForeignKey(
        Personnel,
        on_delete=models.SET_NULL,
        related_name="depots_personnel_1",
        null=True,
        blank=True
    )

    personnel_2 = models.ForeignKey(
        Personnel,
        on_delete=models.SET_NULL,
        related_name="depots_personnel_2",
        null=True,
        blank=True
    )

    part_1 = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    part_2 = models.PositiveIntegerField(
        null=True,
        blank=True
    )

    date = models.DateField(
        auto_now_add=True
    )

    description = models.TextField(
        blank=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )


    class Meta:
        ordering = [
            "-date",
            "-created_at"
        ]
        verbose_name = "Dépôt"
        verbose_name_plural = "Dépôts"


    def total_distribue(self):

        return sum(
            (
                d.montant
                for d in self.distributions.all()
            ),
            Decimal("0")
        )


    def reste(self):

        return self.montantG - self.total_distribue()


    @property
    def montant_reparti_1(self):

        if not self.part_1 or not self.part_2:
            return None

        return (
            self.montant *
            Decimal(self.part_1) /
            Decimal(self.part_1+self.part_2)
        ).quantize(
            Decimal("0.01")
        )


    @property
    def montant_reparti_2(self):

        if not self.part_1 or not self.part_2:
            return None

        return (
            self.montant *
            Decimal(self.part_2) /
            Decimal(self.part_1+self.part_2)
        ).quantize(
            Decimal("0.01")
        )


    def __str__(self):

        return f"Dépôt {self.montantG} Ar"




class Distribution(models.Model):

    depot = models.ForeignKey(
        Depot,
        on_delete=models.CASCADE,
        related_name="distributions"
    )


    distributeur = models.ForeignKey(
        Personnel,
        on_delete=models.CASCADE,
        related_name="distributions_recues"
    )

    vehicule = models.ForeignKey(
        Transentrant,
        on_delete=models.SET_NULL,
        related_name="distributions",
        null=True,
        blank=True
    )

    montant = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        default=0
    )


    @property
    def montant_depenses(self):

        return self.depenses.aggregate(
            total=Sum("montant")
        )["total"] or Decimal("0")


    @property
    def montant_produits(self):

        return self.paiements_produits.aggregate(
            total=Sum("montant")
        )["total"] or Decimal("0")


    @property
    def montant_avances(self):

        return self.avances.aggregate(
            total=Sum("montantAv")
        )["total"] or Decimal("0")


    @property
    def solde(self):

        return (
            self.montant
            - self.montant_depenses
            - self.montant_avances
            - self.montant_produits
        )


    def __str__(self):

        return (
            f"{self.distributeur} - "
            f"{self.montant} Ar"
        )