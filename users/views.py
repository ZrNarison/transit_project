
from django.contrib import messages
from django.contrib.auth.hashers import check_password, make_password
from django.core.exceptions import ImproperlyConfigured
from django.core.paginator import Paginator
from django.db import transaction
from django.forms import modelform_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from users.decorators import h_role_required
from audit.utils import enregistrer_action, h_enregistrer_action
from logs.utils import enregistrer_log, h_enregistrer_log
from .forms import H_UserForm, UserForm
from .models import AppUser, H_AppUser

# ============================================================
# CONSTANTES ET COMPTES PAR DEFAUT
# ============================================================

ADMIN_USERNAME = "GEGE"
ADMIN_PASSWORD = "GEGE Galaxy"

H_ADMIN_USERNAME = "H Admin"
H_ADMIN_PASSWORD = "ELPhBert"


# ============================================================
# OUTILS COMMUNS
# ============================================================

def _journaliser(message, level="INFO", module="AUTH", request=None):
    """Enregistre l'événement dans le journal de la bonne entreprise."""
    est_mccr = (
        request is not None
        and request.session.get("h_user_id") is not None
    )

    fonction_log = h_enregistrer_log if est_mccr else enregistrer_log

    return fonction_log(
        message=message,
        level=level,
        module=module,
        ip_address=(
            request.META.get("REMOTE_ADDR")
            if request is not None
            else None
        ),
    )




def _photo_url(user):
    """Retourne l'URL de la photo, ou None."""
    if user and getattr(user, "photo", None):
        try:
            return user.photo.url
        except (ValueError, AttributeError):
            return None
    return None


def _personnel_type(user):
    """Retourne le type de travail du personnel associé."""
    personnel = getattr(user, "personnel", None)
    return getattr(personnel, "typeTravail", None) if personnel else None


def _profil_inaccessible(request, user, user_id, session_key, detail_route):
    """
    Vérifie qu'un utilisateur consulte uniquement son propre profil.
    Retourne l'utilisateur ou une réponse HTTP de redirection.
    """
    connected_id = request.session.get(session_key)

    if not connected_id:
        messages.warning(request, "Veuillez vous connecter.")
        return redirect("users:login")

    connected_user = get_object_or_404(user, pk=connected_id)

    if str(connected_user.pk) != str(user_id):
        messages.error(
            request,
            "Accès refusé : vous ne pouvez pas consulter "
            "le compte d'un autre utilisateur.",
        )
        return redirect(detail_route, id=connected_user.pk)

    return connected_user


def _render_profile_form(request, template, user):
    return render(request, template, {"user": user})


# ============================================================
# ADMINISTRATEUR GALAXY
# ============================================================


@transaction.atomic
def creer_admin_temporaire():
    """
    Garantit l'existence d'un administrateur GALAXY.

    Le compte GEGE est créé uniquement si aucun rôle Admin
    n'existe. Un compte GEGE existant n'a pas son mot de passe
    réinitialisé automatiquement.
    """
    if AppUser.objects.filter(role="Admin").exists():
        return None

    user = AppUser.objects.filter(username__iexact=ADMIN_USERNAME).first()

    if user:
        user.role = "Admin"
        user.save(update_fields=["role"])
        return user

    return AppUser.objects.create(
        username=ADMIN_USERNAME,
        email="",
        password=make_password(ADMIN_PASSWORD),
        role="Admin",
        personnel=None,
    )


def verifier_admin_temporaire(request=None):
    """Garantit la présence d'un Admin GALAXY et avertit si créé."""
    admin = creer_admin_temporaire()

    if admin and request:
        messages.warning(
            request,
            "Un compte administrateur GALAXY par défaut a été "
            "créé ou réactivé. Vérifiez ses identifiants.",
        )

    return admin


# ============================================================
# ADMINISTRATEUR ENTREPRISE H
# ============================================================


