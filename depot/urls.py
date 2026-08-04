from django.urls import path

from . import views


app_name = "depot"


urlpatterns = [

    path(
        "",
        views.depot_list,
        name="depot_list"
    ),


    path(
        "ajouter/",
        views.depot_add,
        name="depot_add"
    ),


    path(
        "modifier/<int:id>/",
        views.depot_edit,
        name="depot_edit"
    ),


    path(
        "supprimer/<int:id>/",
        views.depot_delete,
        name="depot_delete"
    ),


    path(
        "print/",
        views.depot_print,
        name="depot_print"
    ),

]