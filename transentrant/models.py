from django.db import models
# from clients.models import Client


class Transentrant(models.Model):
    # id_client = models.ForeignKey(Client, on_delete=models.CASCADE)
    chauffeur = models.CharField(max_length=100)
    cin = models.CharField(max_length=12)
    num_vehicule = models.CharField(max_length=8)
    permis = models.CharField(max_length=150)
    telephone = models.CharField(max_length=10)
    adresse= models.TextField(blank=True)

    photo = models.ImageField(upload_to='images/VehiculesEntrant/')

    def __str__(self):
        return f"{self.chauffeur} - {self.num_vehicule}"