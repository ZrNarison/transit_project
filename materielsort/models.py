from django.db import models


class MaterielSort(models.Model):

    id_Materiel = models.ForeignKey(
        "materiels.Materiels",
        on_delete=models.CASCADE,
        related_name="sorties"
    )

    Nb_MatSort = models.DecimalField(
        max_digits=10,
        decimal_places=0
    )

    dateSortie = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-dateSortie"]
        verbose_name = "Sortie de matériel"
        verbose_name_plural = "Sorties de matériel"

    def __str__(self):
        return f"{self.id_Materiel.nom} ({self.Nb_MatSort})"