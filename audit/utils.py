from .models import Audit


def enregistrer_action(
    request,
    action,
    table,
    objet_id=None,
    ancienne=None,
    nouvelle=None,
    description=""
):

    utilisateur = None


    user_id = request.session.get(
        "user_id"
    )


    if user_id:

        from users.models import AppUser

        try:

            utilisateur = AppUser.objects.get(
                id=user_id
            )

        except AppUser.DoesNotExist:

            utilisateur = None



    Audit.objects.create(

        utilisateur=utilisateur,

        action=action,

        table=table,

        objet_id=objet_id,

        ancienne_valeur=ancienne,

        nouvelle_valeur=nouvelle,

        description=description

    )