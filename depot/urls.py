from django.urls import path
from . import views

app_name = 'depot'

urlpatterns = [
    path('', views.depot_list, name='depot_list'),
    path('ajouter/', views.depot_add, name='depot_add'),
    path('<int:id>/modifier/', views.depot_edit, name='depot_edit'),
    path('<int:id>/supprimer/', views.depot_delete, name='depot_delete'),
]
