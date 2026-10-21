from django.urls import path

from . import views

app_name = "materiels"

urlpatterns = [
    # =========================================================
    # GALAXY — LISTE
    # =========================================================
    path(
        "",
        views.materiels_list,
        name="materiels_list",
    ),
    # =========================================================
    # GALAXY — DÉTAIL D'UN GROUPE
    # =========================================================
    path(
        "mdetail/<str:nom>/<str:typeMat>/<str:catMat>/",
        views.materiels_mdetail,
        name="materiels_mdetail",
    ),
    # =========================================================
    # GALAXY — DÉTAIL CLASSIQUE
    # =========================================================
    path(
        "detail/<str:nom>/<str:typeMat>/<str:catMat>/",
        views.materiels_detail,
        name="materiels_detail",
    ),
    # =========================================================
    # GALAXY — AJOUTER
    # =========================================================
    path(
        "add/",
        views.materiels_add,
        name="materiels_add",
    ),
    # =========================================================
    # GALAXY — MODIFIER
    # =========================================================
    path(
        "edit/<int:id>/",
        views.materiels_edit,
        name="materiels_edit",
    ),
    # =========================================================
    # GALAXY — SUPPRIMER
    # =========================================================
    path(
        "delete/<int:id>/",
        views.materiels_delete,
        name="materiels_delete",
    ),
    # =========================================================
    # GALAXY — SUPPRIMER LE STOCK INITIAL
    # =========================================================
    path(
        "supprimer-stock-initial/<str:nom>/<str:typeMat>/<str:catMat>/",
        views.supprimer_stock_initial,
        name="supprimer_stock_initial",
    ),
    # =========================================================
    # ENTREPRISE H — LISTE
    # =========================================================
    path(
        "entreprise-h/",
        views.h_materiels_list,
        name="h_materiels_list",
    ),
    # =========================================================
    # ENTREPRISE H — DÉTAIL D'UN GROUPE
    # =========================================================
    path(
        "entreprise-h/mdetail/<str:nom>/<str:typeMat>/<str:catMat>/",
        views.h_materiels_mdetail,
        name="h_materiels_mdetail",
    ),
    # =========================================================
    # ENTREPRISE H — DÉTAIL CLASSIQUE
    # =========================================================
    path(
        "entreprise-h/detail/<str:nom>/<str:typeMat>/<str:catMat>/",
        views.h_materiels_detail,
        name="h_materiels_detail",
    ),
    # =========================================================
    # ENTREPRISE H — AJOUTER
    # =========================================================
    path(
        "entreprise-h/add/",
        views.h_materiels_add,
        name="h_materiels_add",
    ),
    # =========================================================
    # ENTREPRISE H — MODIFIER
    # =========================================================
    path(
        "entreprise-h/edit/<int:id>/",
        views.h_materiels_edit,
        name="h_materiels_edit",
    ),
    # =========================================================
    # ENTREPRISE H — SUPPRIMER
    # =========================================================
    path(
        "entreprise-h/delete/<int:id>/",
        views.h_materiels_delete,
        name="h_materiels_delete",
    ),
    # =========================================================
    # ENTREPRISE H — SUPPRIMER LE STOCK INITIAL
    # =========================================================
    path(
        "entreprise-h/supprimer-stock-initial/<str:nom>/<str:typeMat>/<str:catMat>/",
        views.h_supprimer_stock_initial,
        name="h_supprimer_stock_initial",
    ),
]
