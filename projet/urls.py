from django.urls import path

from . import views


app_name = "projet"


urlpatterns = [

    # ============================================================
    # PROJETS
    # ============================================================

    path(
        "",
        views.projet_list,
        name="projet_list",
    ),

    path(
        "nouveau/",
        views.projet_create,
        name="projet_create",
    ),

    path(
        "<int:projet_id>/",
        views.projet_detail,
        name="projet_detail",
    ),

    path(
        "<int:projet_id>/modifier/",
        views.projet_update,
        name="projet_update",
    ),

    path(
        "<int:projet_id>/supprimer/",
        views.projet_delete,
        name="projet_delete",
    ),

    # VÉHICULES DU PROJET

    path(
        "<int:projet_id>/vehicules-projet/",
        views.vehicule_projet_list,
        name="vehicule_projet_list",
    ),

    path(
        "<int:projet_id>/vehicules-projet/nouveau/",
        views.vehicule_projet_create,
        name="vehicule_projet_create",
    ),

    path(
        "<int:projet_id>/vehicules-projet/<int:vehicule_projet_id>/modifier/",
        views.vehicule_projet_update,
        name="vehicule_projet_update",
    ),

    path(
        "<int:projet_id>/vehicules-projet/<int:vehicule_projet_id>/supprimer/",
        views.vehicule_projet_delete,
        name="vehicule_projet_delete",
    ),


    
    # ============================================================
    # ACTIVITÉS TRANSPORT PROJET
    # ============================================================

    path(
        "<int:projet_id>/transports/",
        views.activite_transport_projet_list,
        name="activite_transport_projet_list",
    ),

    path(
        "<int:projet_id>/transports/ajouter/",
        views.activite_transport_projet_create,
        name="activite_transport_projet_create",
    ),

    path(
        "<int:projet_id>/transports/<int:activite_id>/modifier/",
        views.activite_transport_projet_update,
        name="activite_transport_projet_update",
    ),

    path(
        "<int:projet_id>/transports/<int:activite_id>/supprimer/",
        views.activite_transport_projet_delete,
        name="activite_transport_projet_delete",
    ),



    # ÉQUIPE D'EXÉCUTION
    

    path(
        "<int:projet_id>/equipe/",
        views.equipe_list,
        name="equipe_list",
    ),

    path(
        "<int:projet_id>/equipe/nouveau/",
        views.equipe_create,
        name="equipe_create",
    ),

    path(
        "<int:projet_id>/equipe/<int:equipe_id>/modifier/",
        views.equipe_update,
        name="equipe_update",
    ),

    path(
        "<int:projet_id>/equipe/<int:equipe_id>/supprimer/",
        views.equipe_delete,
        name="equipe_delete",
    ),

    path(
        "<int:projet_id>/equipe/<int:equipe_id>/utilisateur/nouveau/",
        views.utilisateur_projet_create,
        name="utilisateur_projet_create",
    ),

    path(
        "equipes/nouveau/",
        views.equipe_projet_selection,
        name="equipe_projet_selection",
    ),


    # ============================================================
    # POINTS DE CHANTIER
    # ============================================================

    path(
        "<int:projet_id>/points/",
        views.point_list,
        name="point_list",
    ),

    path(
        "<int:projet_id>/points/nouveau/",
        views.point_create,
        name="point_create",
    ),

    path(
        "<int:projet_id>/points/<int:point_id>/modifier/",
        views.point_update,
        name="point_update",
    ),

    path(
        "<int:projet_id>/points/<int:point_id>/supprimer/",
        views.point_delete,
        name="point_delete",
    ),


    # ============================================================
    # RAPPORT GLOBAL DU PROJET
    # ============================================================

    # Sélection du projet avant d'afficher le rapport global.
    #
    # Navbar :
    # Rapports → Rapport du Projet
    #
    path(
        "rapports/projets/",
        views.rapport_projet_selection,
        name="rapport_projet_selection",
    ),

    # Rapport complet d'un projet.
    #
    # Exemple :
    # /projet/projet/5/rapports/
    #
    path(
        "projet/<int:projet_id>/rapports/",
        views.rapport_projet_global,
        name="rapport_global",
    ),


    # ============================================================
    # RAPPORTS DE L'INGÉNIEUR / RESPONSABLE DU PROJET
    # ============================================================

    # Liste des rapports de l'ingénieur
    path(
        "<int:projet_id>/rapports/",
        views.rapport_projet_list,
        name="rapport_projet_list",
    ),

    # Création d'un rapport de l'ingénieur
    path(
        "<int:projet_id>/rapports/nouveau/",
        views.rapport_projet_create,
        name="rapport_projet_create",
    ),

    # Modification d'un rapport de l'ingénieur
    path(
        "<int:projet_id>/rapports/<int:rapport_id>/modifier/",
        views.rapport_projet_update,
        name="rapport_projet_update",
    ),


    # ============================================================
    # RAPPORTS DES TRAVAUX / CHEF DE CHANTIER
    # ============================================================

    path(
        "<int:projet_id>/travaux/",
        views.rapport_travail_list,
        name="rapport_travail_list",
    ),

    path(
        "<int:projet_id>/travaux/nouveau/",
        views.rapport_travail_create,
        name="rapport_travail_create",
    ),


    # ============================================================
    # RAPPORTS DES MATÉRIAUX / MAGASIN
    # ============================================================

    path(
        "<int:projet_id>/materiaux/",
        views.rapport_materiau_list,
        name="rapport_materiau_list",
    ),

    path(
        "<int:projet_id>/materiaux/nouveau/",
        views.rapport_materiau_create,
        name="rapport_materiau_create",
    ),


    # ============================================================
    # RAPPORTS DES VÉHICULES / CHAUFFEURS
    # ============================================================

    path(
        "<int:projet_id>/vehicules/",
        views.rapport_vehicule_list,
        name="rapport_vehicule_list",
    ),

    path(
        "<int:projet_id>/vehicules/nouveau/",
        views.rapport_vehicule_create,
        name="rapport_vehicule_create",
    ),
]
