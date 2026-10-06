from django.urls import path
from . import views


app_name = "h_entretien"


urlpatterns = [

    path(
        "",
        views.h_entretien_list,
        name="h_list"
    ),

    path(
        "ajouter/",
        views.h_entretien_create,
        name="h_create"
    ),

    path(
        "modifier/<int:id>/",
        views.h_entretien_update,
        name="h_update"
    ),

    path(
        "supprimer/<int:id>/",
        views.h_entretien_delete,
        name="h_delete"
    ),

]