@transaction.atomic
def creer_h_admin_par_defaut():
    """
    Garantit l'existence d'un compte Dir pour Entreprise H.
    Ne réinitialise pas le mot de passe d'un compte existant.
    """
    if H_AppUser.objects.filter(role="Dir").exists():
        return None

    user = H_AppUser.objects.filter(username__iexact=H_ADMIN_USERNAME).first()

    if user:
        user.role = "Dir"
        user.save(update_fields=["role"])
        return user

    return H_AppUser.objects.create(
        username=H_ADMIN_USERNAME,
        password=make_password(H_ADMIN_PASSWORD),
        role="Dir",
        email=None,
        personnel=None,
    )


# ============================================================
# FORMULAIRE ENTREPRISE H
# ============================================================


def get_h_user_form(*args, **kwargs):
    """
    Utilise UserForm directement s'il est lié à H_AppUser.
    Sinon, construit un ModelForm adapté à H_AppUser en conservant
    les champs personnalisés compatibles de UserForm.

    Cela évite de transmettre une instance H_AppUser à un
    ModelForm lié à AppUser.
    """
    if UserForm._meta.model is H_AppUser:
        return UserForm(*args, **kwargs)

    model_fields = {
        field.name
        for field in H_AppUser._meta.get_fields()
        if getattr(field, "concrete", False)
        and not getattr(field, "auto_created", False)
    }

    declared_fields = set(UserForm.base_fields.keys())

    meta_fields = UserForm._meta.fields
    if meta_fields == "__all__":
        selected_fields = model_fields
    else:
        selected_fields = set(meta_fields or [])

    # Conserver uniquement les champs modèle existants dans H_AppUser.
    selected_fields = selected_fields.intersection(model_fields)

    # Conserver les champs personnalisés, par exemple password,
    # s'ils sont déclarés dans UserForm.
    custom_fields = declared_fields - model_fields
    selected_fields.update(custom_fields)

    # Un ModelForm ne doit pas recevoir de champ inexistant
    # qui n'est pas déclaré explicitement dans le formulaire.
    selected_fields = selected_fields.intersection(model_fields | declared_fields)

    if not selected_fields:
        raise ImproperlyConfigured(
            "Impossible de construire le formulaire Entreprise H. "
            "Vérifiez les champs de H_AppUser et UserForm."
        )

    HUserForm = modelform_factory(
        H_AppUser,
        form=UserForm,
        fields=sorted(selected_fields),
    )

    return HUserForm(*args, **kwargs)


# ============================================================
# CONNEXION ENTREPRISE H
# ============================================================


def connexion_entreprise_h(request, username, password):
    user = H_AppUser.objects.filter(username__iexact=username).first()

    if user is None or not check_password(password, user.password):
        messages.error(
            request,
            "Identifiants incorrects pour Entreprise H.",
        )
        return render(request, "users/login.html")

    request.session.flush()
    request.session["h_user_id"] = user.pk
    request.session["h_username"] = user.username
    request.session["h_role"] = user.role
    request.session["h_photo"] = _photo_url(user)
    request.session.set_expiry(0)

    _journaliser(
        f"Connexion Entreprise H : {user.username}",
        request=request,
    )

    return redirect("materiaux:dashboard")


# ============================================================
# REDIRECTION APRES CONNEXION GALAXY
# ============================================================


# ============================================================
# REDIRECTION APRES CONNEXION GALAXY
# ============================================================


def redirection_apres_login(request, user):

    # --------------------------------------------------------
    # ADMINISTRATEUR GALAXY
    # --------------------------------------------------------
    if user.role == "Admin":
        return redirect("projet:projet_list")

    # --------------------------------------------------------
    # SUPERVISEUR MICA ET UTILISATEURS MICA
    # --------------------------------------------------------
    if user.role in (
        "SuperviseurMica",
        "UserMica",
        "ChauffeurMica",
    ):
        return redirect("produit:p_produit_liste")

    # --------------------------------------------------------
    # SUPERVISEUR ENTREPRISE ET UTILISATEURS CONSTRUCTION
    # --------------------------------------------------------
    if user.role in (
        "SuperviseurEntreprise",
        "UserEntreprise",
        "UserProjet",
        "ChauffeurEntreprise",
    ):
        return redirect("projet:projet_list")

    # --------------------------------------------------------
    # MAGASIN
    # --------------------------------------------------------
    if user.role in (
        "ChefMagasin",
        "Magasin",
    ):
        return redirect("dashboard")

    # --------------------------------------------------------
    # ROLE NON CONFIGURE
    # --------------------------------------------------------
    messages.error(
        request, f"Le rôle « {user.role} » n'a pas de page d'accueil configurée."
    )

    request.session.flush()
    return redirect("users:login")


