from django.urls import path

from . import views

app_name = "materiaux"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("dashboard/", views.dashboard_alt, name="dashboard_alt"),
    path("materiaux/", views.materiaux_list, name="materiaux_list"),
    path("materiaux/add/", views.materiau_add, name="materiaux_add"),
    path("materiaux/<int:pk>/edit/", views.materiau_edit, name="materiaux_edit"),
    path("materiaux/<int:pk>/delete/", views.materiau_delete, name="materiaux_delete"),
    path("entrees/", views.entrees_list, name="entrees_list"),
    path("entrees/add/", views.entree_add, name="entree_add"),
    path("entrees/<int:pk>/edit/", views.entree_edit, name="entree_edit"),
    path("entrees/<int:pk>/delete/", views.entree_delete, name="entree_delete"),
    path("divisions/", views.divisions_list, name="divisions_list"),
    path("divisions/add/", views.division_add, name="division_add"),
    path("divisions/<int:pk>/edit/", views.division_edit, name="division_edit"),
    path("divisions/<int:pk>/delete/", views.division_delete, name="division_delete"),
    path("sorties/", views.sorties_list, name="sorties_list"),
    path("sorties/add/", views.sortie_add, name="sortie_add"),
    path("sorties/<int:pk>/modifier/", views.sortie_edit, name="sortie_edit"),
    path("sorties/<int:pk>/supprimer/", views.sortie_delete, name="sortie_delete"),
    path("vehicules/", views.vehicules_list, name="vehicules_list"),
    path("vehicules/add/", views.vehicule_add, name="vehicule_add"),
    path("vehicules/<int:pk>/edit/", views.vehicule_edit, name="vehicule_edit"),
    path("vehicules/<int:pk>/delete/", views.vehicule_delete, name="vehicule_delete"),
    path(
        "categories-depenses/",
        views.categories_depenses_list,
        name="categories_depenses_list",
    ),
    path(
        "categories-depenses/add/",
        views.categorie_depense_add,
        name="categorie_depense_add",
    ),
    path(
        "categories-depenses/<int:pk>/modifier/",
        views.categorie_depense_edit,
        name="categorie_depense_edit",
    ),
    path(
        "categories-depenses/<int:pk>/supprimer/",
        views.categorie_depense_delete,
        name="categorie_depense_delete",
    ),
    path(
        "activites-transport/",
        views.activites_transport_list,
        name="activites_transport_list",
    ),
    path(
        "activites-transport/ajouter/",
        views.activite_transport_add,
        name="activite_transport_add",
    ),
    path(
        "activites-transport/<int:pk>/modifier/",
        views.activite_transport_edit,
        name="activite_transport_edit",
    ),
    path(
        "activites-transport/<int:pk>/supprimer/",
        views.activite_transport_delete,
        name="activite_transport_delete",
    ),
    path(
        "paiements-dockers/",
        views.paiements_dockers_list,
        name="paiements_dockers_list",
    ),
    path(
        "paiements-dockers/add/", views.paiement_docker_add, name="paiement_docker_add"
    ),
    path(
        "paiements-dockers/<int:pk>/edit/",
        views.paiement_docker_edit,
        name="paiement_docker_edit",
    ),
    path(
        "paiements-dockers/<int:pk>/delete/",
        views.paiement_docker_delete,
        name="paiement_docker_delete",
    ),
    path("depenses/", views.depenses_list, name="depenses_list"),
    path("depenses/add/", views.depense_add, name="depense_add"),
    path("depenses/<int:pk>/edit/", views.depense_edit, name="depense_edit"),
    path("depenses/<int:pk>/delete/", views.depense_delete, name="depense_delete"),
    path("gasoil/", views.depenses_gasoil_list, name="depenses_gasoil_list"),
    path("gasoil/add/", views.depense_gasoil_add, name="depense_gasoil_add"),
    path(
        "gasoil/<int:pk>/edit/", views.depense_gasoil_edit, name="depense_gasoil_edit"
    ),
    path(
        "gasoil/<int:pk>/delete/",
        views.depense_gasoil_delete,
        name="depense_gasoil_delete",
    ),
    path("reparations/", views.reparations_list, name="reparations_list"),
    path("reparations/add/", views.reparation_add, name="reparation_add"),
    path("reparations/<int:pk>/edit/", views.reparation_edit, name="reparation_edit"),
    path(
        "reparations/<int:pk>/delete/",
        views.reparation_delete,
        name="reparation_delete",
    ),
    path("stock-entrepot/", views.stock_entrepot, name="stock_entrepot"),
    path("stock-magasin/", views.stock_magasin, name="stock_magasin"),
    path(
        "receptions-materiaux/",
        views.receptions_materiaux_list,
        name="receptions_materiaux_list",
    ),
    path(
        "receptions-materiaux/add/",
        views.reception_materiau_add,
        name="reception_materiau_add",
    ),
    path(
        "receptions-materiaux/<int:pk>/edit/",
        views.reception_materiau_edit,
        name="reception_materiau_edit",
    ),
    path(
        "utilisations-materiaux/",
        views.utilisations_materiaux_list,
        name="utilisations_materiaux_list",
    ),
    path(
        "utilisations-materiaux/add/",
        views.utilisation_materiau_add,
        name="utilisation_materiau_add",
    ),
    path(
        "utilisations-materiaux/<int:pk>/edit/",
        views.utilisation_materiau_edit,
        name="utilisation_materiau_edit",
    ),
    path(
        "utilisations-materiaux/<int:pk>/delete/",
        views.utilisation_materiau_delete,
        name="utilisation_materiau_delete",
    ),
    path(
        "retours-materiaux/",
        views.retours_materiaux_list,
        name="retours_materiaux_list",
    ),
    path(
        "retours-materiaux/add/", views.retour_materiau_add, name="retour_materiau_add"
    ),
    path(
        "retours-materiaux/<int:pk>/edit/",
        views.retour_materiau_edit,
        name="retour_materiau_edit",
    ),
    path(
        "retours-materiaux/<int:pk>/delete/",
        views.retour_materiau_delete,
        name="retour_materiau_delete",
    ),
]
