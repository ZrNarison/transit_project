from django.utils import timezone

from users.models import AppUser
from projet.models import EquipeProjet


def projet_context(request):
    fonction_projet = None
    projet_affectations = []

    user_id = request.session.get("user_id")

    if user_id:
        user = (
            AppUser.objects
            .select_related("personnel")
            .filter(pk=user_id)
            .first()
        )

        if user and user.personnel:
            aujourd_hui = timezone.localdate()

            affectations = (
                EquipeProjet.objects
                .filter(
                    personnel=user.personnel,
                    actif=True,
                    date_debut__lte=aujourd_hui,
                    date_fin__gte=aujourd_hui,
                )
                .select_related("projet")
            )

            projet_affectations = list(affectations)

            if len(projet_affectations) == 1:
                fonction_projet = projet_affectations[0].fonction

    return {
        "fonction_projet": fonction_projet,
        "projet_affectations": projet_affectations,
    }