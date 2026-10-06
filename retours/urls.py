from django.urls import path

from . import views

app_name = "retours"

urlpatterns = [

    path(
        "",
        views.retour_list,
        name="retour_list"
    ),

    path(
        "ajouter/",
        views.retour_add,
        name="retour_add"
    ),

    path(
        "<int:id>/",
        views.retour_detail,
        name="retour_detail"
    ),

    path(
        "<int:id>/modifier/",
        views.retour_edit,
        name="retour_edit"
    ),

    path(
        "<int:id>/supprimer/",
        views.retour_delete,
        name="retour_delete"
    ),

]