from decimal import Decimal

from django.db import models
from django.db.models import Sum

from personnel.models import Personnel
from avances.models import Avance


class Salaire(models.Model):
    class Meta:
        app_label = 'salaire'
        ordering = ['-date', '-created_at']
        verbose_name = 'Salaire'
        verbose_name_plural = 'Salaires'

    personnel = models.ForeignKey(Personnel, on_delete=models.SET_NULL, null=True, blank=True, related_name='salaires')
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    reste = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        target = self.personnel or 'Sans personnel'
        return f"{target} - {self.montant}"

    def calculate_reste(self):
        """Compute reste = montant - sum(avances for this personnel)."""
        if not self.personnel:
            return self.montant or Decimal('0')

        total = Avance.objects.filter(personnel=self.personnel).aggregate(total=Sum('montantAv'))['total']
        if total is None:
            total = Decimal('0')

        # Ensure Decimal arithmetic
        montant = self.montant or Decimal('0')
        return montant - total

    def save(self, *args, **kwargs):
        # Always compute reste from advances when personnel is provided
        try:
            self.reste = self.calculate_reste()
        except Exception:
            # In case migrations or DB not ready, fallback to provided value
            pass
        super().save(*args, **kwargs)