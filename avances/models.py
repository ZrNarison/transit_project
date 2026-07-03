from django.db import models
from clients.models import Client

class Avance(models.Model):

    TYPE_AVANCE = [
        ('espece', 'Espèce'),
        ('cheque', 'Chèque'),
        ('mobile_money', 'Mobile Money'),
    ]

    id_client = models.ForeignKey(Client, on_delete=models.CASCADE)
    motifAv = models.CharField(max_length=255)
    montantAv = models.DecimalField(max_digits=10, decimal_places=2)

    typeAv = models.CharField(
        max_length=20,
        choices=TYPE_AVANCE
    )

    dateAv = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.id_client} - {self.montantAv}"