from django.db import models

# Create your models here.

class Client(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100, blank=True)
    date_naissance = models.DateField(null=True)
    lieu_naissance = models.CharField(max_length=150)
    nom_pere = models.CharField(max_length=150, blank=True)
    nom_mere = models.CharField(max_length=150, blank=True)
    adresse = models.TextField(blank=True)
    photo = models.ImageField(upload_to='images/Clients/')

    def __str__(self):
        return f"{self.nom.upper()} {self.prenom}"
    
    # def __str__(self):
    #     return self.nom