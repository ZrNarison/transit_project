from django.urls import path

from . import views


app_name = "rapportsoc"


urlpatterns = [

    # ============================================================
    # RAPPORT DE TRÉSORERIE — AFFICHAGE
    # ============================================================
    path(
        "",
        views.rapport_tresorerie,
        name="rapport_tresorerie"
    ),

    # ============================================================
    # RAPPORT DE TRÉSORERIE — IMPRESSION
    # ============================================================
    path(
        "rapport-tresorerie/impression/",
        views.rapport_tresorerie_print,
        name="rapport_tresorerie_print"
    ),
]