from django.urls import path

from . import views

app_name = "personnel"


urlpatterns = [
    # ============================================================
    # URLS POUR LA GESTION DES PERSONNELS ENTREPRISE G
    # ============================================================
    path("", views.personnel_list, name="personnel_list"),
    path("ajouter/", views.personnel_add, name="personnel_add"),
    path("<int:id>/", views.personnel_detail, name="personnel_detail"),
    path("<int:id>/modifier/", views.personnel_edit, name="personnel_edit"),
    path("<int:id>/supprimer/", views.personnel_delete, name="personnel_delete"),
    # ============================================================
    # URLS POUR LA GESTION DES PERSONNELS ENTREPRISE H
    # ============================================================
    path("h_personnels/", views.h_personnel_list, name="h_personnel_list"),
    path("h_personnels/ajouter/", views.h_personnel_create, name="h_personnel_create"),
    path("h_personnels/<int:id>/", views.h_personnel_detail, name="h_personnel_detail"),
    path(
        "h_personnels/<int:id>/modifier/",
        views.h_personnel_update,
        name="h_personnel_update",
    ),
    path(
        "h_personnels/<int:id>/supprimer/",
        views.h_personnel_delete,
        name="h_personnel_delete",
    ),
]
