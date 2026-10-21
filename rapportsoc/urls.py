from django.urls import path

from . import views

app_name = "rapportsoc"

urlpatterns = [
    # ==========================================
    # GALAXY
    # ==========================================
    path(
        "",
        views.rapport_tresorerie,
        name="rapport_tresorerie",
    ),
    path(
        "rapport-tresorerie/impression/",
        views.rapport_tresorerie_print,
        name="rapport_tresorerie_print",
    ),
    # ==========================================
    # MCCR / ENTREPRISE H
    # ==========================================
    path(
        "mccr/",
        views.h_rapport_tresorerie,
        name="h_rapport_tresorerie",
    ),
    path(
        "mccr/rapport-tresorerie/impression/",
        views.h_rapport_tresorerie_print,
        name="h_rapport_tresorerie_print",
    ),
]
