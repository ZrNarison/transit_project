from django.db import models


class Materiels(models.Model):
    nom = models.CharField(max_length=100)
    typeMat = models.CharField(max_length=100)
    catMat = models.CharField(max_length=100)
    stock_initial = models.DecimalField(
        max_digits=10,
        decimal_places=0,
        default=0
    )

    class Meta:
        ordering = ["nom"]
        verbose_name = "Matériel"
        verbose_name_plural = "Matériels"

    def stock_sorti(self):
        return sum(
            sortie.Nb_MatSort
            for sortie in self.sorties.all()
        )

    def stock_entre(self):
        return sum(
            entree.Nb_Entre
            for entree in self.entrees.all()
        )

    def stock_restant(self):
        return (
            self.stock_initial
            - self.stock_sorti()
            + self.stock_entre()
        )

    def __str__(self):
        return self.nom