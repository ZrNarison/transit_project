
from users.models import AppUser, H_AppUser

from .models import Audit, H_Audit


def enregistrer_action(
    request,
    action,
    table,
    objet_id=None,
    ancienne=None,
    nouvelle=None,
    description="",
):
    """Enregistre une action dans l'audit GALAXY."""

    utilisateur = None
    user_id = request.session.get("user_id")

    if user_id:
        try:
            utilisateur = AppUser.objects.get(pk=user_id)
        except AppUser.DoesNotExist:
            utilisateur = None

    return Audit.objects.create(
        utilisateur=utilisateur,
        action=action,
        table=table,
        objet_id=objet_id,
        ancienne_valeur=ancienne,
        nouvelle_valeur=nouvelle,
        description=description,
    )


def h_enregistrer_action(
    request,
    action,
    table,
    objet_id=None,
    ancienne=None,
    nouvelle=None,
    description="",
):
    """Enregistre une action dans l'audit MCCR."""

    utilisateur = None
    user_id = request.session.get("h_user_id")

    if user_id:
        try:
            utilisateur = H_AppUser.objects.get(pk=user_id)
        except H_AppUser.DoesNotExist:
            utilisateur = None

    return H_Audit.objects.create(
        utilisateur=utilisateur,
        action=action,
        table=table,
        objet_id=objet_id,
        ancienne_valeur=ancienne,
        nouvelle_valeur=nouvelle,
        description=description,
    )
