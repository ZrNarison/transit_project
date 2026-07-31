from django.db import models
from clients.models import Client
from transentrant.models import Transentrant

class Produit(models.Model):

    TYPE_CHOICES = [
        ('ESPECE', 'Espèce'),
        ('CHEQUE', 'Chèque'),
        ('MOBILE_MONEY', 'Mobile Money'),
    ]

    client = models.ForeignKey(Client, on_delete=models.CASCADE)
    vehicule = models.ForeignKey(Transentrant, on_delete=models.CASCADE)

    source = models.CharField(max_length=50)
    type_produit = models.CharField(max_length=20, choices=TYPE_CHOICES)

    montant = models.DecimalField(max_digits=4, decimal_places=0)
    quantite = models.DecimalField(max_digits=10, decimal_places=0)
    pourcentage = models.DecimalField(max_digits=2, decimal_places=0)

    photo = models.ImageField(upload_to='images/Produits/')

    paye = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    date_paiement = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.client.nom} - {self.vehicule.Chauf_Ent|upper}"