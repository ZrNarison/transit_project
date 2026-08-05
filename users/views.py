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



# ==================================================
# LOGIN
# ==================================================

def users_login(request):

    if request.method == "POST":

        username = request.POST.get(
            "username"
        )

        password = request.POST.get(
            "password"
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
                request.session["username"] = user.username
                request.session["role"] = user.role

                request.session["photo"] = (
                    user.photo.url
                    if user.photo
                    else None
                )
                enregistrer_log(
                    message=f"Connexion utilisateur : {user.username}",
                    level="INFO",
                    module="AUTH",
                    ip_address=request.META.get("REMOTE_ADDR")
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




# ==================================================
# LOGOUT
# ==================================================

def users_logout(request):

    username = request.session.get(
        "username",
        "Utilisateur"
    )


    enregistrer_log(
        message=f"Déconnexion utilisateur : {username}",
        level="INFO",
        module="AUTH",
        ip_address=request.META.get("REMOTE_ADDR")
    )


    request.session.flush()


    return redirect(
        "users:login"
    )




# ==================================================
# LISTE UTILISATEURS
# ==================================================

def users_list(request):

    queryset = (
        AppUser.objects
        .select_related(
            "personnel"
        )
        .order_by(
            "username"
        )
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





# ==================================================
# AJOUT UTILISATEUR
# ==================================================

def users_add(request):

    if request.method == "POST":

        form = UserForm(
            request.POST,
            request.FILES
        )


        if form.is_valid():

            user = form.save(
                commit=False
            )


            password = form.cleaned_data.get(
                "password"
            )


            if password:

                user.password = make_password(
                    password
                )


            user.save()


            enregistrer_action(
                request,
                "CREATE",
                "Utilisateur",
                user.username,
                nouvelle={
                    "username": user.username,
                    "email": user.email,
                    "role": user.role
                },
                description="Création d'un utilisateur"
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





# ==================================================
# DETAIL
# ==================================================

def users_detail(request, id):

    user = get_object_or_404(
        AppUser,
        id=id
    )


    return render(
        request,
        "users/detail.html",
        {
            "user": user
        }
    )





# ==================================================
# MODIFICATION
# ==================================================

def users_edit(request, id):

    user = get_object_or_404(
        AppUser,
        id=id
    )


    ancienne = {
        "username": user.username,
        "email": user.email,
        "role": user.role
    }


    if request.method == "POST":


        form = UserForm(
            request.POST,
            request.FILES,
            instance=user
        )


        if form.is_valid():


            user = form.save(
                commit=False
            )


            password = form.cleaned_data.get(
                "password"
            )


            if password:

                user.password = make_password(
                    password
                )


            user.save()



            enregistrer_action(
                request,
                "UPDATE",
                "Utilisateur",
                user.username,
                ancienne=ancienne,
                nouvelle={
                    "username": user.username,
                    "email": user.email,
                    "role": user.role
                },
                description="Modification d'un utilisateur"
            )



            if request.session.get(
                "user_id"
            ) == user.id:


                request.session["username"] = user.username
                request.session["role"] = user.role

                request.session["photo"] = (
                    user.photo.url
                    if user.photo
                    else None
                )



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
            "action": "Modifier"
        }
    )





# ==================================================
# SUPPRESSION
# ==================================================

def users_delete(request, id):

    user = get_object_or_404(
        AppUser,
        id=id
    )


    if request.method == "POST":


        ancienne = {
            "username": user.username,
            "email": user.email,
            "role": user.role
        }


        enregistrer_action(
            request,
            "DELETE",
            "Utilisateur",
            user.username,
            ancienne=ancienne,
            description="Suppression d'un utilisateur"
        )


        user.delete()



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





# ==================================================
# CHANGER PHOTO
# ==================================================

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


            ancienne = str(user.photo)


            user.photo = photo

            user.save()



            enregistrer_action(
                request,
                "UPDATE",
                "Utilisateur",
                user.username,
                ancienne={
                    "photo": ancienne
                },
                nouvelle={
                    "photo": str(user.photo)
                },
                description="Modification photo utilisateur"
            )



            if request.session.get(
                "user_id"
            ) == user.id:


                request.session["photo"] = user.photo.url
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





# ==================================================
# CHANGER USERNAME
# ==================================================

def change_username(request, id):

    user = get_object_or_404(
        AppUser,
        id=id
    )


    if request.method == "POST":


        ancien_username = user.username


        username = request.POST.get(
            "username"
        ).strip()



        if AppUser.objects.filter(
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
                user.username,
                ancienne={
                    "username": ancien_username
                },
                nouvelle={
                    "username": username
                },
                description="Modification nom utilisateur"
            )



            if request.session.get(
                "user_id"
            ) == user.id:

                request.session["username"] = username



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





# ==================================================
# CHANGER MOT DE PASSE
# ==================================================

def change_password(request, id):

    user = get_object_or_404(
        AppUser,
        id=id
    )



    if request.method == "POST":


        password = request.POST.get(
            "password"
        )


        confirmation = request.POST.get(
            "confirmation"
        )



        if password != confirmation:


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
                user.username,
                description="Modification mot de passe utilisateur"
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