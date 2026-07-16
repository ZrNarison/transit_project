from django.db import models

from personnel.models import Personnel


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