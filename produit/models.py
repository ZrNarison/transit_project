from decimal import Decimal
from django.db import models
from clients.models import Client
from transentrant.models import Transentrant
from depot.models import Distribution
from users.models import AppUser


class Produit(models.Model):

    TYPE_CHOICES = [
        ("ESPECE", "Espèce"),
        ("CHEQUE", "Chèque"),
        ("MOBILE_MONEY", "Mobile Money"),
    ]

    client = models.ForeignKey(
        Client,
        on_delete=models.CASCADE,
        related_name="produits"
    )

    vehicule = models.ForeignKey(
        Transentrant,
        on_delete=models.CASCADE,
        related_name="produits"
    )

    source = models.CharField(
        max_length=100
    )

    type_produit = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default="ESPECE"
    )

    montant = models.DecimalField(
        max_digits=15,
        decimal_places=0
    )

    quantite = models.DecimalField(
        max_digits=15,
        decimal_places=0
    )

    pourcentage = models.DecimalField(
        max_digits=5,
        decimal_places=2
    )

    photo = models.ImageField(
        upload_to="images/Produits/",
        null=True,
        blank=True
    )

    enregistre_par = models.ForeignKey(
        AppUser,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="produits_crees"
    )

    paye = models.BooleanField(
        default=False
    )

    created_at = models.DateTimeField(
        auto_now_add=True
    )

    date_paiement = models.DateTimeField(
        null=True,
        blank=True
    )

    @property
    def montant_net(self):
        return (
            self.montant
            * self.quantite
            * self.pourcentage
            / Decimal("100")
        )

    @property
    def montant_avance(self):
        """
        Total des avances utilisées
        pour ce produit.
        """
        return sum(
            utilisation.montant
            for utilisation in self.utilisations_avance.all()
        )

    @property
    def reste_a_payer(self):
        """
        Montant restant après déduction
        des avances client.
        """
        return (
            self.montant_net
            - self.montant_avance
        )

    class Meta:

        ordering = [
            "-created_at",
            "-id"
        ]

        verbose_name = "Produit"

        verbose_name_plural = "Produits"

    def __str__(self):

        return (
            f"{self.client.nom.upper()} "
            f"- {self.vehicule.chauffeur.upper()}"
        )


class PaiementProduit(models.Model):

    distribution = models.ForeignKey(
        Distribution,
        on_delete=models.CASCADE,
        related_name="paiements_produits"
    )

    produit = models.ForeignKey(
        Produit,
        on_delete=models.CASCADE,
        related_name="paiements"
    )

    montant = models.DecimalField(
        max_digits=15,
        decimal_places=0
    )

    date = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:

        ordering = [
            "date",
            "id"
        ]

        verbose_name = "Paiement produit"

        verbose_name_plural = "Paiements produits"

    def __str__(self):

        return (
            f"{self.distribution} -> "
            f"{self.produit} "
            f"({self.montant} Ar)"
        )