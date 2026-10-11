from django.urls import path
from . import views


app_name = "recette"

urlpatterns = [
    path("", views.recette_list, name="recette_list"),
    path("add/", views.recette_add, name="recette_add"),
    path("detail/<int:id>/", views.recette_detail, name="recette_detail"),
    path("edit/<int:id>/", views.recette_edit, name="recette_edit"),
    path("delete/<int:id>/", views.recette_delete, name="recette_delete"),

    # ============================================================
    # ENTREPRISE H
    # ============================================================
    path("h/", views.h_recette_list, name="h_recette_list"),
    path("h/add/", views.h_recette_add, name="h_recette_add"),
    path("h/detail/<int:id>/", views.h_recette_detail, name="h_recette_detail"),
    path("h/edit/<int:id>/", views.h_recette_edit, name="h_recette_edit"),
    path("h/delete/<int:id>/", views.h_recette_delete, name="h_recette_delete"),
]