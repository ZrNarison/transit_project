from django.shortcuts import (
    render,
    get_object_or_404,
    redirect
)

from django.contrib import messages
from django.contrib.auth.hashers import (
    make_password,
    check_password
)

from .models import AppUser
from .forms import UserForm
from .decorators import role_required


# ==========================
# LOGIN
# ==========================
def users_login(request):

    if request.method == "POST":

        username = request.POST.get("username")
        password = request.POST.get("password")

        try:

            user = AppUser.objects.select_related(
                "personnel"
            ).get(
                username=username
            )
            if check_password(password, user.password):
                request.session["user_id"] = user.id
                request.session["username"] = user.username
            
                request.session["role"] = user.role

                if user.photo:

                    request.session["photo"] = (
                        user.photo.url
                    )

                else:

                    request.session["photo"] = None

                return redirect("/")


            else:

                messages.error(
                    request,
                    "Mot de passe incorrect."
                )


        except AppUser.DoesNotExist:

            messages.error(
                request,
                "Nom d'utilisateur introuvable."
            )


    return render(
        request,
        "users/login.html"
    )

# ==========================
# DECONNEXION
# ==========================

def users_logout(request):

    request.session.flush()

    return redirect(
        "users:login"
    )





# ==========================
# LISTE
# ==========================
def users_liste(request):

    queryset = AppUser.objects.select_related(
        "personnel"
    ).all()


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



    return render(
        request,
        "users/list.html",
        {
            "users": queryset,
            "username": username,
            "email": email,
        }
    )





# ==========================
# AJOUT
# ==========================

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


            user.password = make_password(
                form.cleaned_data["password"]
            )


            user.save()


            messages.success(
                request,
                "Utilisateur ajouté avec succès."
            )


            return redirect(
                "users:users_liste"
            )


    else:

        form = UserForm()


    return render(
        request,
        "users/form.html",
        {
            "form": form
        }
    )

# ==========================
# DETAIL
# ==========================
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





# ==========================
# MODIFICATION
# ==========================
def users_edit(request, id):

    user = get_object_or_404(
        AppUser,
        id=id
    )



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



            messages.success(
                request,
                "Utilisateur modifié avec succès."
            )


            return redirect(
                "users:users_liste"
            )



    else:

        form = UserForm(
            instance=user
        )



    return render(
        request,
        "users/form.html",
        {
            "form": form
        }
    )





# ==========================
# SUPPRESSION
# ==========================

def users_delete(request, id):

    user = get_object_or_404(
        AppUser,
        id=id
    )


    if request.method == "POST":

        user.delete()


        messages.success(
            request,
            "Utilisateur supprimé."
        )


        return redirect(
            "users:users_liste"
        )



    return render(
        request,
        "users/confirm_delete.html",
        {
            "user": user
        }
    )

# ==========================
# CHANGER PHOTO
# ==========================
def change_photo(request, id):

    user = get_object_or_404(
        AppUser,
        id=id
    )


    if request.method == "POST":

        photo = request.FILES.get("photo")
        if photo:
            user.photo = photo
            user.save()


            if request.session.get("user_id") == user.id:

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
# ==========================
# CHANGER USERNAME
# =========================
def change_username(request, id):

    user = get_object_or_404(
        AppUser,
        id=id
    )


    if request.method == "POST":

        username = request.POST.get(
            "username"
        )


        if username:


            user.username = username

            user.save()



            if request.session.get("user_id") == user.id:

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





# ==========================
# CHANGER MOT DE PASSE
# ==========================

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



        if password == confirmation:


            user.password = make_password(
                password
            )


            user.save()



            messages.success(
                request,
                "Mot de passe modifié."
            )


            return redirect(
                "users:users_detail",
                id=id
            )



        else:


            messages.error(
                request,
                "Les mots de passe ne correspondent pas."
            )



    return render(
        request,
        "users/change_password.html",
        {
            "user": user
        }
    )