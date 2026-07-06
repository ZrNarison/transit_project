from django.db import models

class Client(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100, blank=True)
    date_naissance = models.DateField(null=True, blank=True)
    lieu_naissance = models.CharField(max_length=150)
    cin = models.CharField(max_length=12)
    nom_pere = models.CharField(max_length=150, blank=True)
    nom_mere = models.CharField(max_length=150, blank=True)
    contact = models.CharField(max_length=10, blank=True)
    adresse = models.TextField(blank=True)
    photo = models.ImageField(upload_to='images/Clients/')

    def __str__(self):
        return f"{self.nom.upper()} {self.prenom}"