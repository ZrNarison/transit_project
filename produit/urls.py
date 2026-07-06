from django.urls import path
from . import views

app_name = "produit"

urlpatterns = [
    path('', views.produit_list, name='p_produit_liste'),

    path('ajouter/', views.produit_add, name='p_produit_add'),

    path('edit/<int:pk>/', views.produit_edit, name='p_produit_edit'),

    path('delete/<int:pk>/', views.produit_delete, name='p_produit_delete'),
    path('valider-paiement/', views.valider_paiement, name='valider_paiement'),
]