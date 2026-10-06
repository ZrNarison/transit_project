from django.urls import path
from . import views


app_name = "recette"

urlpatterns = [
    path("", views.recette_list, name="recette_list"),
    path("add/", views.recette_add, name="recette_add"),
    path("detail/<int:id>/", views.recette_detail, name="recette_detail"),
    path("edit/<int:id>/", views.recette_edit, name="recette_edit"),
    path("delete/<int:id>/", views.recette_delete, name="recette_delete"),
]