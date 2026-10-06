from django.urls import path

from . import views


app_name = "materiaux"


urlpatterns = [

    # ======================================================
    # TABLEAU DE BORD
    # ======================================================

    path("",views.dashboard,name="dashboard",),

    path(
        "dashboard/",
        views.dashboard,
        name="dashboard_alt",
    ),

    # ======================================================
    # MATÉRIAUX
    # ======================================================

    path(
        "materiaux/",
        views.materiaux_list,
        name="materiaux_list",
    ),

    path(
        "materiaux/add/",
        views.materiaux_add,
        name="materiaux_add",
    ),

    path(
        "materiaux/<int:pk>/edit/",
        views.materiaux_edit,
        name="materiaux_edit",
    ),

    path(
        "materiaux/<int:pk>/delete/",
        views.materiaux_delete,
        name="materiaux_delete",
    ),

    # ======================================================
    # ENTRÉES ENTREPÔT
    # ======================================================

    path(
        "entrees/",
        views.entrees_list,
        name="entrees_list",
    ),

    path(
        "entrees/add/",
        views.entree_add,
        name="entree_add",
    ),

    path(
        "entrees/<int:pk>/edit/",
        views.entree_edit,
        name="entree_edit",
    ),

    path(
        "entrees/<int:pk>/delete/",
        views.entree_delete,
        name="entree_delete",
    ),

    # ======================================================
    # DIVISIONS ENTREPÔT → MAGASIN
    # ======================================================

    path(
        "divisions/",
        views.divisions_list,
        name="divisions_list",
    ),

    path(
        "divisions/add/",
        views.division_add,
        name="division_add",
    ),

    path(
        "divisions/<int:pk>/delete/",
        views.division_delete,
        name="division_delete",
    ),

    # ======================================================
    # SORTIES MAGASIN
    # ======================================================

    path(
        "sorties/",
        views.sorties_list,
        name="sorties_list",
    ),

    path(
        "sorties/add/",
        views.sortie_add,
        name="sortie_add",
    ),

    path(
    "sorties/<int:pk>/modifier/",
    views.sortie_edit,
    name="sortie_edit",
    ),

    path(
        "sorties/<int:pk>/supprimer/",
        views.sortie_delete,
        name="sortie_delete",
    ),

    # ======================================================
    # DOCKERS
    # ======================================================
    path( "paiements-dockers/", views.paiements_dockers_list, name="paiements_dockers_list", ), 
    path( "paiements-dockers/add/", views.paiement_docker_add, name="paiement_docker_add", ), 
    path( "paiements-dockers/<int:pk>/edit/", views.paiement_docker_edit, name="paiement_docker_edit", ), 
    path( "paiements-dockers/<int:pk>/delete/", views.paiement_docker_delete, name="paiement_docker_delete", ),
    # ======================================================
    # VÉHICULES
    # ======================================================

    path(
        "vehicules/",
        views.vehicules_list,
        name="vehicules_list",
    ),

    path(
        "vehicules/add/",
        views.vehicule_add,
        name="vehicule_add",
    ),

    path(
        "vehicules/<int:pk>/edit/",
        views.vehicule_edit,
        name="vehicule_edit",
    ),

    path(
        "vehicules/<int:pk>/delete/",
        views.vehicule_delete,
        name="vehicule_delete",
    ),
    # ======================================================
    # CATÉGORIES DE DÉPENSES
    # ======================================================

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
            "categories-depenses/modifier/",
            views.categorie_depense_edit,
            name="categorie_depense_edit",
        ),
    path(
            "categories-depenses/supprimer/",
            views.categorie_depense_delete,
            name="categorie_depense_delete",
        ),

    # =========================
    # ACTIVITÉS DE TRANSPORT
    # =========================

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

    # ======================================================
    # DÉPENSES GÉNÉRALES
    # ======================================================

    path(
        "depenses/",
        views.depenses_list,
        name="depenses_list",
    ),

    path(
        "depenses/add/",
        views.depense_add,
        name="depense_add",
    ),

    path(
        "depenses/<int:pk>/edit/",
        views.depense_edit,
        name="depense_edit",
    ),

    path(
        "depenses/<int:pk>/delete/",
        views.depense_delete,
        name="depense_delete",
    ),

    # ======================================================
    # GASOIL
    # ======================================================

    path(
        "gasoil/",
        views.depenses_gasoil_list,
        name="depenses_gasoil_list",
    ),

    path(
        "gasoil/add/",
        views.depense_gasoil_add,
        name="depense_gasoil_add",
    ),

    path(
        "gasoil/<int:pk>/edit/",
        views.depense_gasoil_edit,
        name="depense_gasoil_edit",
    ),

    path(
        "gasoil/<int:pk>/delete/",
        views.depense_gasoil_delete,
        name="depense_gasoil_delete",
    ),

    # ======================================================
    # RÉPARATIONS / ENTRETIEN
    # ======================================================

    path(
        "reparations/",
        views.reparations_list,
        name="reparations_list",
    ),

    path(
        "reparations/add/",
        views.reparation_add,
        name="reparation_add",
    ),

    path(
        "reparations/<int:pk>/edit/",
        views.reparation_edit,
        name="reparation_edit",
    ),

    path(
        "reparations/<int:pk>/delete/",
        views.reparation_delete,
        name="reparation_delete",
    ),

    # ======================================================
    # STOCK ENTREPÔT
    # ======================================================

    path(
        "stock-entrepot/",
        views.stock_entrepot,
        name="stock_entrepot",
    ),

    # ======================================================
    # STOCK MAGASIN
    # ======================================================

    path(
        "stock-magasin/",
        views.stock_magasin,
        name="stock_magasin",
    ),
]