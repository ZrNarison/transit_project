from django.db import models

# Create your models here.
class Salaire(models.Model):
    id_Sal_Pers = models.DecimalField(max_length=100)
    Montant_Sal = models.DecimalField(max_length=100)
    Reste_Sal = models.DecimalField(max_digits=10, decimal_places=2, null=True)

    def __str__(self):
        return self.id_Sal_Pers