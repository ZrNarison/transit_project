from decimal import Decimal

from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import Avance


@receiver(post_save, sender=Avance)
def update_salaire_on_avance_save(sender, instance, **kwargs):
    """When an Avance is saved, recalculate reste for all Salaire of the personnel."""
    personnel = instance.personnel
    if not personnel:
        return
    # Import here to avoid circular imports at module import time
    from salaire.models import Salaire

    for s in Salaire.objects.filter(personnel=personnel):
        s.reste = s.calculate_reste()
        s.save()


@receiver(post_delete, sender=Avance)
def update_salaire_on_avance_delete(sender, instance, **kwargs):
    """When an Avance is deleted, recalculate reste for all Salaire of the personnel."""
    personnel = instance.personnel
    if not personnel:
        return
    from salaire.models import Salaire

    for s in Salaire.objects.filter(personnel=personnel):
        s.reste = s.calculate_reste()
        s.save()
