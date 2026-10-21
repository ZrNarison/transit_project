from django.urls import path

from . import views

app_name = "sauvegarde"

urlpatterns = [
    path("", views.index, name="index"),
    path("exporter/", views.exporter, name="exporter"),
    path("valider-import/", views.valider_import, name="valider_import"),
    path("importer/", views.importer, name="importer"),
]
