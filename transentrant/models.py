from django.db import models
from users.models import AppUser


class Transentrant(models.Model):

    chauffeur = models.CharField(
        max_length=100
    )

    cin = models.CharField(
        max_length=12
    )

    num_vehicule = models.CharField(
        max_length=8
    )

    permis = models.CharField(
        max_length=50
    )

    telephone = models.CharField(
        max_length=10
    )

    adresse = models.TextField()


    photo = models.ImageField(
        upload_to="transentrant/",
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
        return self.chauffeur