from django.urls import path
from . import views

app_name = 'avances'

urlpatterns = [
    path('', views.avance_list, name='avance_list'),
    path('ajouter/', views.avance_add, name='avance_add'),
    path('<int:id>/', views.avance_detail, name='avance_detail'),
    path('<int:id>/modifier/', views.avance_edit, name='avance_edit'),  # ✔ CORRIGÉ
    path('<int:id>/supprimer/', views.avance_delete, name='avance_delete'),
]