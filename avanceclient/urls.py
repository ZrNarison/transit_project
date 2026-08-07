from django.urls import path

from . import views


app_name = "avanceclient"


urlpatterns = [

    # Liste
    path(
        "",
        views.avanceclient_list,
        name="list"
    ),


    # Ajout
    path(
        "ajouter/",
        views.avanceclient_add,
        name="add"
    ),


    # Détail
    path(
        "detail/<int:id>/",
        views.avanceclient_detail,
        name="detail"
    ),


    # Modification
    path(
        "modifier/<int:id>/",
        views.avanceclient_edit,
        name="edit"
    ),


    # Suppression
    path(
        "supprimer/<int:id>/",
        views.avanceclient_delete,
        name="delete"
    ),

]