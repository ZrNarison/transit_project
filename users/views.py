from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib import messages
from django.contrib.auth.hashers import (
    make_password,
    check_password
)
from django.core.paginator import Paginator

from .models import AppUser
from .forms import UserForm

from audit.utils import enregistrer_action
from logs.utils import enregistrer_log


# ============================================================
# ADMIN TEMPORAIRE
# ============================================================

def creer_admin_temporaire():
    """
    Crée automatiquement un Admin temporaire si aucun Admin
    n'existe dans la base de données.

    Identifiant :
        Admin

    Mot de passe initial :
        Admin

    Le mot de passe est stocké sous forme hashée.
    """

    if not AppUser.objects.filter(role="Admin").exists():

        # Si le username Admin existe déjà avec un autre rôle,
        # on ne peut pas créer l'Admin temporaire avec le même nom.
        if AppUser.objects.filter(username="Admin").exists():

            return None

        admin = AppUser.objects.create(
            username="Admin",
            email="",
            password=make_password("Admin"),
            role="Admin",
            personnel=None
        )

        return admin

    return None


# ============================================================
# VERIFICATION / CREATION ADMIN
# ============================================================

def verifier_admin_temporaire(request=None):
    """
    Vérifie qu'il existe toujours au moins un Admin.

    Si aucun Admin n'existe, création automatique de :
        Admin / Admin
    """

    admin = creer_admin_temporaire()

    if admin and request:

        messages.warning(
            request,
            "Aucun administrateur n'existait. "
            "Un compte Admin temporaire a été créé."
        )

    return admin


# ============================================================
# VERIFICATION DES LIMITES
# ============================================================

def verifier_limite_utilisateur(role, personnel=None, instance=None):
    """
    Vérifie les limites d'inscription.

    Admin :
        maximum 2

    Superviseur :
        maximum 2 Mica
        maximum 2 Construction

    UserMica :
        maximum 10

    UserEntreprise :
        maximum 10
    """

    queryset = AppUser.objects.all()

    # Modification :
    # on exclut l'utilisateur actuellement modifié.
    if instance and instance.pk:
        queryset = queryset.exclude(pk=instance.pk)

    # --------------------------------------------------------
    # ADMIN
    # --------------------------------------------------------

    if role == "Admin":

        nombre_admin = queryset.filter(
            role="Admin"
        ).count()

        if nombre_admin >= 2:

            return False, (
                "Impossible de créer cet administrateur. "
                "Le nombre maximum est de 2 Admin."
            )

        return True, ""

    # --------------------------------------------------------
    # SUPERVISEUR
    # --------------------------------------------------------

    if role == "Superviseur":

        if not personnel:

            return False, (
                "Un Superviseur doit être lié à un personnel."
            )

        type_travail = getattr(
            personnel,
            "typeTravail",
            None
        )

        if type_travail not in [
            "Mica",
            "Construction"
        ]:

            return False, (
                "Le type de travail du personnel doit être "
                "Mica ou Construction."
            )

        nombre_superviseurs = queryset.filter(
            role="Superviseur",
            personnel__typeTravail=type_travail
        ).count()

        if nombre_superviseurs >= 2:

            return False, (
                f"Impossible de créer ce Superviseur. "
                f"Le maximum est de 2 Superviseurs "
                f"pour {type_travail}."
            )

        return True, ""

    # --------------------------------------------------------
    # USER MICA
    # --------------------------------------------------------

    if role == "UserMica":

        nombre_mica = queryset.filter(
            role="UserMica"
        ).count()

        if nombre_mica >= 10:

            return False, (
                "Impossible de créer cet utilisateur. "
                "Le maximum est de 10 UserMica."
            )

        if personnel:

            type_travail = getattr(
                personnel,
                "typeTravail",
                None
            )

            if type_travail != "Mica":

                return False, (
                    "Un UserMica doit être lié à un "
                    "personnel de type Mica."
                )

        return True, ""

    # --------------------------------------------------------
    # USER ENTREPRISE
    # --------------------------------------------------------

    if role == "UserEntreprise":

        nombre_entreprise = queryset.filter(
            role="UserEntreprise"
        ).count()

        if nombre_entreprise >= 10:

            return False, (
                "Impossible de créer cet utilisateur. "
                "Le maximum est de 10 UserEntreprise."
            )

        if personnel:

            type_travail = getattr(
                personnel,
                "typeTravail",
                None
            )

            if type_travail != "Construction":

                return False, (
                    "Un UserEntreprise doit être lié à un "
                    "personnel de type Construction."
                )

        return True, ""

    return True, ""


