from .models import Audit
from users.models import AppUser


def enregistrer_action(
    request,
    action,
    table,
    objet_id=None,
    ancienne=None,
    nouvelle=None,
    description=""
):

    """
    Enregistre une action utilisateur dans la table Audit.

    Paramètres :
        request : requête Django
        action : CREATE / UPDATE / DELETE / LOGIN / LOGOUT
        table : nom du module ou modèle concerné
        objet_id : id de l'objet concerné
        ancienne : ancienne valeur (dict)
        nouvelle : nouvelle valeur (dict)
        description : commentaire
    """


    # ==========================
    # Récupération utilisateur
    # ==========================

    utilisateur = None


    user_id = request.session.get(
        "user_id"
    )


    if user_id:

        try:

            utilisateur = AppUser.objects.get(
                id=user_id
            )

        except AppUser.DoesNotExist:

            utilisateur = None



    # ==========================
    # Création Audit
    # ==========================

    Audit.objects.create(

        utilisateur=utilisateur,

        action=action,

        table=table,

        objet_id=objet_id,

        ancienne_valeur=ancienne,

        nouvelle_valeur=nouvelle,

        description=description

    )