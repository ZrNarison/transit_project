from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def role_required(*roles):

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            # Vérifier connexion
            if not request.session.get("user_id"):

                messages.error(
                    request,
                    "Veuillez vous connecter."
                )

                return redirect(
                    "users:login"
                )


            # Récupérer catégorie utilisateur
            categorie = request.session.get(
                "categorie"
            )


            # Vérifier rôle
            if categorie not in roles:

                messages.error(
                    request,
                    "Accès interdit."
                )

                return redirect("/")


            return view_func(
                request,
                *args,
                **kwargs
            )


        return wrapper

    return decorator