# ============================================================
# CONNEXION UNIQUE GALAXY / ENTREPRISE H
# ============================================================

@never_cache
@require_http_methods(["GET", "POST"])
def users_login(request):
    if request.method == "GET":
        verifier_admin_temporaire(request)
        creer_h_admin_par_defaut()
        return render(request, "users/login.html")

    username = request.POST.get("username", "").strip()
    password = request.POST.get("password", "")
    entreprise = request.POST.get("entreprise", "entreprise").strip()

    if not username or not password:
        messages.error(
            request,
            "Veuillez saisir le nom d'utilisateur et le mot de passe.",
        )
        return render(request, "users/login.html")

    # --------------------------------------------------------
    # MCCR (anciennement Entreprise H)
    # --------------------------------------------------------
    if entreprise == "H":
        user = H_AppUser.objects.filter(
            username__iexact=username
        ).first()

        if user is None or not check_password(password, user.password):
            messages.error(
                request,
                "Identifiants incorrects pour MCCR.",
            )
            return render(request, "users/login.html")

        request.session.flush()
        request.session["h_user_id"] = user.pk
        request.session["h_username"] = user.username
        request.session["h_role"] = user.role
        request.session["h_photo"] = _photo_url(user)
        request.session.set_expiry(0)

        # Audit MCCR
        h_enregistrer_action(
            request,
            "LOGIN",
            "Utilisateur",
            user.pk,
            description="Connexion MCCR",
        )

        # Journal MCCR
        _journaliser(
            f"Connexion MCCR : {user.username}",
            request=request,
        )

        return redirect("mccr_materiaux:dashboard_mccr")

    # --------------------------------------------------------
    # GALAXY
    # --------------------------------------------------------
    if entreprise != "entreprise":
        messages.error(
            request,
            "Entreprise sélectionnée invalide.",
        )
        return render(request, "users/login.html")

    user = (
        AppUser.objects.select_related("personnel")
        .filter(username__iexact=username)
        .first()
    )

    if user is None or not check_password(password, user.password):
        messages.error(
            request,
            "Identifiants incorrects pour GALAXY.",
        )
        return render(request, "users/login.html")

    request.session.flush()
    request.session["user_id"] = user.pk
    request.session["username"] = user.username
    request.session["role"] = user.role
    request.session["photo"] = _photo_url(user)
    request.session["typeTravail"] = _personnel_type(user)
    request.session.set_expiry(0)

    # Audit GALAXY
    enregistrer_action(
        request,
        "LOGIN",
        "Utilisateur",
        user.pk,
        description="Connexion GALAXY",
    )

    # Journal GALAXY
    _journaliser(
        f"Connexion GALAXY : {user.username}",
        request=request,
    )

    return redirection_apres_login(request, user)

# ============================================================
# DECONNEXION GALAXY
# ============================================================
@never_cache
@require_http_methods(["GET", "POST"])
def users_logout(request):
    user_id = request.session.get("user_id")
    username = request.session.get("username", "Utilisateur")

    if user_id:
        # Audit GALAXY
        enregistrer_action(
            request,
            "LOGOUT",
            "Utilisateur",
            user_id,
            description="Déconnexion GALAXY",
        )

        # Journal GALAXY
        _journaliser(
            f"Déconnexion GALAXY : {username}",
            request=request,
        )

    request.session.flush()

    messages.success(
        request,
        "Vous avez été déconnecté de GALAXY avec succès.",
    )
    return redirect("users:login")


