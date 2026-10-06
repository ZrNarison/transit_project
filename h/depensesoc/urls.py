from django.urls import path

from . import views


app_name = "depensesoc"


urlpatterns = [

    path(
        "",
        views.h_soc_depense_list,
        name="h_soc_depense_list"
    ),

    path(
        "ajouter/",
        views.h_soc_depense_add,
        name="h_soc_depense_add"
    ),

    path(
        "<int:id>/modifier/",
        views.h_soc_depense_edit,
        name="h_soc_depense_edit"
    ),

    path(
        "<int:id>/supprimer/",
        views.h_soc_depense_delete,
        name="h_soc_depense_delete"
    ),

]
