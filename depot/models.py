from django.db import models


class Depot(models.Model):
    class Meta:
        app_label = 'depot'
        ordering = ['-date', '-created_at']
        verbose_name = 'Dépôt'
        verbose_name_plural = 'Dépôts'

    nom = models.CharField(max_length=150)
    montant = models.DecimalField(max_digits=12, decimal_places=2)
    date = models.DateField(auto_now_add=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nom
