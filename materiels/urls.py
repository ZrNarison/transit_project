from django.urls import path
from . import views

app_name = "materiels"

urlpatterns = [

    # Liste
    path(
        "",
        views.materiels_list,
        name="materiels_list"
    ),

    # =========================================================
    # DETAIL D'UN GROUPE
    # Nom + Type + Catégorie
    # =========================================================

    path(
        "mdetail/<str:nom>/<str:typeMat>/<str:catMat>/",
        views.materiels_mdetail,
        name="materiels_mdetail"
    ),

    # =========================================================
    # DETAIL CLASSIQUE
    # =========================================================

    path(
        "detail/<str:nom>/<str:typeMat>/<str:catMat>/",
        views.materiels_detail,
        name="materiels_detail"
    ),

    # Ajouter
    path(
        "add/",
        views.materiels_add,
        name="materiels_add"
    ),

    # Modifier un enregistrement
    path(
        "edit/<int:id>/",
        views.materiels_edit,
        name="materiels_edit"
    ),

    # Supprimer un enregistrement
    path(
        "delete/<int:id>/",
        views.materiels_delete,
        name="materiels_delete"
    ),

    # Supprimer le stock initial du groupe
    path(
        "supprimer-stock-initial/<str:nom>/<str:typeMat>/<str:catMat>/",
        views.supprimer_stock_initial,
        name="supprimer_stock_initial"
    ),
]
