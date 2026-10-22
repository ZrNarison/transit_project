from django.urls import path

from . import views

app_name = "depensesoc"


urlpatterns = [
    path("", views.soc_depense_list, name="soc_depense_list"),
    path("ajouter/", views.soc_depense_add, name="soc_depense_add"),
    path("<int:id>/modifier/", views.soc_depense_edit, name="soc_depense_edit"),
    path("<int:id>/supprimer/", views.soc_depense_delete, name="soc_depense_delete"),

    #==================================================
    # ENTREPRISE H
    #==================================================
    path("mccr/", views.h_soc_depense_list, name="h_soc_depense_list"),
    path("mccr/ajouter/", views.h_soc_depense_add, name="h_soc_depense_add"),
    path("mccr/<int:id>/modifier/", views.h_soc_depense_edit, name="h_soc_depense_edit"),
    path("mccr/<int:id>/supprimer/", views.h_soc_depense_delete, name="h_soc_depense_delete"),
]
