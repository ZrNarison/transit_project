from django.urls import path
from . import views

app_name = 'h_avances'

urlpatterns = [
    path('', views.h_avance_list, name='h_avance_list'),
    path('ajouter/', views.h_avance_add, name='h_avance_add'),
    path('<int:id>/', views.h_avance_detail, name='h_avance_detail'),
    path('<int:id>/modifier/', views.h_avance_edit, name='h_avance_edit'),  # ✔ CORRIGÉ
    path('<int:id>/supprimer/', views.h_avance_delete, name='h_avance_delete'),
]