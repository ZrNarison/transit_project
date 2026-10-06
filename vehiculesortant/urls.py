from django.urls import path
from . import views

app_name = 'vehiculesortant'

urlpatterns = [
    path('', views.vehicule_sortant_list, name='vehicule_sortant_list'),
    path('ajouter/', views.vehicule_sortant_add, name='vehicule_sortant_add'),
    path('<int:id>/', views.vehicule_sortant_detail, name='vehicule_sortant_detail'),
    path('<int:id>/modifier/', views.vehicule_sortant_edit, name='vehicule_sortant_edit'),
    path('<int:id>/supprimer/', views.vehicule_sortant_delete, name='vehicule_sortant_delete'),
]
