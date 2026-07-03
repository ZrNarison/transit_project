from django.db import models

# Create your models here.
class Personnel(models.Model):
        nom = models.CharField(max_length=100)
        prenom = models.CharField(max_length=100, blank=True)
        date_naissance = models.DateField(null=True)
        lieu_naissance = models.CharField(max_length=150)
        adresse = models.TextField(blank=True)
        telephone = models.CharField(max_length=20)
        categorie = models.CharField(max_length=100)
        photo = models.ImageField(upload_to='images/Personnel/')

        def __str__(self):
            return self.nom