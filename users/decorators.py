
from functools import wraps

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404, redirect
from django.utils import timezone
from django.views.decorators.cache import never_cache
from users.models import AppUser


# ============================================================
# CONFIGURATION DES RÔLES
# ============================================================

# Vérifie que ces rôles correspondent bien aux droits souhaités
# dans ton projet. Ne donne pas un rôle de gestion par défaut
# à un utilisateur qui ne doit pas posséder ces droits.
PROJECT_MANAGER_ROLES = {
    "Admin",
    "Superviseur",
    "UserEntreprise",
}

# ============================================================
# CONFIGURATION DES RÔLES MICA
# ============================================================

MICA_MANAGER_ROLES = {
    "Admin",
    "Superviseur",
    "UserMica",
}


# ============================================================
# IMPORTS DES MODÈLES DU PROJET
# Imports locaux pour limiter les risques de dépendances
# circulaires entre les applications Django.
# ============================================================

def _get_project_models():
    from personnel.models import Personnel
    from projet.models import EquipeProjet, Projet

    return Personnel, EquipeProjet, Projet



def mica_required(view_func):

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        user_id = request.session.get("user_id")

        if not user_id:
            messages.error(
                request,
                "Veuillez vous connecter."
            )
            return redirect("users:login")

        user = (
            AppUser.objects
            .filter(pk=user_id)
            .first()
        )

        if not user:
            request.session.flush()
            messages.error(
                request,
                "Votre session a expiré. Veuillez vous reconnecter."
            )
            return redirect("users:login")

        if user.role not in MICA_MANAGER_ROLES:
            messages.error(
                request,
                "Vous n'avez pas accès au module Mica."
            )
            return redirect("users:login")

        request.current_user = user

        return view_func(request, *args, **kwargs)

    return wrapper
# ============================================================
# CONTRÔLE DES RÔLES DE SESSION
# ============================================================

def role_required(*roles):
    """Autorise uniquement les rôles de session indiqués."""

    def decorator(view_func):

        @wraps(view_func)
        def wrapper(request, *args, **kwargs):

            user = get_current_user(request)

            if not user:
                messages.error(
                    request,
                    "Veuillez vous connecter."
                )
                return redirect("users:login")

            # Le rôle enregistré à la connexion est "role",
            # et non "categorie".
            if user.role not in roles:
                raise PermissionDenied(
                    "Vous n'avez pas l'autorisation d'accéder à cette page."
                )

            request.current_user = user

            return view_func(request, *args, **kwargs)

        return wrapper

    return decorator
# ============================================================
# UTILISATEUR CONNECTÉ
# ============================================================

def get_current_user(request):
    """
    Retourne l'AppUser connecté.

    La session user_id doit contenir l'identifiant de AppUser.
    """

    user_id = request.session.get("user_id")

    if not user_id:
        return None

    return (
        AppUser.objects
        .select_related("personnel")
        .filter(pk=user_id)
        .first()
    )


# ============================================================
# AUTHENTIFICATION PERSONNALISÉE
# ============================================================

def login_required_projet(view_func):
    """Vérifie que l'utilisateur AppUser est connecté."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        user = get_current_user(request)

        if not user:
            messages.error(
                request,
                "Veuillez vous connecter.",
            )
            return redirect("users:login")

        request.current_user = user

        return view_func(request, *args, **kwargs)

    return wrapper


# ============================================================
# DROITS DE GESTION DES PROJETS
# ============================================================

def user_can_manage_projects(user):
    """
    Vérifie si l'utilisateur possède un rôle de gestion.

    Accepte un AppUser ou, par précaution, un Personnel.
    """

    if not user:
        return False

    Personnel, _, _ = _get_project_models()

    if isinstance(user, Personnel):
        user = (
            AppUser.objects
            .filter(personnel=user)
            .first()
        )

        if not user:
            return False

    if not isinstance(user, AppUser):
        return False

    return user.role in PROJECT_MANAGER_ROLES


def project_manager_required(view_func):
    """Réserve la vue aux gestionnaires de projets."""

    @wraps(view_func)
    @login_required_projet
    def wrapper(request, *args, **kwargs):

        if not user_can_manage_projects(request.current_user):
            messages.error(
                request,
                "Vous n'avez pas l'autorisation de gérer les projets.",
            )
            return redirect("projet:projet_list")

        return view_func(request, *args, **kwargs)

    return wrapper


# ============================================================
# PERSONNEL ASSOCIÉ À L'UTILISATEUR
# ============================================================

def get_current_personnel(request):
    """Retourne le Personnel associé à l'utilisateur connecté."""

    user = getattr(request, "current_user", None)

    if not user:
        user = get_current_user(request)

    if not user:
        return None

    return getattr(user, "personnel", None)


# ============================================================
# DROITS DE GESTION DES MATÉRIAUX
# ============================================================

def user_can_manage_materiaux(user, projet=None):
    """
    Autorise :
    - les gestionnaires globaux ;
    - les ingénieurs ;
    - les chefs de chantier ;
    - les chefs d'équipe affectés activement au projet.
    """

    if not user or not projet:
        return False

    if user_can_manage_projects(user):
        return True

    Personnel, EquipeProjet, _ = _get_project_models()

    if isinstance(user, Personnel):
        personnel = user
    elif isinstance(user, AppUser):
        personnel = user.personnel
    else:
        return False

    if not personnel:
        return False

    aujourd_hui = timezone.localdate()

    return EquipeProjet.objects.filter(
        projet=projet,
        personnel=personnel,
        actif=True,
        date_debut__lte=aujourd_hui,
        date_fin__gte=aujourd_hui,
        fonction__in=[
            "INGENIEUR",
            "CHEF_CHANTIER",
            "CHEF_EQUIPE",
        ],
    ).exists()


