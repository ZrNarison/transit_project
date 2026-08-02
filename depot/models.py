from decimal import Decimal

from django.db import models

from personnel.models import Personnel


class Depot(models.Model):
    class Meta:
        app_label = 'depot'
        ordering = ['-date', '-created_at']
        verbose_name = 'Dépôt'
        verbose_name_plural = 'Dépôts'

    nom = models.CharField(max_length=150)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    personnel_1 = models.ForeignKey(
        Personnel,
        on_delete=models.SET_NULL,
        related_name='depots_personnel_1',
        null=True,
        blank=True,
    )
    personnel_2 = models.ForeignKey(
        Personnel,
        on_delete=models.SET_NULL,
        related_name='depots_personnel_2',
        null=True,
        blank=True,
    )
    part_1 = models.PositiveIntegerField(null=True, blank=True)
    part_2 = models.PositiveIntegerField(null=True, blank=True)
    date = models.DateField(auto_now_add=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def montant_reparti_1(self):
        if self.part_1 is None or self.part_2 is None or self.part_1 == 0 or self.part_2 == 0:
            return None
        return (self.montant * Decimal(self.part_1) / Decimal(self.part_1 + self.part_2)).quantize(Decimal('0.01'))

    @property
    def montant_reparti_2(self):
        if self.part_1 is None or self.part_2 is None or self.part_1 == 0 or self.part_2 == 0:
            return None
        return (self.montant * Decimal(self.part_2) / Decimal(self.part_1 + self.part_2)).quantize(Decimal('0.01'))

    def __str__(self):
        return self.nom
