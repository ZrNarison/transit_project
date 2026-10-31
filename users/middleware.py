
from django.shortcuts import redirect
from django.urls import Resolver404, resolve, reverse


class LoginRequiredMiddleware:
    """
    Middleware d'authentification pour TRANSIT_PROJECT.

    GALAXY :
        Session :
            user_id
            username
            role
            photo
            typeTravail

    MCCR :
        Session :
            h_user_id
            h_username
            h_role
            h_photo

    Les routes MCCR sont reconnues par leur namespace
    ou par leur nom de route.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):

        path = request.path

        # ==================================================
        # 1. ROUTES PUBLIQUES
        # ==================================================
        public_paths = {
            reverse("users:login"),
        }

        if (
            path in public_paths
            or path.startswith((
                "/static/",
                "/media/",
                "/admin/",
            ))
        ):
            return self.get_response(request)

        # ==================================================
        # 2. RÉSOLUTION DE LA ROUTE DJANGO
        # ==================================================
        try:
            match = resolve(request.path_info)

            namespace = match.namespace or ""
            view_name = match.view_name or ""

        except Resolver404:
            # Laisser Django gérer les URL inexistantes.
            return self.get_response(request)

        # ==================================================
        # 3. RÉCUPÉRATION DES SESSIONS
        # ==================================================
        h_user_id = request.session.get("h_user_id")
        h_role = request.session.get("h_role")

        galaxy_user_id = request.session.get("user_id")

        # ==================================================
        # 4. NAMESPACES RÉSERVÉS À MCCR
        # ==================================================
        h_namespaces = {
            "mccr_materiaux",
        }

        # ==================================================
        # 5. PRÉFIXES DES ROUTES MCCR
        # ==================================================
        h_route_prefixes = (

            # Utilisateurs MCCR
            "users:h_",

            # Personnel MCCR
            "personnel:h_personnel_",

            # Salaires MCCR
            "salaire:h_salaire_",

            # Banque Construction
            "depotSoc:h_depot_soc_",

            # Dépenses MCCR
            "depensesoc:h_soc_depense_",

            # Audit MCCR
            "audit:h_",

            # Logs MCCR
            "logs:h_",

            # Sauvegarde MCCR
            "sauvegarde:h_",

            # Matériels MCCR
            "materiels:h_materiels_",

            # Entrées matériels MCCR
            "materielEntre:h_materielEntre_",

            # Sorties matériels MCCR
            "materielsort:h_materielsort_",

            # Recettes MCCR
            "recette:h_recette_",

            # Rapports MCCR
            "rapportsoc:h_",

            # Avances MCCR
            "avances:h_",
        )

        # ==================================================
        # 6. IDENTIFICATION D'UNE ROUTE MCCR
        # ==================================================
        is_h_route = (
            namespace in h_namespaces
            or any(
                view_name.startswith(prefix)
                for prefix in h_route_prefixes
            )
        )

        # ==================================================
        # 7. PROTECTION DES ROUTES MCCR
        # ==================================================
        if is_h_route:

            if not h_user_id or not h_role:
                return redirect("users:login")

            # Session MCCR valide.
            return self.get_response(request)

        # ==================================================
        # 8. AUTRES ROUTES
        # ==================================================
        # Les autres routes conservent leurs propres
        # décorateurs et règles d'accès.
        #
        # GALAXY continue à utiliser user_id.
        # Le middleware ne modifie pas ses autorisations.

        return self.get_response(request)