# ============================================================
# LOGIN
# ============================================================

def users_login(request):

    # --------------------------------------------------------
    # Vérifier qu'il existe au moins un Admin
    # --------------------------------------------------------

    verifier_admin_temporaire(request)

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        if not username or not password:

            messages.error(
                request,
                "Veuillez saisir le nom utilisateur et le mot de passe."
            )

            return render(
                request,
                "users/login.html"
            )

        try:

            user = (
                AppUser.objects
                .select_related("personnel")
                .get(
                    username=username
                )
            )

            if check_password(
                password,
                user.password
            ):

                request.session["user_id"] = user.id

                request.session["username"] = (
                    user.username
                )

                request.session["role"] = (
                    user.role
                )

                request.session["photo"] = (
                    user.photo.url
                    if user.photo
                    else None
                )

                if user.personnel:

                    request.session["typeTravail"] = (
                        user.personnel.typeTravail
                    )

                else:

                    request.session["typeTravail"] = None

                enregistrer_log(
                    message=(
                        f"Connexion utilisateur : "
                        f"{user.username}"
                    ),
                    level="INFO",
                    module="AUTH",
                    ip_address=request.META.get(
                        "REMOTE_ADDR"
                    )
                )

                return redirect("/")

            messages.error(
                request,
                "Mot de passe incorrect."
            )

        except AppUser.DoesNotExist:

            messages.error(
                request,
                "Utilisateur introuvable."
            )

    return render(
        request,
        "users/login.html"
    )


# ============================================================
# LOGOUT
# ============================================================

def users_logout(request):

    username = request.session.get(
        "username",
        "Utilisateur"
    )

    enregistrer_log(
        message=(
            f"Déconnexion utilisateur : "
            f"{username}"
        ),
        level="INFO",
        module="AUTH",
        ip_address=request.META.get(
            "REMOTE_ADDR"
        )
    )

    request.session.flush()

    return redirect(
        "users:login"
    )


# ============================================================
# LISTE UTILISATEURS
# ============================================================

def users_list(request):

    # Toujours garantir l'existence d'un Admin.
    verifier_admin_temporaire(request)

    queryset = (
        AppUser.objects
        .select_related("personnel")
        .order_by("username")
    )

    username = request.GET.get(
        "username",
        ""
    ).strip()

    email = request.GET.get(
        "email",
        ""
    ).strip()

    if username:

        queryset = queryset.filter(
            username__icontains=username
        )

    if email:

        queryset = queryset.filter(
            email__icontains=email
        )

    paginator = Paginator(
        queryset,
        10
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "users/list.html",
        {
            "users": page_obj,
            "page_obj": page_obj,
            "username": username,
            "email": email,
        }
    )


# ============================================================
# AJOUT UTILISATEUR
# ============================================================

def users_add(request):

    # Si aucun Admin existe, on le crée avant toute chose.
    verifier_admin_temporaire(request)

    if request.method == "POST":

        form = UserForm(
            request.POST,
            request.FILES
        )

        if form.is_valid():

            user = form.save(
                commit=False
            )

            role = user.role
            personnel = user.personnel

            # ------------------------------------------------
            # VERIFICATION LIMITE
            # ------------------------------------------------

            autorise, message = verifier_limite_utilisateur(
                role,
                personnel=personnel
            )

            if not autorise:

                messages.error(
                    request,
                    message
                )

                return render(
                    request,
                    "users/form.html",
                    {
                        "form": form,
                        "action": "Ajouter"
                    }
                )

            # ------------------------------------------------
            # MOT DE PASSE
            # ------------------------------------------------

            password = form.cleaned_data.get(
                "password"
            )

            if password:

                user.password = make_password(
                    password
                )

            # ------------------------------------------------
            # SAUVEGARDE
            # ------------------------------------------------

            user.save()

            # ------------------------------------------------
            # AUDIT
            # ------------------------------------------------

            enregistrer_action(
                request,
                "CREATE",
                "Utilisateur",
                user.id,
                nouvelle={
                    "username": user.username,
                    "email": user.email,
                    "role": user.role,
                    "personnel": (
                        str(user.personnel)
                        if user.personnel
                        else None
                    ),
                    "typeTravail": (
                        user.personnel.typeTravail
                        if user.personnel
                        else None
                    ),
                },
                description=(
                    "Création d'un utilisateur"
                )
            )

            messages.success(
                request,
                "Utilisateur ajouté avec succès."
            )

            return redirect(
                "users:users_list"
            )

    else:

        form = UserForm()

    return render(
        request,
        "users/form.html",
        {
            "form": form,
            "action": "Ajouter"
        }
    )