# ============================================================
# DECONNEXION MCCR (ANCIENNEMENT ENTREPRISE H)
# ============================================================
@never_cache
@require_http_methods(["GET", "POST"])
def h_logout(request):
    username = request.session.get("h_username", "Utilisateur MCCR")
    h_user_id = request.session.get("h_user_id")

    if h_user_id:
        # Audit MCCR
        h_enregistrer_action(
            request,
            "LOGOUT",
            "Utilisateur",
            h_user_id,
            description="Déconnexion MCCR",
        )

        # Journal MCCR
        _journaliser(
            f"Déconnexion MCCR : {username}",
            request=request,
        )

    request.session.flush()

    messages.success(
        request,
        "Vous êtes déconnecté de MCCR.",
    )
    return redirect("users:login")

# ============================================================
# LIMITES DES COMPTES GALAXY
# ============================================================


def verifier_limite_utilisateur(role, personnel=None, instance=None):
    """
    Limites GALAXY :
      - Admin : maximum 2
      - Superviseur : maximum 2 par type de travail
      - UserMica : maximum 10
      - UserEntreprise : maximum 10
    """
    queryset = AppUser.objects.all()

    if instance and instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    if role == "Admin":
        if queryset.filter(role="Admin").count() >= 2:
            return False, (
                "Impossible de créer cet administrateur : " "le maximum est de 2 Admin."
            )
        return True, ""

    if role == "Superviseur":
        if not personnel:
            return False, "Un Superviseur doit être lié à un personnel."

        type_travail = getattr(personnel, "typeTravail", None)

        if type_travail not in ("Mica", "Construction"):
            return False, ("Le type de travail doit être Mica ou Construction.")

        nombre = queryset.filter(
            role="Superviseur",
            personnel__typeTravail=type_travail,
        ).count()

        if nombre >= 2:
            return False, (f"Le maximum est de 2 Superviseurs pour {type_travail}.")

        return True, ""

    if role == "UserMica":
        if queryset.filter(role="UserMica").count() >= 10:
            return False, "Le maximum est de 10 UserMica."

        if personnel and getattr(personnel, "typeTravail", None) != "Mica":
            return False, "Un UserMica doit être lié à un personnel Mica."

        return True, ""

    if role == "UserEntreprise":
        if queryset.filter(role="UserEntreprise").count() >= 10:
            return False, "Le maximum est de 10 UserEntreprise."

        if personnel and getattr(personnel, "typeTravail", None) != "Construction":
            return False, (
                "Un UserEntreprise doit être lié à un personnel "
                "de type Construction."
            )

        return True, ""

    return True, ""


# ============================================================
# LISTE DES UTILISATEURS GALAXY
# ============================================================


