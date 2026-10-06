from django.urls import path
from . import views

app_name = 'transentrant'

urlpatterns = [
    path('', views.t_transentrant_list, name='t_transentrant_liste'),
    path('ajouter/', views.t_transentrant_add, name='t_transentrant_add'),
    path('<int:id>/', views.t_transentrant_detail, name='t_transentrant_detail'),
    path('<int:id>/modifier/', views.t_transentrant_edit, name='t_transentrant_edit'),
    path('<int:id>/supprimer/', views.t_transentrant_delete, name='t_transentrant_delete'),
]