from django.db import models
from users.models import AppUser


class Transentrant(models.Model):

    chauffeur = models.CharField(max_length=100)
    cin = models.CharField(max_length=12,blank=True,unique=True)
    num_vehicule = models.CharField(max_length=8,unique=True)
    permis = models.CharField(max_length=50,blank=True)
    telephone = models.CharField(max_length=10)
    adresse = models.TextField(blank=True)
    photo = models.ImageField(
        upload_to="images/transentrants/",
        blank=True,
        null=True
    )
    created_by = models.ForeignKey(
        AppUser,
        on_delete=models.PROTECT,
        related_name="transentrants",
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(
        auto_now_add=True
    )
    def __str__(self):

        return f"{self.chauffeur.upper()} - {self.num_vehicule.upper()}"