def _users_list_queryset(request, model):
    """Prépare la pagination sans modifier la réponse HTTP."""
    queryset = model.objects.select_related("personnel").order_by("username")

    username = request.GET.get("username", "").strip()
    email = request.GET.get("email", "").strip()

    if username:
        queryset = queryset.filter(username__icontains=username)

    if email:
        queryset = queryset.filter(email__icontains=email)

    paginator = Paginator(queryset, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    return page_obj, username, email


# ============================================================
# LISTE GALAXY
# ============================================================

from users.decorators import (
    role_required,
)

# ============================================================
# LISTE DES UTILISATEURS GALAXY
# ============================================================


@role_required("Admin", "Superviseur")
def users_list(request):
    verifier_admin_temporaire(request)

    page_obj, username, email = _users_list_queryset(
        request,
        AppUser,
    )

    return render(
        request,
        "users/list.html",
        {
            "users": page_obj,
            "page_obj": page_obj,
            "username": username,
            "email": email,
            "type_compte": "GALAXY",
            "url_liste": "users:users_list",
            "url_ajout": "users:users_add",
            "url_detail": "users:users_detail",
            "url_modification": "users:users_edit",
            "url_suppression": "users:users_delete",
        },
    )


# ============================================================
# LISTE DES UTILISATEURS ENTREPRISE H
# ============================================================


@h_role_required("Dir", "Compta")
def h_users_list(request):
    page_obj, username, email = _users_list_queryset(
        request,
        H_AppUser,
    )

    return render(
        request,
        "users/list.html",
        {
            "users": page_obj,
            "page_obj": page_obj,
            "username": username,
            "email": email,
            "type_compte": "H",
            "url_liste": "users:h_users_list",
            "url_ajout": "users:h_users_add",
            "url_detail": "users:h_users_detail",
            "url_modification": "users:h_users_edit",
            "url_suppression": "users:h_users_delete",
        },
    )


# ============================================================
# AJOUT GALAXY
# ============================================================


@role_required("Admin")
def users_add(request):
    verifier_admin_temporaire(request)

    if request.method == "POST":
        form = UserForm(request.POST, request.FILES)

        if form.is_valid():
            user = form.save(commit=False)

            autorise, message = verifier_limite_utilisateur(
                user.role,
                personnel=user.personnel,
            )

            if not autorise:
                messages.error(request, message)
            else:
                password = form.cleaned_data.get("password")

                if password:
                    user.password = make_password(password)

                user.save()

                enregistrer_action(
                    request,
                    "CREATE",
                    "Utilisateur",
                    user.pk,
                    nouvelle={
                        "username": user.username,
                        "email": user.email,
                        "role": user.role,
                        "personnel": str(user.personnel) if user.personnel else None,
                        "typeTravail": _personnel_type(user),
                    },
                    description="Création d'un utilisateur GALAXY",
                )

                messages.success(request, "Utilisateur ajouté avec succès.")
                return redirect("users:users_list")

    else:
        form = UserForm()

    return render(
        request,
        "users/form.html",
        {"form": form, "action": "Ajouter"},
    )


# ============================================================
# MODIFICATION GALAXY
# ============================================================


@role_required("Admin", "Superviseur")
def users_edit(request, id):
    user = get_object_or_404(AppUser, pk=id)

    ancienne = {
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "personnel": str(user.personnel) if user.personnel else None,
    }

    if request.method == "POST":
        form = UserForm(request.POST, request.FILES, instance=user)

        if form.is_valid():
            user_modifie = form.save(commit=False)

            autorise, message = verifier_limite_utilisateur(
                user_modifie.role,
                personnel=user_modifie.personnel,
                instance=user,
            )

            if not autorise:
                messages.error(request, message)
            else:
                password = form.cleaned_data.get("password")

                if password:
                    user_modifie.password = make_password(password)
                else:
                    user_modifie.password = user.password

                user_modifie.save()

                enregistrer_action(
                    request,
                    "UPDATE",
                    "Utilisateur",
                    user_modifie.pk,
                    ancienne=ancienne,
                    nouvelle={
                        "username": user_modifie.username,
                        "email": user_modifie.email,
                        "role": user_modifie.role,
                        "personnel": (
                            str(user_modifie.personnel)
                            if user_modifie.personnel
                            else None
                        ),
                    },
                    description="Modification d'un utilisateur GALAXY",
                )

                if request.session.get("user_id") == user_modifie.pk:
                    request.session["username"] = user_modifie.username
                    request.session["role"] = user_modifie.role
                    request.session["photo"] = _photo_url(user_modifie)
                    request.session["typeTravail"] = _personnel_type(user_modifie)
                    request.session.modified = True

                messages.success(request, "Utilisateur modifié avec succès.")
                return redirect("users:users_list")

    else:
        form = UserForm(instance=user)

    return render(
        request,
        "users/form.html",
        {"form": form, "action": "Modifier", "user": user},
    )


# ============================================================
# SUPPRESSION GALAXY
# ============================================================


@role_required("Admin")
@require_http_methods(["GET", "POST"])
def users_delete(request, id):
    user = get_object_or_404(AppUser, pk=id)

    if request.method == "POST":
        if user.role == "Admin" and AppUser.objects.filter(role="Admin").count() <= 1:
            messages.error(
                request,
                "Impossible de supprimer le dernier administrateur GALAXY.",
            )
            return redirect("users:users_list")

        ancienne = {
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "personnel": str(user.personnel) if user.personnel else None,
        }

        enregistrer_action(
            request,
            "DELETE",
            "Utilisateur",
            user.pk,
            ancienne=ancienne,
            description="Suppression d'un utilisateur GALAXY",
        )

        user.delete()
        verifier_admin_temporaire(request)

        messages.success(request, "Utilisateur supprimé avec succès.")
        return redirect("users:users_list")

    return render(request, "users/confirm_delete.html", {"user": user})


# ============================================================
# PROFIL GALAXY : VERIFICATION D'ACCES
# ============================================================


def _verifier_acces_profil(request, user_id):
    return _profil_inaccessible(
        request,
        AppUser,
        user_id,
        "user_id",
        "users:users_detail",
    )


# ============================================================
# DETAIL PROFIL GALAXY
# ============================================================


def users_detail(request, id):
    user = _verifier_acces_profil(request, id)

    if hasattr(user, "status_code"):
        return user

    return render(request, "users/detail.html", {"user": user})


# ============================================================
# PHOTO PROFIL GALAXY
# ============================================================


@require_http_methods(["GET", "POST"])
def change_photo(request, id):
    user = _verifier_acces_profil(request, id)

    if hasattr(user, "status_code"):
        return user

    if request.method == "POST":
        photo = request.FILES.get("photo")

        if not photo:
            messages.error(request, "Veuillez sélectionner une photo.")
        else:
            ancienne = str(user.photo) if user.photo else ""
            user.photo = photo
            user.save(update_fields=["photo"])

            enregistrer_action(
                request,
                "UPDATE",
                "Utilisateur",
                user.pk,
                ancienne={"photo": ancienne},
                nouvelle={"photo": str(user.photo)},
                description="Modification photo utilisateur GALAXY",
            )

            request.session["photo"] = _photo_url(user)
            request.session.modified = True

            messages.success(request, "Photo modifiée avec succès.")
            return redirect("users:users_detail", id=user.pk)

    return render(request, "users/change_photo.html", {"user": user})


# ============================================================
# NOM UTILISATEUR GALAXY
# ============================================================


@require_http_methods(["GET", "POST"])
def change_username(request, id):
    user = _verifier_acces_profil(request, id)

    if hasattr(user, "status_code"):
        return user

    if request.method == "POST":
        ancien_username = user.username
        username = request.POST.get("username", "").strip()

        if not username:
            messages.error(request, "Le nom utilisateur est obligatoire.")
        elif (
            AppUser.objects.filter(username__iexact=username)
            .exclude(pk=user.pk)
            .exists()
        ):
            messages.error(request, "Ce nom utilisateur existe déjà.")
        else:
            user.username = username
            user.save(update_fields=["username"])

            request.session["username"] = username
            request.session.modified = True

            enregistrer_action(
                request,
                "UPDATE",
                "Utilisateur",
                user.pk,
                ancienne={"username": ancien_username},
                nouvelle={"username": username},
                description="Modification nom utilisateur GALAXY",
            )

            messages.success(request, "Nom utilisateur modifié avec succès.")
            return redirect("users:users_detail", id=user.pk)

    return render(request, "users/change_username.html", {"user": user})


# ============================================================
# MOT DE PASSE GALAXY
# ============================================================


@require_http_methods(["GET", "POST"])
def change_password(request, id):
    user = _verifier_acces_profil(request, id)

    if hasattr(user, "status_code"):
        return user

    if request.method == "POST":
        password = request.POST.get("password", "")
        confirmation = request.POST.get("confirmation", "")

        if not password:
            messages.error(request, "Le mot de passe est obligatoire.")
        elif password != confirmation:
            messages.error(request, "Les mots de passe ne correspondent pas.")
        else:
            user.password = make_password(password)
            user.save(update_fields=["password"])

            enregistrer_action(
                request,
                "UPDATE",
                "Utilisateur",
                user.pk,
                description="Modification mot de passe utilisateur GALAXY",
            )

            messages.success(request, "Mot de passe modifié avec succès.")
            return redirect("users:users_detail", id=user.pk)

    return render(request, "users/change_password.html", {"user": user})


# ============================================================
# AJOUT UTILISATEUR ENTREPRISE H
# ============================================================


@h_role_required("Dir", "Compta")
def h_users_add(request):

    if request.method == "POST":
        form = H_UserForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            user = form.save(commit=False)
            password = form.cleaned_data.get("password")

            # Enregistrer le mot de passe sous forme hachée.
            if password:
                user.password = make_password(password)

            user.save()

            enregistrer_action(
                request,
                "CREATE",
                "Utilisateur H",
                user.pk,
                nouvelle={
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "personnel": (str(user.personnel) if user.personnel else None),
                },
                description="Création d'un utilisateur Entreprise H",
            )

            messages.success(
                request,
                "Utilisateur Entreprise H ajouté avec succès.",
            )
            return redirect("users:h_users_list")

    else:
        form = H_UserForm()

    return render(
        request,
        "users/form.html",
        {
            "form": form,
            "action": "Ajouter",
            "type_compte": "H",
        },
    )


# ============================================================
# MODIFICATION UTILISATEUR ENTREPRISE H
# Source : H_Personnel uniquement
# ============================================================


@h_role_required("Dir", "Compta")
def h_users_edit(request, id):

    user = get_object_or_404(H_AppUser, pk=id)

    ancienne = {
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "personnel": (str(user.personnel) if user.personnel else None),
    }

    if request.method == "POST":
        form = H_UserForm(
            request.POST,
            request.FILES,
            instance=user,
        )

        if form.is_valid():
            user_modifie = form.save(commit=False)
            password = form.cleaned_data.get("password")

            # Un champ vide conserve l'ancien mot de passe.
            if password:
                user_modifie.password = make_password(password)
            else:
                user_modifie.password = user.password

            user_modifie.save()

            enregistrer_action(
                request,
                "UPDATE",
                "Utilisateur H",
                user_modifie.pk,
                ancienne=ancienne,
                nouvelle={
                    "username": user_modifie.username,
                    "email": user_modifie.email,
                    "role": user_modifie.role,
                    "personnel": (
                        str(user_modifie.personnel) if user_modifie.personnel else None
                    ),
                },
                description="Modification d'un utilisateur Entreprise H",
            )

            # Actualiser la session si le compte connecté est modifié.
            if request.session.get("h_user_id") == user_modifie.pk:
                request.session["h_username"] = user_modifie.username
                request.session["h_role"] = user_modifie.role
                request.session["h_photo"] = _photo_url(user_modifie)
                request.session.modified = True

            messages.success(
                request,
                "Utilisateur Entreprise H modifié avec succès.",
            )
            return redirect("users:h_users_list")

    else:
        form = H_UserForm(instance=user)

    return render(
        request,
        "users/form.html",
        {
            "form": form,
            "action": "Modifier",
            "user": user,
            "type_compte": "H",
        },
    )


# ============================================================
# SUPPRESSION UTILISATEUR ENTREPRISE H
# ============================================================


@h_role_required("Dir", "Compta")
@require_http_methods(["GET", "POST"])
def h_users_delete(request, id):
    user = get_object_or_404(H_AppUser, pk=id)

    if request.method == "POST":
        if user.role == "Dir" and H_AppUser.objects.filter(role="Dir").count() <= 1:
            messages.error(
                request,
                "Impossible de supprimer le dernier administrateur " "d'Entreprise H.",
            )
            return redirect("users:users_h_list")

        ancienne = {
            "username": user.username,
            "email": getattr(user, "email", None),
            "role": user.role,
            "personnel": (
                str(user.personnel) if getattr(user, "personnel", None) else None
            ),
        }

        enregistrer_action(
            request,
            "DELETE",
            "Utilisateur H",
            user.pk,
            ancienne=ancienne,
            description="Suppression d'un utilisateur Entreprise H",
        )

        user.delete()

        messages.success(
            request,
            "Utilisateur Entreprise H supprimé avec succès.",
        )
        return redirect("users:users_h_list")

    return render(request, "users/confirm_delete.html", {"user": user})


# ============================================================
# PROFIL ENTREPRISE H : VERIFICATION D'ACCES
# ============================================================


def h_verifier_acces_profil(request, user_id):
    return _profil_inaccessible(
        request,
        H_AppUser,
        user_id,
        "h_user_id",
        "users:h_users_detail",
    )


# ============================================================
# DETAIL PROFIL ENTREPRISE H
# ============================================================


def h_users_detail(request, id):
    user = h_verifier_acces_profil(request, id)

    if hasattr(user, "status_code"):
        return user

    return render(request, "users/h_detail.html", {"user": user})


# ============================================================
# PHOTO PROFIL ENTREPRISE H
# ============================================================


@require_http_methods(["GET", "POST"])
def h_change_photo(request, id):
    user = h_verifier_acces_profil(request, id)

    if hasattr(user, "status_code"):
        return user

    if request.method == "POST":
        photo = request.FILES.get("photo")

        if not photo:
            messages.error(request, "Veuillez sélectionner une photo.")
        else:
            ancienne = str(user.photo) if user.photo else ""
            user.photo = photo
            user.save(update_fields=["photo"])

            enregistrer_action(
                request,
                "UPDATE",
                "Utilisateur H",
                user.pk,
                ancienne={"photo": ancienne},
                nouvelle={"photo": str(user.photo)},
                description="Modification photo utilisateur Entreprise H",
            )

            request.session["h_photo"] = _photo_url(user)
            request.session.modified = True

            messages.success(request, "Photo modifiée avec succès.")
            return redirect("users:h_users_detail", id=user.pk)

    return render(request, "users/h_change_photo.html", {"user": user})


# ============================================================
# NOM UTILISATEUR ENTREPRISE H
# ============================================================


@require_http_methods(["GET", "POST"])
def h_change_username(request, id):
    user = h_verifier_acces_profil(request, id)

    if hasattr(user, "status_code"):
        return user

    if request.method == "POST":
        ancien_username = user.username
        username = request.POST.get("username", "").strip()

        if not username:
            messages.error(request, "Le nom utilisateur est obligatoire.")
        elif (
            H_AppUser.objects.filter(username__iexact=username)
            .exclude(pk=user.pk)
            .exists()
        ):
            messages.error(request, "Ce nom utilisateur existe déjà.")
        else:
            user.username = username
            user.save(update_fields=["username"])

            request.session["h_username"] = username
            request.session.modified = True

            enregistrer_action(
                request,
                "UPDATE",
                "Utilisateur H",
                user.pk,
                ancienne={"username": ancien_username},
                nouvelle={"username": username},
                description="Modification nom utilisateur Entreprise H",
            )

            messages.success(request, "Nom utilisateur modifié avec succès.")
            return redirect("users:h_users_detail", id=user.pk)

    return render(request, "users/h_change_username.html", {"user": user})


# ============================================================
# MOT DE PASSE ENTREPRISE H
# ============================================================


@require_http_methods(["GET", "POST"])
def h_change_password(request, id):
    user = h_verifier_acces_profil(request, id)

    if hasattr(user, "status_code"):
        return user

    if request.method == "POST":
        password = request.POST.get("password", "")
        confirmation = request.POST.get("confirmation", "")

        if not password:
            messages.error(request, "Le mot de passe est obligatoire.")
        elif password != confirmation:
            messages.error(request, "Les mots de passe ne correspondent pas.")
        else:
            user.password = make_password(password)
            user.save(update_fields=["password"])

            enregistrer_action(
                request,
                "UPDATE",
                "Utilisateur H",
                user.pk,
                description="Modification mot de passe utilisateur Entreprise H",
            )

            messages.success(request, "Mot de passe modifié avec succès.")
            return redirect("users:h_users_detail", id=user.pk)

    return render(
        request,
        "users/h_change_password.html",
        {"user": user},
    )
