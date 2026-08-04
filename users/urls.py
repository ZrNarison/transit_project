from django.urls import path
from . import views

app_name = "users"

urlpatterns = [
    path("login/",    views.users_login,    name="login"),
    path("logout/",    views.users_logout,    name="logout"),
    path("", views.users_liste, name="users_liste"),
    path("ajouter/", views.users_add, name="users_add"),
    path("<int:id>/", views.users_detail, name="users_detail"),
    path("<int:id>/modifier/", views.users_edit, name="users_edit"),
    path("<int:id>/supprimer/", views.users_delete, name="users_delete"),
    path(
    "profil/<int:id>/photo/",
    views.change_photo,
    name="change_photo"
),

path(
    "profil/<int:id>/username/",
    views.change_username,
    name="change_username"
),

path(
    "profil/<int:id>/password/",
    views.change_password,
    name="change_password"
),
]