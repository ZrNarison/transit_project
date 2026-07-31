from django.urls import path
from . import views

app_name = 'clients'

urlpatterns = [
    path('', views.client_list, name='client_list'),
    path('ajouter/', views.client_add, name='client_add'),
    path('<int:id>/', views.client_detail, name='client_detail'),
    path('<int:id>/modifier/', views.client_edit, name='client_edit'),
    path('<int:id>/supprimer/', views.client_delete, name='client_delete'),
]