# ============================================================
# DETAIL
# ============================================================

def users_detail(request, id):

    user = get_object_or_404(
        AppUser.objects.select_related(
            "personnel"
        ),
        id=id
    )

    return render(
        request,
        "users/detail.html",
        {
            "user": user
        }
    )


# ============================================================
# MODIFICATION
# ============================================================

def users_edit(request, id):

    user = get_object_or_404(
        AppUser,
        id=id
    )

    ancienne = {
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "personnel": (
            str(user.personnel)
            if user.personnel
            else None
        ),
    }

    if request.method == "POST":

        form = UserForm(
            request.POST,
            request.FILES,
            instance=user
        )

        if form.is_valid():

            user_modifie = form.save(
                commit=False
            )

            role = user_modifie.role
            personnel = user_modifie.personnel

            # ------------------------------------------------
            # VERIFICATION DES LIMITES
            # ------------------------------------------------

            autorise, message = verifier_limite_utilisateur(
                role,
                personnel=personnel,
                instance=user
            )

            if not autorise:

                messages.error(
                    request,
                    message
                )

                return render(
                    request,
                    "users/form.html",
                    {
                        "form": form,
                        "action": "Modifier",
                        "user": user
                    }
                )

            # ------------------------------------------------
            # MOT DE PASSE
            # ------------------------------------------------

            password = form.cleaned_data.get(
                "password"
            )

            if password:

                user_modifie.password = make_password(
                    password
                )

            else:

                # Le formulaire ne doit pas effacer
                # le mot de passe existant.
                user_modifie.password = user.password

            user_modifie.save()

            # ------------------------------------------------
            # AUDIT
            # ------------------------------------------------

            enregistrer_action(
                request,
                "UPDATE",
                "Utilisateur",
                user_modifie.id,
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
                description=(
                    "Modification d'un utilisateur"
                )
            )

            # ------------------------------------------------
            # ACTUALISATION SESSION
            # ------------------------------------------------

            if request.session.get(
                "user_id"
            ) == user_modifie.id:

                request.session["username"] = (
                    user_modifie.username
                )

                request.session["role"] = (
                    user_modifie.role
                )

                request.session["photo"] = (
                    user_modifie.photo.url
                    if user_modifie.photo
                    else None
                )

                request.session["typeTravail"] = (
                    user_modifie.personnel.typeTravail
                    if user_modifie.personnel
                    else None
                )

                request.session.modified = True

            messages.success(
                request,
                "Utilisateur modifié avec succès."
            )

            return redirect(
                "users:users_list"
            )

    else:

        form = UserForm(
            instance=user
        )

    return render(
        request,
        "users/form.html",
        {
            "form": form,
            "action": "Modifier",
            "user": user
        }
    )


# ============================================================
# SUPPRESSION
# ============================================================

