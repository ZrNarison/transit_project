from decimal import Decimal
from django.db import models
from django.db.models import Sum
from personnel.models import Personnel


class Depot(models.Model):

    class Meta:
        ordering = ['-date', '-created_at']
        verbose_name = "Dépôt"
        verbose_name_plural = "Dépôts"


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


    date = models.DateField(
        auto_now_add=True
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    def total_distribue(self):
        return sum(
            (distribution.montant for distribution in self.distributions.all()),
            Decimal('0')
        )


    def reste(self):
        return self.montantG - self.total_distribue()


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
        return f"{self.distributeur} - {self.montant} Ar"