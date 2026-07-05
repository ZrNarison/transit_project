from django.urls import path
from . import views

app_name = 'produit'

urlpatterns = [
    path('', views.p_produit_list, name='p_produit_liste'),
    path('ajouter/', views.p_produit_add, name='p_produit_add'),
    path('<int:id>/modifier/', views.p_produit_edit, name='p_produit_edit'),
    path('<int:id>/supprimer/', views.p_produit_delete, name='p_produit_delete'),
    path(
    'valider-paiement/',
    views.valider_paiement,
    name='valider_paiement'
),
]