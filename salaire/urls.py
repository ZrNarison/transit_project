from django.urls import path
from . import views

app_name = 'salaire'

urlpatterns = [
    path('', views.salaire_list, name='salaire_list'),
    path('ajouter/', views.salaire_add, name='salaire_add'),
    path('<int:id>/modifier/', views.salaire_edit, name='salaire_edit'),
    path('<int:id>/supprimer/', views.salaire_delete, name='salaire_delete'),
]
