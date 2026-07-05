from django.db import models
from clients.models import Client

class Produit(models.Model):

    TYPE_CHOICES = [
        ('ESPECE', 'Espèce'),
        ('CHEQUE', 'Chèque'),
        ('MOBILE_MONEY', 'Mobile Money'),
    ]

    id_client = models.ForeignKey(Client, on_delete=models.CASCADE)

    Nom_Prod = models.CharField(max_length=100)
    Source_Prod = models.CharField(max_length=50)

    Type_Pro = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES
    )

    Montant_Pro = models.DecimalField(max_digits=10, decimal_places=2)
    Qte_Pro = models.DecimalField(max_digits=10, decimal_places=2)
    Pourcentage_Pro = models.DecimalField(max_digits=10, decimal_places=2)

    photo = models.ImageField(upload_to='images/Produits/')

    paye = models.BooleanField(default=False)

    created_at = models.DateTimeField(auto_now_add=True)

    date_paiement = models.DateTimeField(
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.id_client.nom.upper()} - {self.Nom_Prod}"

    class Meta:
        ordering = ['-id']