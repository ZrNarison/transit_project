from django.urls import path
from . import views


app_name = "categorie"


urlpatterns = [

    path(
        "",
        views.categorie_liste,
        name="categorie_liste"
    ),

    path(
        "ajouter/",
        views.categorie_add,
        name="categorie_add"
    ),

    path(
        "<int:id>/modifier/",
        views.categorie_edit,
        name="categorie_edit"
    ),

    path(
        "<int:id>/supprimer/",
        views.categorie_delete,
        name="categorie_delete"
    ),

]