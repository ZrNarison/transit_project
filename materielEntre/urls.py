from django.urls import path
from . import views

app_name = "materielEntre"

urlpatterns = [
    path("", views.materielEntre_list, name="materielEntre_list"),
    path("ajouter/", views.materielEntre_add, name="materielsort_add"),
    path("<int:id>/", views.materielEntre_detail, name="materielEntre_detail"),
    path("<int:id>/modifier/", views.materielEntre_edit, name="materielEntre_edit"),
    path("<int:id>/supprimer/", views.materielEntre_delete, name="materielEntre_delete"),
]