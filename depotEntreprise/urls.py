
from django.urls import path

from . import views


app_name = "depotSoc"
urlpatterns = [

    # ========================================================
    # LISTE
    # ========================================================

    path(
        "",
        views.depot_soc_list,
        name="depot_soc_list"
    ),

    # ========================================================
    # AJOUT
    # ========================================================

    path(
        "add/",
        views.depot_soc_add,
        name="depot_soc_add"
    ),

    # ========================================================
    # DÉTAIL
    # ========================================================

    path(
        "<int:id>/",
        views.depot_soc_detail,
        name="depot_soc_detail"
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
        views.depot_soc_delete,
        name="depot_soc_delete"
    ),

    # ============================================================
    # ENTREPRISE H
    # ============================================================
    path(
        "h/",
        views.h_depot_soc_list,
        name="h_depot_soc_list"
    ),
    path(
        "h/add/",
        views.h_depot_soc_add,
        name="h_depot_soc_add"
    ),
    path(
        "h/<int:id>/",
        views.h_depot_soc_detail,
        name="h_depot_soc_detail"
    ),
    path(
        "h/<int:id>/edit/",
        views.h_depot_soc_edit,
        name="h_depot_soc_edit"
    ),
    path(
        "h/<int:id>/delete/",
        views.h_depot_soc_delete,
        name="h_depot_soc_delete"
    ),
    
]
