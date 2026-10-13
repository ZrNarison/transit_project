from django.shortcuts import redirect
from django.urls import resolve, Resolver404, reverse


class LoginRequiredMiddleware:

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        path = request.path

        # =====================================================
        # ROUTES PUBLIQUES
        # =====================================================

        public_paths = {
            reverse("users:login"),
        }

        if (
            path in public_paths
            or path.startswith(
                ("/static/", "/media/", "/admin/")
            )
        ):
            return self.get_response(request)

        # =====================================================
        # RÉSOLUTION DE L'URL
        # =====================================================

        try:
            match = resolve(request.path_info)

            namespace = match.namespace or ""
            view_name = match.view_name or ""

        except Resolver404:
            return self.get_response(request)

        # =====================================================
        # SESSION ENTREPRISE H
        # =====================================================

        h_user_id = request.session.get("h_user_id")
        h_role = request.session.get("h_role")

        # Applications réservées à Entreprise H.
        # "avances" est retiré car les vues partagées
        # utilisent ici la session GALAXY.
        # "salaire" peut être partagé entre GALAXY et H.
        # "recette" utilise la session GALAXY.

        h_namespaces = {
            "materiaux",
            "categorie",
            "depotSoc",
            "audit",
            "logs",
        }

        # =====================================================
        # IDENTIFICATION DES ROUTES ENTREPRISE H
        # =====================================================

        is_h_route = (
            namespace in h_namespaces
            or view_name.startswith("users:h_")
            or view_name.startswith(
                "personnel:h_personnel_"
            )
            or view_name.startswith(
                "salaire:h_salaire_"
            )
        )

        # =====================================================
        # CONTRÔLE SESSION ENTREPRISE H
        # =====================================================

        if is_h_route:

            if not h_user_id or not h_role:
                return redirect("users:login")

            return self.get_response(request)

        # =====================================================
        # CONTRÔLE SESSION GALAXY
        # =====================================================

        if not request.session.get("user_id"):
            return redirect("users:login")

        return self.get_response(request)