from django.urls import path

from . import views

app_name = "materielsort"

urlpatterns = [
    # ==========================================
    # GALAXY
    # ==========================================
    path(
        "",
        views.materielsort_list,
        name="materielsort_list",
    ),
    path(
        "ajouter/",
        views.materielsort_add,
        name="materielsort_add",
    ),
    path(
        "<int:id>/",
        views.materielsort_detail,
        name="materielsort_detail",
    ),
    path(
        "<int:id>/modifier/",
        views.materielsort_edit,
        name="materielsort_edit",
    ),
    path(
        "<int:id>/supprimer/",
        views.materielsort_delete,
        name="materielsort_delete",
    ),
    # ==========================================
    # MCCR / ENTREPRISE H
    # ==========================================
    path(
        "mccr/",
        views.h_materielsort_list,
        name="h_materielsort_list",
    ),
    path(
        "mccr/ajouter/",
        views.h_materielsort_add,
        name="h_materielsort_add",
    ),
    path(
        "mccr/<int:id>/",
        views.h_materielsort_detail,
        name="h_materielsort_detail",
    ),
    path(
        "mccr/<int:id>/modifier/",
        views.h_materielsort_edit,
        name="h_materielsort_edit",
    ),
    path(
        "mccr/<int:id>/supprimer/",
        views.h_materielsort_delete,
        name="h_materielsort_delete",
    ),
]
