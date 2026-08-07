from django.urls import path
from . import views


app_name = "entretien"


urlpatterns = [

    path(
        "",
        views.entretien_list,
        name="list"
    ),

    path(
        "ajouter/",
        views.entretien_create,
        name="create"
    ),

    path(
        "modifier/<int:id>/",
        views.entretien_update,
        name="update"
    ),

    path(
        "supprimer/<int:id>/",
        views.entretien_delete,
        name="delete"
    ),

]