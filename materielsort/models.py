from django.db import models
from materiels.models import Materiels


class MaterielSort(models.Model):

    id_Materiel = models.ForeignKey(
        Materiels,
        on_delete=models.CASCADE,
        related_name="sorties"
    )

    demandeur = models.CharField(max_length=100)
    responsable_sortie = models.CharField(max_length=100)

    Nb_MatSort = models.DecimalField(
        max_digits=10,
        decimal_places=0
    )

    observation = models.TextField(blank=True, null=True)

    avec_remise = models.BooleanField(default=False)

    dateSortie = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-dateSortie"]
        verbose_name = "Sortie de matériel"
        verbose_name_plural = "Sorties de matériel"

    def __str__(self):
        return f"{self.id_Materiel} - {self.Nb_MatSort}"