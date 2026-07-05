from django.db import models
from clients.models import Client

class Transentrant(models.Model):
    id_client = models.ForeignKey(Client, on_delete=models.CASCADE)
    Chauf_Ent = models.CharField(max_length=100, blank=True)
    NumVeh_Ent = models.CharField(max_length=50)  # corrigé (pas DateField)
    NumPermis_Ent = models.CharField(max_length=150)
    adresse = models.TextField(blank=True)
    telephone = models.CharField(max_length=10)
    photo = models.ImageField(upload_to='images/VehiculesEntrant/')

    def __str__(self):
        return f"{self.id_client} - {self.Chauf_Ent}"