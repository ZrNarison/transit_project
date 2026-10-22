from django.urls import path

from . import views

app_name = "avances"

urlpatterns = [
    # =========================
    # GALAXY — conserver les routes existantes
    # =========================
    path("", views.avance_list, name="avance_list"),
    path("ajouter/", views.avance_add, name="avance_add"),
    path("<int:id>/", views.avance_detail, name="avance_detail"),
    path("<int:id>/modifier/", views.avance_edit, name="avance_edit"),
    path("<int:id>/supprimer/", views.avance_delete, name="avance_delete"),

    # =========================
    # MCCR / ENTREPRISE H
    # =========================
    path("h/", views.h_avance_list, name="h_avance_list"),
    path("h/ajouter/", views.h_avance_add, name="h_avance_add"),
    path("h/<int:id>/modifier/", views.h_avance_edit, name="h_avance_edit"),
    path("h/<int:id>/supprimer/", views.h_avance_delete, name="h_avance_delete"),
]