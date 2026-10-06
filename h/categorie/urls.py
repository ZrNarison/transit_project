from django.urls import path
from . import views


app_name = "h_categorie"


urlpatterns = [

    path(
        "",
        views.h_categorie_liste,
        name="h_categorie_liste"
    ),

    path(
        "ajouter/",
        views.h_categorie_add,
        name="h_categorie_add"
    ),

    path(
        "<int:id>/modifier/",
        views.h_categorie_edit,
        name="h_categorie_edit"
    ),

    path(
        "<int:id>/supprimer/",
        views.h_categorie_delete,
        name="h_categorie_delete"
    ),

]