def users_delete(request, id):

    user = get_object_or_404(
        AppUser,
        id=id
    )

    # --------------------------------------------------------
    # PROTECTION :
    # impossible de supprimer le dernier Admin
    # --------------------------------------------------------

    if user.role == "Admin":

        nombre_admin = AppUser.objects.filter(
            role="Admin"
        ).count()

        if nombre_admin <= 1:

            messages.error(
                request,
                "Impossible de supprimer le dernier administrateur. "
                "Le système doit toujours conserver au moins un Admin."
            )

            return redirect(
                "users:users_list"
            )

    # --------------------------------------------------------
    # SUPPRESSION
    # --------------------------------------------------------

    if request.method == "POST":

        ancienne = {
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "personnel": (
                str(user.personnel)
                if user.personnel
                else None
            ),
        }

        enregistrer_action(
            request,
            "DELETE",
            "Utilisateur",
            user.id,
            ancienne=ancienne,
            description=(
                "Suppression d'un utilisateur"
            )
        )

        user.delete()

        # ----------------------------------------------------
        # Après suppression, vérifier qu'il existe un Admin.
        # Si le dernier Admin a été supprimé, on recrée
        # automatiquement Admin / Admin.
        # ----------------------------------------------------

        verifier_admin_temporaire(request)

        messages.success(
            request,
            "Utilisateur supprimé avec succès."
        )

        return redirect(
            "users:users_list"
        )

    return render(
        request,
        "users/confirm_delete.html",
        {
            "user": user
        }
    )


# ============================================================
# CHANGER PHOTO
# ============================================================

def change_photo(request, id):

    user = get_object_or_404(
        AppUser,
        id=id
    )

    if request.method == "POST":

        photo = request.FILES.get(
            "photo"
        )

        if photo:

            ancienne = str(
                user.photo
            )

            user.photo = photo

            user.save()

            enregistrer_action(
                request,
                "UPDATE",
                "Utilisateur",
                user.id,
                ancienne={
                    "photo": ancienne
                },
                nouvelle={
                    "photo": str(user.photo)
                },
                description=(
                    "Modification photo utilisateur"
                )
            )

            if request.session.get(
                "user_id"
            ) == user.id:

                request.session["photo"] = (
                    user.photo.url
                )

                request.session.modified = True

            messages.success(
                request,
                "Photo modifiée avec succès."
            )

            return redirect(
                "users:users_detail",
                id=id
            )

    return render(
        request,
        "users/change_photo.html",
        {
            "user": user
        }
    )


# ============================================================
# CHANGER USERNAME
# ============================================================

def change_username(request, id):

    user = get_object_or_404(
        AppUser,
        id=id
    )

    if request.method == "POST":

        ancien_username = user.username

        username = request.POST.get(
            "username",
            ""
        ).strip()

        if not username:

            messages.error(
                request,
                "Le nom utilisateur est obligatoire."
            )

        elif AppUser.objects.filter(
            username=username
        ).exclude(
            id=id
        ).exists():

            messages.error(
                request,
                "Ce nom utilisateur existe déjà."
            )

        else:

            user.username = username

            user.save()

            enregistrer_action(
                request,
                "UPDATE",
                "Utilisateur",
                user.id,
                ancienne={
                    "username": ancien_username
                },
                nouvelle={
                    "username": username
                },
                description=(
                    "Modification nom utilisateur"
                )
            )

            if request.session.get(
                "user_id"
            ) == user.id:

                request.session["username"] = (
                    username
                )

            messages.success(
                request,
                "Nom utilisateur modifié."
            )

            return redirect(
                "users:users_detail",
                id=id
            )

    return render(
        request,
        "users/change_username.html",
        {
            "user": user
        }
    )


# ============================================================
# CHANGER MOT DE PASSE
# ============================================================

def change_password(request, id):

    user = get_object_or_404(
        AppUser,
        id=id
    )

    if request.method == "POST":

        password = request.POST.get(
            "password",
            ""
        )

        confirmation = request.POST.get(
            "confirmation",
            ""
        )

        if not password:

            messages.error(
                request,
                "Le mot de passe est obligatoire."
            )

        elif password != confirmation:

            messages.error(
                request,
                "Les mots de passe ne correspondent pas."
            )

        else:

            user.password = make_password(
                password
            )

            user.save()

            enregistrer_action(
                request,
                "UPDATE",
                "Utilisateur",
                user.id,
                description=(
                    "Modification mot de passe utilisateur"
                )
            )

            messages.success(
                request,
                "Mot de passe modifié avec succès."
            )

            return redirect(
                "users:users_detail",
                id=id
            )

    return render(
        request,
        "users/change_password.html",
        {
            "user": user
        }
    )
