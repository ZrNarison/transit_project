
from django.urls import path

from . import views


app_name = "h_depotSoc"
urlpatterns = [

    # ========================================================
    # LISTE
    # ========================================================

    path(
        "",
        views.h_depot_soc_list,
        name="h_depot_soc_list"
    ),

    # ========================================================
    # AJOUT
    # ========================================================

    path(
        "add/",
        views.h_depot_soc_add,
        name="h_depot_soc_add"
    ),

    # ========================================================
    # DÉTAIL
    # ========================================================

    path(
        "<int:id>/",
        views.h_depot_soc_detail,
        name="h_depot_soc_detail"
    ),

    # ========================================================
    # MODIFICATION
    # ========================================================

    path(
        "<int:id>/edit/",
        views.depot_soc_edit,
        name="depot_soc_edit"
    ),

    # ========================================================
    # SUPPRESSION
    # ========================================================

    path(
        "<int:id>/delete/",
        views.h_depot_soc_delete,
        name="h_depot_soc_delete"
    ),
]
