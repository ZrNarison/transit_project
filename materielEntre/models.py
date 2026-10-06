from django.db import models
from materielsort.models import MaterielSort


class MaterielEntre(models.Model):

    id_MaterielSort = models.ForeignKey(
        MaterielSort,
        on_delete=models.CASCADE,
        related_name="entrees"
    )

    Nb_Entre = models.DecimalField(
        max_digits=10,
        decimal_places=0
    )

    responsable_entree = models.CharField(
        max_length=100,
        null=True,
        blank=True
    )

    observation = models.TextField(
        blank=True,
        null=True
    )

    # Date saisie par l'utilisateur
    dateEntre = models.DateField()

    dateEnregistreur = models.DateTimeField(
        auto_now_add=True
    )

    class Meta:
        ordering = ["-dateEntre", "-id"]
        verbose_name = "Entrée de matériel"
        verbose_name_plural = "Entrées de matériel"

    def __str__(self):
        return (
            f"{self.id_MaterielSort.id_Materiel.nom} | "
            f"Quantité : {self.Nb_Entre} | "
            f"Date : {self.dateEntre}"
        )