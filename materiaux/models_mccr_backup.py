
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Sum

from users.models import H_AppUser


# ============================================================
# CONFIGURATION EXCLUSIVE AU MCCR
# ============================================================

ENTREPRISE_CHOICES = [
    ("MCCR", "MCCR"),
]


def verifier_entreprise(entreprise, objet, champ="entreprise"):
    """Vérifie que les objets liés appartiennent au MCCR."""
    if objet is not None and entreprise != objet.entreprise:
        raise ValidationError({
            champ: (
                "Cet élément n'appartient pas au MCCR. "
                "Sélectionnez un élément du MCCR."
            )
        })


class EntrepriseModel(models.Model):
    entreprise = models.CharField(
        max_length=10,
        choices=ENTREPRISE_CHOICES,
        default="MCCR",
        db_index=True,
        verbose_name="Entreprise",
    )

    class Meta:
        abstract = True

    def clean(self):
        super().clean()

        if self.entreprise != "MCCR":
            raise ValidationError({
                "entreprise": "Ce module est réservé au MCCR."
            })


class EntrepriseAvecEnregistreur(EntrepriseModel):
    enregistreur_mccr = models.ForeignKey(
        H_AppUser,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_enregistrements_mccr",
        null=True,
        blank=True,
        verbose_name="Enregistré par (MCCR)",
    )

    class Meta:
        abstract = True