# ============================================================
# PRÉPARATION DU FORMULAIRE D'ÉQUIPE
# ============================================================

def prepare_equipe_form(form, projet=None, affectation=None):
    """
    Filtre les personnels proposés dans le formulaire d'équipe.
    Évite de proposer un personnel déjà affecté au même projet.
    """

    if "personnel" not in form.fields:
        return form

    Personnel, EquipeProjet, _ = _get_project_models()

    form.fields["personnel"].label = (
        "Personnel de l'entreprise"
    )

    queryset = Personnel.objects.filter(
        typeTravail="Construction",
    ).order_by("nom", "prenom")

    if projet:
        affectations = EquipeProjet.objects.filter(
            projet=projet,
        )

        # En modification, on conserve le personnel de
        # l'affectation actuelle dans les choix disponibles.
        if affectation and affectation.pk:
            affectations = affectations.exclude(
                pk=affectation.pk,
            )

        personnels_deja_affectes = (
            affectations.values_list(
                "personnel_id",
                flat=True,
            )
        )

        queryset = queryset.exclude(
            pk__in=personnels_deja_affectes,
        )

    form.fields["personnel"].queryset = queryset

    return form


# ============================================================
# VÉRIFICATION DE L'ACCÈS À UN PROJET
# ============================================================

def user_has_project_access(user, projet):
    """
    Vérifie l'accès actuel au projet.

    Les gestionnaires globaux ont accès à tous les projets.
    Les autres utilisateurs doivent avoir une affectation active.
    """

    if not user or not projet:
        return False

    Personnel, EquipeProjet, _ = _get_project_models()

    if isinstance(user, Personnel):
        user = (
            AppUser.objects
            .select_related("personnel")
            .filter(personnel=user)
            .first()
        )

        if not user:
            return False

    if not isinstance(user, AppUser):
        return False

    if user_can_manage_projects(user):
        return True

    personnel = getattr(user, "personnel", None)

    if not personnel:
        return False

    aujourd_hui = timezone.localdate()

    return EquipeProjet.objects.filter(
        projet=projet,
        personnel=personnel,
        actif=True,
        date_debut__lte=aujourd_hui,
        date_fin__gte=aujourd_hui,
    ).exists()


# ============================================================
# DÉCORATEUR D'ACCÈS À UN PROJET
# ============================================================

def project_access_required(view_func):
    """
    Vérifie l'accès au projet identifié par le paramètre URL
    projet_id, puis rend le projet disponible via request.projet.
    """

    @wraps(view_func)
    @login_required_projet
    def wrapper(request, *args, **kwargs):

        projet_id = kwargs.get("projet_id")

        if not projet_id:
            raise PermissionDenied("Projet non spécifié.")

        _, _, Projet = _get_project_models()

        projet = get_object_or_404(
            Projet,
            pk=projet_id,
        )

        if not user_has_project_access(
            request.current_user,
            projet,
        ):
            messages.error(
                request,
                "Votre accès à ce projet n'est pas actif.",
            )
            return redirect("projet:projet_list")

        request.projet = projet

        return view_func(request, *args, **kwargs)

    return wrapper

# ============================================================
# CONTRÔLE DES FONCTIONS DANS L'ÉQUIPE DU PROJET
# ============================================================

def user_has_project_function(user, projet, fonctions):
    """
    Vérifie si l'utilisateur exerce l'une des fonctions
    demandées dans l'équipe du projet.
    """

    if not user or not projet:
        return False

    Personnel, EquipeProjet, _ = _get_project_models()

    if isinstance(user, Personnel):
        personnel = user
        app_user = (
            AppUser.objects
            .filter(personnel=personnel)
            .first()
        )

        if app_user and user_can_manage_projects(app_user):
            return True

    elif isinstance(user, AppUser):
        if user_can_manage_projects(user):
            return True

        personnel = getattr(user, "personnel", None)

    else:
        return False

    if not personnel:
        return False

    aujourd_hui = timezone.localdate()

    return EquipeProjet.objects.filter(
        projet=projet,
        personnel=personnel,
        actif=True,
        date_debut__lte=aujourd_hui,
        date_fin__gte=aujourd_hui,
        fonction__in=fonctions,
    ).exists()

# ============================================================
# PROTECTION CONTRE L'ACCÈS APRÈS DÉCONNEXION
# ============================================================

def session_login_required(view_func):
    """
    Protège une vue contre l'accès sans session valide.
    Empêche la mise en cache des pages protégées.
    """

    @wraps(view_func)
    @never_cache
    def wrapper(request, *args, **kwargs):

        user_id = request.session.get("user_id")

        if not user_id:
            messages.warning(
                request,
                "Votre session a expiré. Veuillez vous reconnecter."
            )
            return redirect("users:login")

        # Vérifier que l'utilisateur existe toujours.
        user = AppUser.objects.filter(pk=user_id).first()

        if not user:
            request.session.flush()
            messages.warning(
                request,
                "Votre session a expiré. Veuillez vous reconnecter."
            )
            return redirect("users:login")

        request.current_user = user

        return view_func(request, *args, **kwargs)

    return wrapper
