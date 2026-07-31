from django.urls import path
from . import views

app_name = 'personnel'

urlpatterns = [
    path('', views.personnel_list, name='personnel_list'),
    path('ajouter/', views.personnel_add, name='personnel_add'),
    path('<int:id>/', views.personnel_detail, name='personnel_detail'),
    path('<int:id>/modifier/', views.personnel_edit, name='personnel_edit'),
    path('<int:id>/supprimer/', views.personnel_delete, name='personnel_delete'),
]