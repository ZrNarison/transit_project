from django.urls import path
from . import views

app_name = "users"

urlpatterns = [
    path('', views.users_liste, name='users_liste'),
    path('ajouter/', views.users_add, name='users_add'),
    path('<int:id>/', views.users_detail, name='users_detail'),
    path('<int:id>/modifier/', views.users_edit, name='users_edit'),
    path('<int:id>/supprimer/', views.users_delete, name='users_delete'),
]