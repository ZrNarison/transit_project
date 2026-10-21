from django.urls import path

from . import views

app_name = "sauvegarde"

urlpatterns = [
    # GALAXY : routes existantes
    path("", views.index, name="index"),
    path("exporter/", views.exporter, name="exporter"),
    path("valider-import/", views.valider_import, name="valider_import"),
    path("importer/", views.importer, name="importer"),

    # MCCR : routes séparées
    path("mccr/", views.index, name="h_index"),
    path("mccr/exporter/", views.exporter, name="h_exporter"),
    path("mccr/valider-import/", views.valider_import, name="h_valider_import"),
    path("mccr/importer/", views.importer, name="h_importer"),
]
