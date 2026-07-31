from django.db import models
from personnel.models import Personnel


class Avance(models.Model):

    TYPE_AVANCE = [
        ('ESPECE', 'Espèce'),
        ('CHEQUE', 'Chèque'),
        ('MOBILE_MONEY', 'Mobile Money'),
    ]

    personnel = models.ForeignKey(Personnel, on_delete=models.CASCADE, related_name='avances', null=True, blank=True)
    motifAv = models.CharField(max_length=255)
    montantAv = models.DecimalField(max_digits=10, decimal_places=2)

    typeAv = models.CharField(
        max_length=20,
        choices=TYPE_AVANCE,
        default='ESPECE'
    )

    dateAv = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.personnel} - {self.montantAv}"