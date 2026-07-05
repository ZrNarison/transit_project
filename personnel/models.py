from django.db import models


class Personnel(models.Model):
    nom = models.CharField(max_length=100)
    prenom = models.CharField(max_length=100, blank=True)
    adresse = models.TextField(blank=True)
    telephone = models.CharField(max_length=20)
    fonction = models.CharField(max_length=20, default="Employé")
    categorie = models.CharField(
        max_length=20,
        choices=[
            ('User', 'Client'),
            ('Admin', 'Administrateur'),
            ('SuperAdmin', 'SuperViseur'),
        ]
    )

    photo = models.ImageField(
        upload_to='images/Personnel/',
    )

    def __str__(self):
        return self.nom