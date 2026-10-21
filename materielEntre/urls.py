from django.urls import path

from . import views

app_name = "materielEntre"

urlpatterns = [
    # ==========================================
    # GALAXY
    # ==========================================
    path(
        "",
        views.materielEntre_list,
        name="materielEntre_list",
    ),
    path(
        "ajouter/",
        views.materielEntre_add,
        name="materielEntre_add",
    ),
    path(
        "detail/<int:id>/",
        views.materielEntre_detail,
        name="materielEntre_detail",
    ),
    path(
        "modifier/<int:id>/",
        views.materielEntre_edit,
        name="materielEntre_edit",
    ),
    path(
        "supprimer/<int:id>/",
        views.materielEntre_delete,
        name="materielEntre_delete",
    ),
    # ==========================================
    # MCCR / ENTREPRISE H
    # ==========================================
    path(
        "mccr/",
        views.h_materielEntre_list,
        name="h_materielEntre_list",
    ),
    path(
        "mccr/ajouter/",
        views.h_materielEntre_add,
        name="h_materielEntre_add",
    ),
    path(
        "mccr/detail/<int:id>/",
        views.h_materielEntre_detail,
        name="h_materielEntre_detail",
    ),
    path(
        "mccr/modifier/<int:id>/",
        views.h_materielEntre_edit,
        name="h_materielEntre_edit",
    ),
    path(
        "mccr/supprimer/<int:id>/",
        views.h_materielEntre_delete,
        name="h_materielEntre_delete",
    ),
]
