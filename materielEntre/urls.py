from django.urls import path
from . import views

app_name = "materielEntre"

urlpatterns = [
    path("", views.materielEntre_list, name="materielEntre_list"),
    
    path("ajouter/", views.materielEntre_add, name="materielEntre_add"),
    
    path("detail/<int:id>/", views.materielEntre_detail, name="materielEntre_detail"),
    
    path("modifier/<int:id>/", views.materielEntre_edit, name="materielEntre_edit"),
    
    path("supprimer/<int:id>/", views.materielEntre_delete, name="materielEntre_delete"),
]