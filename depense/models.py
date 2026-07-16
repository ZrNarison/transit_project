from django.db import models


class Depense(models.Model):
    class Meta:
        app_label = 'depense'
        ordering = ['-date', '-created_at']
        verbose_name = 'Dépense'
        verbose_name_plural = 'Dépenses'

    titre = models.CharField(max_length=150)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.TextField(blank=True)
    date = models.DateField(auto_now_add=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titre
