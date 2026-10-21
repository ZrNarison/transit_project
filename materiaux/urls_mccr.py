from django.urls import include, path

from . import views_mccr

app_name = "mccr_materiaux"

urlpatterns = [
    # Dashboard
    path(
        "",
        views_mccr.dashboard_mccr,
        name="dashboard_mccr",
    ),
    # CRUD des matériaux
    path(
        "materiaux/",
        views_mccr.materiaux_mccr_list,
        name="materiaux_list",
    ),
    path(
        "materiaux/ajouter/",
        views_mccr.materiau_mccr_create,
        name="materiau_create",
    ),
    path(
        "materiaux/<int:pk>/modifier/",
        views_mccr.materiau_mccr_update,
        name="materiau_update",
    ),
    path(
        "materiaux/<int:pk>/supprimer/",
        views_mccr.materiau_mccr_delete,
        name="materiau_delete",
    ),
    # CRUD des mouvements : entrées, sorties et retours
    path(
        "mouvements/",
        views_mccr.mouvements_mccr_list,
        name="mouvements_list",
    ),
    path(
        "mouvements/ajouter/",
        views_mccr.mouvement_mccr_create,
        name="mouvement_create",
    ),
    path(
        "mouvements/<int:pk>/modifier/",
        views_mccr.mouvement_mccr_update,
        name="mouvement_update",
    ),
    path(
        "mouvements/<int:pk>/supprimer/",
        views_mccr.mouvement_mccr_delete,
        name="mouvement_delete",
    ),
]
