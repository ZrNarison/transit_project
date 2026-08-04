from django.urls import path
from . import views


app_name = "salaire"


urlpatterns = [

    # Liste des salaires
    path(
        "",
        views.salaire_list,
        name="salaire_list"
    ),


    # Ajouter
    path(
        "ajouter/",
        views.salaire_add,
        name="salaire_add"
    ),


    # Modifier
    path(
        "<int:id>/modifier/",
        views.salaire_edit,
        name="salaire_edit"
    ),


    # Supprimer
    path(
        "<int:id>/supprimer/",
        views.salaire_delete,
        name="salaire_delete"
    ),

]