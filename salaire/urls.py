from django.urls import path

from . import views

app_name = "salaire"

urlpatterns = [
    # ============================================================
    # GALAXY
    # ============================================================
    path(
        "",
        views.salaire_list,
        name="salaire_list",
    ),
    path(
        "ajouter/",
        views.salaire_add,
        name="salaire_add",
    ),
    path(
        "<int:id>/modifier/",
        views.salaire_edit,
        name="salaire_edit",
    ),
    path(
        "<int:id>/supprimer/",
        views.salaire_delete,
        name="salaire_delete",
    ),
    # ============================================================
    # ENTREPRISE H
    # ============================================================
    path(
        "entreprise-h/",
        views.h_salaire_list,
        name="h_salaire_list",
    ),
    path(
        "entreprise-h/ajouter/",
        views.h_salaire_add,
        name="h_salaire_add",
    ),
    path(
        "entreprise-h/<int:id>/modifier/",
        views.h_salaire_edit,
        name="h_salaire_edit",
    ),
    path(
        "entreprise-h/<int:id>/supprimer/",
        views.h_salaire_delete,
        name="h_salaire_delete",
    ),
]
