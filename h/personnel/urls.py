from django.urls import path
from . import views


app_name = "h_personnel"


urlpatterns = [

    path(
        "",
        views.h_personnel_list,
        name="h_personnel_list"
    ),

    path(
        "ajouter/",
        views.h_personnel_add,
        name="h_personnel_add"
    ),

    path(
        "<int:id>/",
        views.h_personnel_detail,
        name="h_personnel_detail"
    ),

    path(
        "<int:id>/modifier/",
        views.h_personnel_edit,
        name="h_personnel_edit"
    ),

    path(
        "<int:id>/supprimer/",
        views.h_personnel_delete,
        name="h_personnel_delete"
    ),

]