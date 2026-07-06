from django.db import models
from clients.models import Client


class CompteBancaire(models.Model):

    client = models.ForeignKey(Client, on_delete=models.CASCADE)

    nom_banque = models.CharField(
        max_length=100
    )

    numero_compte = models.CharField(
        max_length=50,
        unique=True
    )

    titulaire = models.CharField(
        max_length=150,
        blank=True
    )

    code_banque = models.CharField(
        max_length=20,
        blank=True
    )

    agence = models.CharField(
        max_length=100,
        blank=True
    )

    iban = models.CharField(
        max_length=50,
        blank=True
    )

    swift_bic = models.CharField(
        max_length=20,
        blank=True
    )

    principal = models.BooleanField(
        default=False
    )

    actif = models.BooleanField(
        default=True
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["nom_banque", "numero_compte"]

    def __str__(self):
        return f"{self.client} - {self.nom_banque} ({self.numero_compte})"