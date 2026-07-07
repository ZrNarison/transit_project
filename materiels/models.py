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


    # ==========================
    # TOTAL SORTIES
    # ==========================
    def stock_sorti(self):

        return sum(
            s.Nb_MatSort or 0
            for s in self.sorties.all()
        )


    # ==========================
    # TOTAL ENTREES (REMISES)
    # Materiels → MaterielSort → MaterielEntre
    # ==========================
    def stock_entre(self):

        return sum(
            e.Nb_Entre or 0
            for s in self.sorties.all()
            for e in s.entrees.all()
        )


    # ==========================
    # STOCK RESTANT
    # ==========================
    def stock_restant(self):

        return (
            self.stock_initial
            - self.stock_sorti()
            + self.stock_entre()
        )


    def __str__(self):

        return f"{self.nom} | {self.typeMat} | {self.catMat}"