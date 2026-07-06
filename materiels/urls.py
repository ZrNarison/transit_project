from django.urls import path
from . import views

app_name = "materiels"

urlpatterns = [
    path("", views.materiels_list, name="materiels_list"),
    path("ajouter/", views.materiels_add, name="materiels_add"),

    path(
        "detail/<str:nom>/<str:typeMat>/<str:catMat>/",
        views.materiels_detail,
        name="materiels_detail"
    ),

    path("<int:id>/modifier/", views.materiels_edit, name="materiels_edit"),
    path("<int:id>/supprimer/", views.materiels_delete, name="materiels_delete"),
]