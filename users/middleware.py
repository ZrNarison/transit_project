from django.shortcuts import redirect
from django.urls import resolve, Resolver404, reverse


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        path = request.path

        # Routes publiques
        public_paths = {
            reverse("users:login"),
        }

        if (
            path in public_paths
            or path.startswith(("/static/", "/media/", "/admin/"))
        ):
            return self.get_response(request)

        try:
            match = resolve(request.path_info)
            namespace = match.namespace or ""
            view_name = match.view_name or ""
        except Resolver404:
            return self.get_response(request)

        # Vérifier la session Entreprise H
        h_user_id = request.session.get("h_user_id")
        h_role = request.session.get("h_role")

        # Les pages réservées à Entreprise H
        h_namespaces = {
            "materiaux",
            "categorie",
            "avances",
            "depotSoc",
            "salaire",
            "recette",
            "materiels",
            "materielEntre",
            "materielsort",
            "rapportsoc",
            "audit",
            "logs",
        }

        is_h_route = (
            namespace in h_namespaces
            or view_name.startswith("users:h_")
            or view_name.startswith("personnel:h_personnel_")
        )

        if is_h_route:
            if not h_user_id or not h_role:
                return redirect("users:login")

            # Les vues et leurs décorateurs doivent vérifier
            # que la session H correspond à un utilisateur valide.
            return self.get_response(request)

        # Authentification GALAXY pour les autres pages
        if not request.session.get("user_id"):
            return redirect("users:login")

        return self.get_response(request)