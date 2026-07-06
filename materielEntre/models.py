from django.db import models


class MaterielEntre(models.Model):

    id_Materiel = models.ForeignKey(
        "materiels.Materiels",
        on_delete=models.CASCADE,
        related_name="entrees"
    )

    id_MaterielSort = models.ForeignKey(
        "materielsort.MaterielSort",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="retours"
    )

    Nb_Entre = models.DecimalField(
        max_digits=10,
        decimal_places=0
    )

    dateEntre = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-dateEntre"]
        verbose_name = "Entrée de matériel"
        verbose_name_plural = "Entrées de matériel"

    def __str__(self):
        return f"{self.id_Materiel.nom} ({self.Nb_Entre})"