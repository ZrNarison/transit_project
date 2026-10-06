from django.db import models
from users.models import AppUser


class VehiculeSortant(models.Model):
    chauffeur = models.CharField(max_length=100)
    cin = models.CharField(max_length=12)
    num_vehicule = models.CharField(max_length=8)
    permis = models.CharField(max_length=50)
    telephone = models.CharField(max_length=10)
    adresse = models.TextField(blank=True)
    remorque = models.CharField(max_length=50, blank=True, null=True)
    montant = models.DecimalField(max_digits=15,decimal_places=0,default=0)
    ticket = models.CharField(max_length=5,unique=True)
    photo = models.ImageField(upload_to='images/vehicules_sortants/', blank=True, null=True)
    created_by = models.ForeignKey(AppUser, on_delete=models.PROTECT, related_name='vehicules_sortants', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Véhicule sortant'
        verbose_name_plural = 'Véhicules sortants'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.chauffeur.upper()} - {self.num_vehicule.upper()}"
