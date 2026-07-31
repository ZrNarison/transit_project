from django.shortcuts import render, get_object_or_404, redirect
from .models import AppUser
from django.contrib.auth.hashers import make_password

def users_liste(request):
    queryset = AppUser.objects.all()
    username = request.GET.get('username', '').strip()
    email = request.GET.get('email', '').strip()

    if username:
        queryset = queryset.filter(username__icontains=username)
    if email:
        queryset = queryset.filter(email__icontains=email)

    return render(request, "users/list.html", {
        "users": queryset,
        "username": username,
        "email": email,
    })


def users_add(request):
    if request.method == "POST":
        password = make_password(request.POST.get("password"))

        AppUser.objects.create(
            username=request.POST.get("username"),
            email=request.POST.get("email"),
            password=password
        )
        return redirect("users:users_liste")

    return render(request, "users/add.html")

def users_detail(request, id):
    user = get_object_or_404(AppUser, id=id)
    return render(request, "users/detail.html", {"user": user})


def users_edit(request, id):
    user = get_object_or_404(AppUser, id=id)

    if request.method == "POST":
        user.username = request.POST.get("username")
        user.email = request.POST.get("email")
        user.password = request.POST.get("password")
        user.save()
        return redirect("users:users_liste")

    return render(request, "users/edit.html", {"user": user})


def users_delete(request, id):
    user = get_object_or_404(AppUser, id=id)
    user.delete()
    return redirect("users:users_liste")