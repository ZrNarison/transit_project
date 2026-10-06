from django.urls import path
from . import views

app_name = 'depense'

urlpatterns = [
    path('', views.depense_list, name='depense_list'),
    path('ajouter/', views.depense_add, name='depense_add'),
    path('<int:id>/modifier/', views.depense_edit, name='depense_edit'),
    path('<int:id>/supprimer/', views.depense_delete, name='depense_delete'),
]
