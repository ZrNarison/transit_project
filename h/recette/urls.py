from django.urls import path
from . import views


app_name = "recette"

urlpatterns = [
    path("", views.h_recette_list, name="h_recette_list"),
    path("add/", views.h_recette_add, name="h_recette_add"),
    path("detail/<int:id>/", views.h_recette_detail, name="h_recette_detail"),
    path("edit/<int:id>/", views.h_recette_edit, name="h_recette_edit"),
    path("delete/<int:id>/", views.h_recette_delete, name="h_recette_delete"),
]