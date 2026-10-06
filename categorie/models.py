from django.db import models


class Categorie(models.Model):

    nom = models.CharField(
        max_length=100,
        unique=True
    )


    description = models.TextField(
        max_length=500,
        blank=True,
        null=True
    )


    created_at = models.DateTimeField(
        auto_now_add=True
    )


    updated_at = models.DateTimeField(
        auto_now=True
    )


    def __str__(self):
        return self.nom