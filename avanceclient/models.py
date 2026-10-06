from decimal import Decimal

from django.db import models

from clients.models import Client
from users.models import AppUser


class AvanceClient(models.Model):

    TYPE_AVANCE = [
        ("ESPECE", "Espèce"),
        ("CHEQUE", "Chèque"),
        ("MOBILE_MONEY", "Mobile Money"),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="avances_client"
    )

    montant = models.DecimalField(
        max_digits=15,
        decimal_places=0
    )

    # Montant utilisé pour payer les produits
    montant_utilise = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        default=Decimal("0")
    )

    # Montant remboursé au client
    montant_retour = models.DecimalField(
        max_digits=15,
        decimal_places=0,
        default=Decimal("0")
    )

    type_avance = models.CharField(
        max_length=20,
        choices=TYPE_AVANCE,
        default="ESPECE"
    )

    motif = models.CharField(
        max_length=255,
        default="Avance client"
    )

    date = models.DateTimeField(
        auto_now_add=True
    )

    enregistrer_par = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="avances_client_enregistrees"
    )

    @property
    def reste(self):
        return (
            self.montant
            - self.montant_utilise
            - self.montant_retour
        )

    @property
    def est_soldee(self):
        return self.reste <= 0

    class Meta:
        ordering = ["date", "id"]
        verbose_name = "Avance client"
        verbose_name_plural = "Avances clients"

    def __str__(self):
        return (
            f"{self.client.nom.upper()} "
            f"{self.client.prenom.title()} "
            f"- Reste : {self.reste} Ar"
        )


class UtilisationAvanceClient(models.Model):

    avance = models.ForeignKey(
        AvanceClient,
        on_delete=models.CASCADE,
        related_name="utilisations"
    )

    produit = models.ForeignKey(
        "produit.Produit",
        on_delete=models.CASCADE,
        related_name="utilisations_avance"
    )

    montant = models.DecimalField(
        max_digits=15,
        decimal_places=0
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["created_at", "id"]
        verbose_name = "Utilisation d'avance client"
        verbose_name_plural = "Utilisations d'avances clients"

    def __str__(self):
        return (
            f"{self.avance.client.nom.upper()} "
            f"- Produit #{self.produit.id} "
            f"- {self.montant} Ar"
        )