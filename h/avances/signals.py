from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import h_Avance
from salaire.views import recalculer_situation_personnel


# ============================================================
# APRÈS CRÉATION OU MODIFICATION D'UNE AVANCE
# ============================================================

@receiver(post_save, sender=Avance)
def update_salaire_on_avance_save(sender, instance, **kwargs):
    """
    Recalcule toute la situation salariale du personnel
    après création ou modification d'une avance.

    La logique FIFO est entièrement gérée par :
        recalculer_situation_personnel()
    """

    if not instance.personnel_id:
        return

    recalculer_situation_personnel(
        instance.personnel
    )


# ============================================================
# APRÈS SUPPRESSION D'UNE AVANCE
# ============================================================

@receiver(post_delete, sender=Avance)
def update_salaire_on_avance_delete(sender, instance, **kwargs):
    """
    Recalcule toute la situation salariale du personnel
    après suppression d'une avance.
    """

    if not instance.personnel_id:
        return

    recalculer_situation_personnel(
        instance.personnel
    )

