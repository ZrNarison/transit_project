from materiels.models import Materiels
from materielsort.models import MaterielSort
from django.db import models


class MaterielEntre(models.Model):

    id_MaterielSort = models.ForeignKey(
        MaterielSort,
        on_delete=models.CASCADE,
        related_name="entrees" 
    )

    Nb_Entre = models.DecimalField(max_digits=10, decimal_places=0)
    responsable_entree = models.CharField(max_length=100, null=True, blank=True)
    observation = models.TextField(blank=True, null=True)
    dateEntre = models.DateTimeField(auto_now_add=True)