from django.urls import path

from . import views

app_name = "users"

urlpatterns = [
    # ============================================================
    # AUTHENTIFICATION COMMUNE
    # ============================================================
    path("login/", views.users_login, name="login"),
    path("logout/", views.users_logout, name="logout"),
    # ============================================================
    # GESTION DES UTILISATEURS ACTIFS (AppUser)
    # ============================================================
    path("", views.users_list, name="users_list"),
    path("ajouter/", views.users_add, name="users_add"),
    path("<int:id>/", views.users_detail, name="users_detail"),
    path("<int:id>/modifier/", views.users_edit, name="users_edit"),
    path("<int:id>/supprimer/", views.users_delete, name="users_delete"),
    # Profil actif
    path(
        "profil/<int:id>/photo/",
        views.change_photo,
        name="change_photo",
    ),
    path(
        "profil/<int:id>/username/",
        views.change_username,
        name="change_username",
    ),
    path(
        "profil/<int:id>/password/",
        views.change_password,
        name="change_password",
    ),
    # ============================================================
    # GESTION DES UTILISATEURS HISTORIQUES (H_AppUser)
    # ============================================================
    path("historique/utilisateurs/", views.h_users_list, name="h_users_list"),
    path("historique/utilisateurs/ajouter/", views.h_users_add, name="h_users_add"),
    path(
        "historique/utilisateurs/<int:id>/",
        views.h_users_detail,
        name="h_users_detail",
    ),
    path(
        "historique/utilisateurs/<int:id>/modifier/",
        views.h_users_edit,
        name="h_users_edit",
    ),
    path(
        "historique/utilisateurs/<int:id>/supprimer/",
        views.h_users_delete,
        name="h_users_delete",
    ),
    # Profil historique
    path(
        "historique/profil/<int:id>/photo/",
        views.h_change_photo,
        name="h_change_photo",
    ),
    path(
        "historique/profil/<int:id>/username/",
        views.h_change_username,
        name="h_change_username",
    ),
    path(
        "historique/profil/<int:id>/password/",
        views.h_change_password,
        name="h_change_password",
    ),
    # Déconnexion historique, si nécessaire séparément
    path("historique/logout/", views.h_logout, name="h_logout"),
]
