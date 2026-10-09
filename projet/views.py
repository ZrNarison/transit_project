from functools import wraps
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.utils import timezone
# from django.db.models import  Sum, F, ExpressionWrapper, DecimalField
from django.db.models import ( Q,DecimalField, ExpressionWrapper, F, Sum,)
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import ProtectedError
from django.shortcuts import get_object_or_404, redirect, render

from users.models import AppUser
from personnel.models import Personnel
from materiaux.models import Materiaux, Vehicule

from .forms import (ProjetForm,EquipeProjetForm,ChefEquipeProjetForm,MinierProjetForm,MateriauProjetForm,PointProjetForm,RapportProjetForm,
    RapportTravailForm,RapportMateriauForm,VehiculeProjetForm,EnginProjetForm,
    RapportVehiculeForm,ActiviteTransportProjetForm,MouvementVehiculeProjetForm)

from .models import (
    Projet,MateriauProjet,EquipeProjet,PointProjet,RapportProjet,RapportTravail,    RapportMateriau,
    VehiculeProjet,EnginProjet,
    MouvementVehiculeProjet,
    RapportVehicule,
    ActiviteTransportProjet,
    PersonnelExecutionProjet,
    MouvementPersonnelProjet,
    EquipageProjet,
    AvanceEquipeProjet,
    EquipeMateriauProjet,
    VehiculeLourdsProjet,
)
from users.decorators import (
    get_current_user,
    project_access_required,
    user_can_manage_projects,user_has_project_access,
    get_current_personnel,
    login_required_projet,
    project_manager_required,    
)

# ============================================================
# CONSTANTES
# ============================================================

PERSONNEL_PROJET_FONCTIONS = [
    ("INGENIEUR", "Ingénieur Responsable du Chantier"),
    ("CHEF_CHANTIER", "Chef de Chantier"),
    ("CHEF_MAGASIN", "Chef Magasinier"),
    ("MAGASINIER", "Magasinier"),
    ("CHAUFFEUR", "Chauffeur"),
    ("OUVRIER", "Ouvrier"),
    ("AUTRE", "Autre"),
]


# ============================================================
# CRUD CHEF D'ÉQUIPE
# ============================================================
@login_required_projet
def chef_equipe_list(
    request,
    projet_id,
):
    """
    Liste des chefs d'équipe enregistrés pour le projet.

    Fonctionnalités :
        - Vérification de l'accès au projet
        - Filtre par nom
        - Filtre par date de début
        - Filtre par date de fin
        - Calcul du nombre de chefs
        - Calcul du total des rémunérations
        - Modification/suppression uniquement par
          l'utilisateur qui a enregistré le chef
    """

    current_user = request.current_user

    # ============================================================
    # PROJET
    # ============================================================

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    # ============================================================
    # VÉRIFICATION ACCÈS PROJET
    # ============================================================

    if not user_has_project_access(
        current_user,
        projet,
    ):
        messages.error(
            request,
            "Votre accès à ce projet n'est pas actif.",
        )

        return redirect(
            "projet:projet_list"
        )

    # ============================================================
    # DROIT DE GESTION
    # ============================================================

    peut_gerer = user_can_manage_projects(
        current_user
    )

    # ============================================================
    # PERSONNEL CONNECTÉ
    # ============================================================

    personnel_connecte = getattr(
        current_user,
        "personnel",
        None,
    )

    # ============================================================
    # FILTRES
    # ============================================================

    nom = request.GET.get(
        "nom",
        "",
    ).strip()

    date_debut = request.GET.get(
        "date_debut",
        "",
    ).strip()

    date_fin = request.GET.get(
        "date_fin",
        "",
    ).strip()

    # ============================================================
    # REQUÊTE DE BASE
    # ============================================================

    chefs_queryset = (
        PersonnelExecutionProjet.objects
        .filter(
            projet=projet,
            type_class="CHEF_EQUIPE",
        )
        .select_related(
            "projet",
            "enregistre_par",
            "point_projet",
        )
    )

    # ============================================================
    # FILTRE NOM
    # ============================================================

    if nom:
        chefs_queryset = chefs_queryset.filter(
            nom__icontains=nom
        )

    # ============================================================
    # FILTRE DATE DE DÉBUT
    # ============================================================

    if date_debut:
        chefs_queryset = chefs_queryset.filter(
            date_debut__gte=date_debut
        )

    # ============================================================
    # FILTRE DATE DE FIN
    # ============================================================

    if date_fin:
        chefs_queryset = chefs_queryset.filter(
            date_fin__lte=date_fin
        )

    # ============================================================
    # TRI
    # ============================================================

    chefs_queryset = chefs_queryset.order_by(
        "-date_debut",
        "nom",
        "id",
    )

    # ============================================================
    # TOTAL RÉMUNÉRATION
    # ============================================================

    total_remuneration = (
        chefs_queryset.aggregate(
            total=Sum("montant")
        )["total"]
        or Decimal("0.00")
    )

    # ============================================================
    # LISTE
    # ============================================================

    chefs = list(
        chefs_queryset
    )

    # ============================================================
    # AUTORISATION MODIFICATION
    # ============================================================
    #
    # IMPORTANT :
    #
    # enregistre_par = Personnel
    #
    # request.current_user = AppUser
    #
    # Il faut donc comparer :
    #
    # chef.enregistre_par_id
    #
    # avec :
    #
    # current_user.personnel_id
    #
    # et NON avec request.session.user_id.
    #

    for chef in chefs:

        chef.peut_modifier = (
            personnel_connecte is not None
            and chef.enregistre_par_id
            == personnel_connecte.pk
        )

    # ============================================================
    # CONTEXTE
    # ============================================================

    context = {
        "projet": projet,

        "chefs": chefs,

        "current_user": current_user,

        "user": current_user,

        "personnel": personnel_connecte,

        "peut_gerer": peut_gerer,

        "aujourd_hui": timezone.localdate(),

        # Filtres
        "filtre_nom": nom,
        "filtre_date_debut": date_debut,
        "filtre_date_fin": date_fin,

        # Statistiques
        "total_chefs": len(chefs),
        "total_remuneration": total_remuneration,
    }

    # ============================================================
    # AFFICHAGE
    # ============================================================

    return render(
        request,
        "projet/chefEquipe/list.html",
        context,
    )

# ============================================================
# AJOUTER UN CHEF D'ÉQUIPE
# ============================================================

@project_manager_required
def chef_equipe_create(
    request,
    projet_id,
):
    """
    Enregistrer un chef d'équipe externe pour le projet.
    """

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    # --------------------------------------------------------
    # PERSONNEL CONNECTÉ
    # --------------------------------------------------------

    personnel_connecte = get_object_or_404(
        Personnel,
        pk=request.current_user.pk,
    )

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == "POST":

        form = ChefEquipeProjetForm(
            request.POST,
            request.FILES,
            projet=projet,
        )

        if form.is_valid():

            chef = form.save(
                commit=False
            )

            # ------------------------------------------------
            # VALEURS AUTOMATIQUES
            # ------------------------------------------------

            chef.projet = projet

            chef.type_class = "CHEF_EQUIPE"

            chef.type_contrat = "FORFAITAIRE"

            chef.enregistre_par = personnel_connecte

            chef.save()

            messages.success(
                request,
                (
                    f"Le chef d'équipe "
                    f"« {chef.nom} » a été enregistré "
                    f"pour le projet « {projet.titre} »."
                ),
            )

            return redirect(
                "projet:chef_equipe_list",
                projet_id=projet.pk,
            )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    else:

        form = ChefEquipeProjetForm(
            projet=projet,
        )

    # --------------------------------------------------------
    # TEMPLATE
    # --------------------------------------------------------

    return render(
        request,
        "projet/chefEquipe/form.html",
        {
            "form": form,
            "projet": projet,
            "chef": None,
            "mode": "ajout",
            "titre_page": "Ajouter un chef d'équipe",
            "user": request.current_user,
        },
    )


# ============================================================
# MODIFIER UN CHEF D'ÉQUIPE
# ============================================================

@project_manager_required
def chef_equipe_update(
    request,
    projet_id,
    pk,
):
    """
    Modifier un chef d'équipe.

    Seul le Personnel ayant enregistré le chef
    peut le modifier.
    """

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    chef = get_object_or_404(
        PersonnelExecutionProjet,
        pk=pk,
        projet=projet,
        type_class="CHEF_EQUIPE",
    )

    # --------------------------------------------------------
    # RÉCUPÉRER LE PERSONNEL CONNECTÉ
    # --------------------------------------------------------

    personnel_connecte = get_object_or_404(
        Personnel,
        pk=request.current_user.pk,
    )

    # --------------------------------------------------------
    # VÉRIFICATION DU CRÉATEUR
    # --------------------------------------------------------

    if chef.enregistre_par_id != personnel_connecte.pk:

        messages.error(
            request,
            (
                "Vous ne pouvez modifier que les chefs "
                "d'équipe que vous avez enregistrés."
            ),
        )

        return redirect(
            "projet:chef_equipe_list",
            projet_id=projet.pk,
        )

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == "POST":

        form = ChefEquipeProjetForm(
            request.POST,
            request.FILES,
            instance=chef,
            projet=projet,
        )

        if form.is_valid():

            chef_modifie = form.save(
                commit=False
            )

            # ------------------------------------------------
            # VALEURS PROJET
            # ------------------------------------------------

            chef_modifie.projet = projet

            chef_modifie.type_class = "CHEF_EQUIPE"

            chef_modifie.type_contrat = "FORFAITAIRE"

            # ------------------------------------------------
            # CONSERVATION DU CRÉATEUR
            # ------------------------------------------------

            chef_modifie.enregistre_par = chef.enregistre_par

            chef_modifie.save()

            messages.success(
                request,
                (
                    f"Le chef d'équipe "
                    f"« {chef_modifie.nom} » "
                    f"a été modifié avec succès."
                ),
            )

            return redirect(
                "projet:chef_equipe_list",
                projet_id=projet.pk,
            )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    else:

        form = ChefEquipeProjetForm(
            instance=chef,
            projet=projet,
        )

    # --------------------------------------------------------
    # AFFICHAGE
    # --------------------------------------------------------

    return render(
        request,
        "projet/ChefEquipe/form.html",
        {
            "form": form,
            "projet": projet,
            "chef": chef,
            "mode": "modification",
            "titre_page": "Modifier le chef d'équipe",
            "user": request.current_user,
        },
    )


# ============================================================
# SUPPRIMER UN CHEF D'ÉQUIPE
# ============================================================

@project_manager_required
def chef_equipe_delete(request,projet_id,pk,):
    """
    Supprimer un chef d'équipe.
    Seul le Personnel ayant enregistré le chef peut le supprimer.
    """

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    chef = get_object_or_404(
        PersonnelExecutionProjet,
        pk=pk,
        projet=projet,
        type_class="CHEF_EQUIPE",
    )

    # --------------------------------------------------------
    # RÉCUPÉRER LE PERSONNEL CONNECTÉ
    # --------------------------------------------------------

    personnel_connecte = get_object_or_404(
        Personnel,
        pk=request.current_user.pk,
    )

    # --------------------------------------------------------
    # VÉRIFICATION DU CRÉATEUR
    # --------------------------------------------------------

    if chef.enregistre_par_id != personnel_connecte.pk:

        messages.error(
            request,
            (
                "Vous ne pouvez supprimer que les chefs "
                "d'équipe que vous avez enregistrés."
            ),
        )

        return redirect(
            "projet:chef_equipe_list",
            projet_id=projet.pk,
        )

    # --------------------------------------------------------
    # GET : PAGE DE CONFIRMATION
    # --------------------------------------------------------

    if request.method != "POST":

        return render(
            request,
            "projet/chef_equipe_confirm_delete.html",
            {
                "projet": projet,
                "chef": chef,
                "user": request.current_user,
            },
        )

    # --------------------------------------------------------
    # POST : SUPPRESSION
    # --------------------------------------------------------

    nom = chef.nom

    try:

        chef.delete()

        messages.success(
            request,
            (
                f"Le chef d'équipe "
                f"« {nom} » a été supprimé avec succès."
            ),
        )

    except ProtectedError:

        messages.error(
            request,
            (
                "Impossible de supprimer ce chef d'équipe "
                "car il est déjà utilisé par des données "
                "du projet."
            ),
        )

    return redirect(
        "projet:chef_equipe_list",
        projet_id=projet.pk,
    )

# ============================================================
# CREER UN COMPTE UTILISATEUR POUR UN MEMBRE DU PROJET
# ============================================================

@project_manager_required
def utilisateur_projet_create(
    request,
    projet_id,
    equipe_id,
):

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    affectation = get_object_or_404(
        EquipeProjet.objects.select_related(
            "personnel"
        ),
        pk=equipe_id,
        projet=projet,
    )

    personnel = affectation.personnel

    if not personnel:

        messages.error(
            request,
            "Cette affectation ne possède pas de personnel interne.",
        )

        return redirect(
            "projet:equipe_list",
            projet_id=projet.pk,
        )

    compte_existant = (
        AppUser.objects
        .filter(
            personnel=personnel
        )
        .first()
    )

    if compte_existant:

        messages.warning(
            request,
            (
                f"{personnel} possède déjà un compte "
                f"utilisateur « {compte_existant.username} »."
            ),
        )

        return redirect(
            "projet:equipe_list",
            projet_id=projet.pk,
        )

    if request.method == "POST":

        username = request.POST.get(
            "username",
            "",
        ).strip()

        password = request.POST.get(
            "password",
            "",
        )

        password_confirmation = request.POST.get(
            "password_confirmation",
            "",
        )

        if not username:

            messages.error(
                request,
                "Le nom d'utilisateur est obligatoire.",
            )

        elif not password:

            messages.error(
                request,
                "Le mot de passe est obligatoire.",
            )

        elif password != password_confirmation:

            messages.error(
                request,
                "Les deux mots de passe ne correspondent pas.",
            )

        elif AppUser.objects.filter(
            username=username
        ).exists():

            messages.error(
                request,
                (
                    f"Le nom d'utilisateur "
                    f"« {username} » existe déjà."
                ),
            )

        else:

            utilisateur = AppUser.objects.create(
                personnel=personnel,
                username=username,
                password=make_password(password),
                role="UserProjet",
            )

            messages.success(
                request,
                (
                    f"Le compte « {utilisateur.username} » "
                    f"a été créé pour {personnel}."
                ),
            )

            return redirect(
                "projet:equipe_list",
                projet_id=projet.pk,
            )

    return render(
        request,
        "projet/utilisateur_projet_form.html",
        {
            "projet": projet,
            "affectation": affectation,
            "personnel": personnel,
            "user": request.current_user,
        },
    )


# ============================================================
# LISTE DES PROJETS
# ============================================================

@login_required_projet
def projet_list(request):

    user = request.current_user

    projets = Projet.objects.all()

    if user_can_manage_projects(user):

        projets = projets.order_by(
            "-date_debut",
            "-id",
        )

    else:

        personnel = getattr(
            user,
            "personnel",
            None,
        )

        if not personnel:

            projets = Projet.objects.none()

        else:

            aujourd_hui = timezone.localdate()

            projets = (
                Projet.objects
                .filter(
                    equipe__personnel=personnel,
                    equipe__actif=True,
                    equipe__date_debut__lte=aujourd_hui,
                    equipe__date_fin__gte=aujourd_hui,
                )
                .distinct()
                .order_by(
                    "-date_debut",
                    "-id",
                )
            )

    return render(
        request,
        "projet/projet_list.html",
        {
            "projets": projets,
            "user": user,
            "aujourd_hui": timezone.localdate(),
        },
    )


# ============================================================
# CREER UN PROJET
# ============================================================

@project_manager_required
def projet_create(request):

    if request.method == "POST":

        form = ProjetForm(
            request.POST
        )

        if form.is_valid():

            projet = form.save(
                commit=False
            )

            projet.enregistre_par = (
                request.current_user
            )

            projet.save()

            messages.success(
                request,
                "Le projet a été créé avec succès.",
            )

            return redirect(
                "projet:projet_detail",
                projet_id=projet.pk,
            )

    else:

        form = ProjetForm()

    return render(
        request,
        "projet/projet_form.html",
        {
            "form": form,
            "titre_page": "Nouveau projet",
            "projet": None,
            "mode": "creation",
            "user": request.current_user,
        },
    )


# ============================================================
# MODIFIER UN PROJET
# ============================================================

@project_manager_required
def projet_update(
    request,
    projet_id,
):

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    if request.method == "POST":

        form = ProjetForm(
            request.POST,
            instance=projet,
        )

        if form.is_valid():

            projet_modifie = form.save(
                commit=False
            )

            # Conservation du créateur initial.
            projet_modifie.enregistre_par_id = (
                projet.enregistre_par_id
            )

            projet_modifie.save()

            messages.success(
                request,
                "Le projet a été modifié avec succès.",
            )

            return redirect(
                "projet:projet_detail",
                projet_id=projet.pk,
            )

    else:

        form = ProjetForm(
            instance=projet,
        )

    return render(
        request,
        "projet/projet_form.html",
        {
            "form": form,
            "titre_page": "Modifier le projet",
            "projet": projet,
            "mode": "modification",
            "user": request.current_user,
        },
    )


# ============================================================
# SUPPRIMER UN PROJET
# ============================================================

@project_manager_required
def projet_delete(
    request,
    projet_id,
):

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    if projet.enregistre_par_id != request.current_user.id:

        messages.error(
            request,
            "Vous n'êtes pas autorisé à supprimer ce projet.",
        )

        return redirect(
            "projet:projet_detail",
            projet_id=projet.pk,
        )

    if request.method != "POST":

        return redirect(
            "projet:projet_detail",
            projet_id=projet.pk,
        )

    try:

        projet.delete()

        messages.success(
            request,
            "Le projet a été supprimé.",
        )

    except ProtectedError:

        messages.error(
            request,
            (
                "Impossible de supprimer ce projet car "
                "il possède des données liées."
            ),
        )

    return redirect(
        "projet:projet_list"
    )
# ============================================================
# DETAIL D'UN PROJET
# ============================================================

@login_required_projet
def projet_detail(
    request,
    projet_id,
):
    # ============================================================
    # UTILISATEUR CONNECTÉ
    # ============================================================

    current_user = request.current_user

    if not current_user:
        messages.error(
            request,
            "Utilisateur connecté introuvable.",
        )

        return redirect("users:login")

    # ============================================================
    # PROJET
    # ============================================================

    projet = get_object_or_404(
        Projet.objects
        .select_related(
            "enregistre_par",
        ),
        pk=projet_id,
    )

    # ============================================================
    # VÉRIFICATION ACCÈS PROJET
    # ============================================================

    if not user_has_project_access(
        current_user,
        projet,
    ):
        messages.error(
            request,
            "Votre accès à ce projet n'est pas actif.",
        )

        return redirect(
            "projet:projet_list"
        )

    # ============================================================
    # ÉQUIPE DU PROJET
    # ============================================================

    equipe = (
        projet.equipe
        .all()
        .select_related(
            "personnel",
            "personnel_execution",
            "personnel_execution__point_projet",
            "personnel_execution__materiau_projet",
        )
        .order_by(
            "fonction",
            "personnel__nom",
            "personnel__prenom",
        )
    )

    # ============================================================
    # ÉQUIPE ACTIVE
    # ============================================================

    equipe_active = sum(
        1
        for membre in equipe
        if membre.acces_actif
    )

    # ============================================================
    # FONCTION DU CONNECTÉ SUR LE PROJET
    # ============================================================

    fonction_projet = None

    # ------------------------------------------------------------
    # Personnel lié à l'utilisateur connecté
    # ------------------------------------------------------------

    personnel_connecte_id = getattr(
        current_user,
        "personnel_id",
        None,
    )

    if personnel_connecte_id:

        for membre in equipe:

            # ----------------------------------------------------
            # Personnel interne
            # ----------------------------------------------------

            if (
                membre.personnel_id
                and membre.personnel_id == personnel_connecte_id
            ):

                if membre.acces_actif:

                    fonction_projet = membre.fonction

                    break

            # ----------------------------------------------------
            # Personnel d'exécution lié à un personnel interne
            # ----------------------------------------------------

            if (
                membre.personnel_execution_id
                and membre.personnel_execution
            ):

                personnel_execution = (
                    membre.personnel_execution
                )

                if (
                    personnel_execution.personnel_id
                    and personnel_execution.personnel_id
                    == personnel_connecte_id
                ):

                    if membre.acces_actif:

                        fonction_projet = membre.fonction

                        break

    # ============================================================
    # POINTS DU PROJET
    # ============================================================

    points = (
        projet.points
        .all()
        .order_by(
            "nom",
        )
    )

    # ============================================================
    # CHEFS D'ÉQUIPE
    #
    # Les chefs d'équipe sont enregistrés dans
    # PersonnelExecutionProjet avec type_class=CHEF_EQUIPE.
    # ============================================================

    chefs_equipe = (
        PersonnelExecutionProjet.objects
        .filter(
            projet=projet,
            type_class="CHEF_EQUIPE",
        )
        .select_related(
            "projet",
            "point_projet",
            "enregistre_par",
        )
        .order_by(
            "nom",
            "date_debut",
            "-id",
        )
    )

    nombre_chefs_equipe = (
        chefs_equipe.count()
    )

    # ============================================================
    # PERSONNELS D'EXÉCUTION
    # ============================================================

    personnels_execution = (
        PersonnelExecutionProjet.objects
        .filter(
            projet=projet,
        )
        .select_related(
            "personnel",
            "point_projet",
            "materiau_projet",
            "enregistre_par",
        )
        .order_by(
            "type_class",
            "nom",
        )
    )

    # ============================================================
    # MINIERS
    # ============================================================

    miniers = (
        personnels_execution
        .filter(
            type_class="MINIER",
        )
    )

    nombre_miniers = (
        miniers.count()
    )

    # ============================================================
    # MATÉRIAUX DU PROJET
    #
    # IMPORTANT :
    # MateriauProjet.materiau est maintenant un CharField.
    #
    # Donc :
    #   select_related("materiau")       -> INTERDIT
    #   order_by("materiau__nom")        -> INTERDIT
    #
    # On utilise directement :
    #   order_by("materiau", "id")
    # ============================================================

    materiaux_projet = (
        projet.materiaux_projet
        .all()
        .select_related(
            "projet",
        )
        .order_by(
            "materiau",
            "id",
        )
    )

    nombre_materiaux_projet = (
        materiaux_projet.count()
    )

    # ============================================================
    # RAPPORTS D'AVANCEMENT
    # ============================================================

    rapports_projet = (
        projet.rapports_projet
        .all()
        .select_related(
            "auteur",
        )
        .order_by(
            "-date_rapport",
        )
    )

    # ============================================================
    # RAPPORTS TRAVAUX
    # ============================================================

    rapports_travaux = (
        projet.rapports_travaux
        .all()
        .select_related(
            "auteur",
        )
        .order_by(
            "-date_debut",
        )
    )

    # ============================================================
    # RAPPORTS MATÉRIAUX
    #
    # Ici "materiau" est conservé uniquement si le modèle
    # RapportMateriau possède bien un ForeignKey nommé materiau.
    # ============================================================

    rapports_materiaux = (
        projet.rapports_materiaux
        .all()
        .select_related(
            "materiau",
            "auteur",
        )
        .order_by(
            "-date_ravitaillement",
        )
    )

    # ============================================================
    # RAPPORTS VÉHICULES
    # ============================================================

    rapports_vehicules = (
        projet.rapports_vehicules
        .all()
        .select_related(
            "vehicule",
            "chauffeur",
        )
        .order_by(
            "-date_rapport",
        )
    )

    # ============================================================
    # NOMBRE DE RAPPORTS
    # ============================================================

    total_rapports = (
        rapports_projet.count()
        + rapports_travaux.count()
        + rapports_materiaux.count()
        + rapports_vehicules.count()
    )

    nombre_rapports_travaux = (
        rapports_travaux.count()
    )

    # ============================================================
    # IMPORTS MATÉRIAUX / TRANSPORT / DÉPENSES
    # ============================================================

    from materiaux.models import (
        MateriauxOut,
        ActiviteTransport,
        ReceptionMateriau,
        UtilisationMateriau,
        MateriauxRetour,
        Depense,
        DepenseGasoil,
        ReparationVehicule,
        PaiementDocker,
    )

    # ============================================================
    # SORTIES MATÉRIAUX
    # ============================================================

    sorties_materiaux = (
        MateriauxOut.objects
        .filter(
            projet=projet,
        )
        .select_related(
            "materiau",
            "division",
            "point_projet",
        )
    )

    # ============================================================
    # ACTIVITÉS TRANSPORT
    # ============================================================

    transports = (
        ActiviteTransport.objects
        .filter(
            projet=projet,
        )
        .select_related(
            "vehicule",
            "chauffeur_personnel",
            "point_projet",
            "sortie_materiau",
        )
    )

    # ============================================================
    # RÉCEPTIONS
    # ============================================================

    receptions = (
        ReceptionMateriau.objects
        .filter(
            projet=projet,
        )
        .select_related(
            "transport",
            "point",
        )
    )

    # ============================================================
    # UTILISATIONS
    # ============================================================

    utilisations = (
        UtilisationMateriau.objects
        .filter(
            reception__projet=projet,
        )
    )

    # ============================================================
    # RETOURS
    # ============================================================

    retours = (
        MateriauxRetour.objects
        .filter(
            sortie__projet=projet,
        )
    )

    # ============================================================
    # DÉPENSES
    # ============================================================

    depenses = (
        Depense.objects
        .filter(
            projet=projet,
        )
    )

    # ============================================================
    # DÉPENSES GASOIL
    # ============================================================

    depenses_gasoil = (
        DepenseGasoil.objects
        .filter(
            projet=projet,
        )
    )

    # ============================================================
    # RÉPARATIONS
    # ============================================================

    reparations = (
        ReparationVehicule.objects
        .filter(
            projet=projet,
        )
    )

    # ============================================================
    # PAIEMENTS DOCKERS
    # ============================================================

    paiements_dockers = (
        PaiementDocker.objects
        .filter(
            projet=projet,
        )
    )

    # ============================================================
    # TOTAUX MATÉRIAUX
    # ============================================================

    total_sorties = (
        sorties_materiaux
        .aggregate(
            total=Sum("quantite"),
        )["total"]
        or 0
    )

    total_transport = (
        transports
        .aggregate(
            total=Sum("quantite"),
        )["total"]
        or 0
    )

    total_reception = (
        receptions
        .aggregate(
            total=Sum("quantite_recue"),
        )["total"]
        or 0
    )

    total_utilisation = (
        utilisations
        .aggregate(
            total=Sum("quantite_utilisee"),
        )["total"]
        or 0
    )

    total_retour = (
        retours
        .aggregate(
            total=Sum("quantite"),
        )["total"]
        or 0
    )

    # ============================================================
    # TOTAL MATÉRIAUX RAVITAILLÉS
    # ============================================================

    total_materiaux = (
        total_sorties
    )

    # ============================================================
    # TOTAUX DÉPENSES
    # ============================================================

    total_depenses = (
        depenses
        .aggregate(
            total=Sum("montant"),
        )["total"]
        or 0
    )

    total_gasoil = (
        depenses_gasoil
        .aggregate(
            total=Sum("total"),
        )["total"]
        or 0
    )

    total_reparations = (
        reparations
        .aggregate(
            total=Sum("total"),
        )["total"]
        or 0
    )

    total_dockers = (
        paiements_dockers
        .aggregate(
            total=Sum("montant"),
        )["total"]
        or 0
    )

    # ============================================================
    # TOTAL GLOBAL DÉPENSES PROJET
    # ============================================================

    total_depenses_projet = (
        total_depenses
        + total_gasoil
        + total_reparations
        + total_dockers
    )

    # ============================================================
    # PERMISSION DE GESTION
    # ============================================================

    peut_gerer = user_can_manage_projects(
        current_user
    )

    # ============================================================
    # ACCÈS ACTUEL
    # ============================================================

    acces_actuel = user_has_project_access(
        current_user,
        projet,
    )

    # ============================================================
    # CONTEXTE
    # ============================================================

    context = {

        # --------------------------------------------------------
        # PROJET
        # --------------------------------------------------------

        "projet": projet,

        # --------------------------------------------------------
        # UTILISATEUR
        # --------------------------------------------------------

        "user": current_user,
        "current_user": current_user,

        # --------------------------------------------------------
        # PERMISSIONS
        # --------------------------------------------------------

        "peut_gerer": peut_gerer,
        "acces_actuel": acces_actuel,

        # --------------------------------------------------------
        # FONCTION SUR LE PROJET
        # --------------------------------------------------------

        "fonction_projet": fonction_projet,

        # --------------------------------------------------------
        # ÉQUIPE
        # --------------------------------------------------------

        "equipe": equipe,
        "equipe_active": equipe_active,

        # --------------------------------------------------------
        # CHEFS D'ÉQUIPE
        # --------------------------------------------------------

        "chefs_equipe": chefs_equipe,
        "nombre_chefs_equipe": nombre_chefs_equipe,

        # --------------------------------------------------------
        # PERSONNEL D'EXÉCUTION
        # --------------------------------------------------------

        "personnels_execution": personnels_execution,

        # --------------------------------------------------------
        # MINIERS
        # --------------------------------------------------------

        "miniers": miniers,
        "nombre_miniers": nombre_miniers,

        # --------------------------------------------------------
        # POINTS
        # --------------------------------------------------------

        "points": points,

        # --------------------------------------------------------
        # MATÉRIAUX DU PROJET
        # --------------------------------------------------------

        "materiaux_projet": materiaux_projet,
        "nombre_materiaux_projet": nombre_materiaux_projet,

        # --------------------------------------------------------
        # RAPPORTS
        # --------------------------------------------------------

        "rapports_projet": rapports_projet,
        "rapports_travaux": rapports_travaux,
        "rapports_materiaux": rapports_materiaux,
        "rapports_vehicules": rapports_vehicules,

        "total_rapports": total_rapports,
        "nombre_rapports_travaux": nombre_rapports_travaux,

        # --------------------------------------------------------
        # MATÉRIAUX / LOGISTIQUE
        # --------------------------------------------------------

        "sorties_materiaux": sorties_materiaux,
        "transports": transports,
        "receptions": receptions,
        "utilisations": utilisations,
        "retours": retours,

        "total_sorties": total_sorties,
        "total_transport": total_transport,
        "total_reception": total_reception,
        "total_utilisation": total_utilisation,
        "total_retour": total_retour,

        "total_materiaux": total_materiaux,

        # --------------------------------------------------------
        # DÉPENSES
        # --------------------------------------------------------

        "depenses": depenses,
        "depenses_gasoil": depenses_gasoil,
        "reparations": reparations,
        "paiements_dockers": paiements_dockers,

        "total_depenses": total_depenses,
        "total_gasoil": total_gasoil,
        "total_reparations": total_reparations,
        "total_dockers": total_dockers,

        "total_depenses_projet": total_depenses_projet,

        # --------------------------------------------------------
        # DATE
        # --------------------------------------------------------

        "aujourd_hui": timezone.localdate(),
    }

    # ============================================================
    # AFFICHAGE
    # ============================================================

    return render(
        request,
        "projet/projet_detail.html",
        context,
    )


# ============================================================
# RAPPORT GLOBAL DU PROJET
# ============================================================

@project_access_required
def rapport_projet_global(
    request,
    projet_id,
):

    projet = request.projet

    rapports_projet = (
        RapportProjet.objects
        .filter(
            projet=projet
        )
        .select_related(
            "auteur"
        )
    )

    rapports_travaux = (
        RapportTravail.objects
        .filter(
            projet=projet
        )
        .select_related(
            "point",
            "auteur",
        )
    )

    rapports_materiaux = (
        RapportMateriau.objects
        .filter(
            projet=projet
        )
        .select_related(
            "point",
            "materiau",
            "auteur",
        )
    )

    rapports_vehicules = (
        RapportVehicule.objects
        .filter(
            projet=projet
        )
        .select_related(
            "vehicule",
            "chauffeur",
        )
    )

    total_rapports = (
        rapports_projet.count()
        + rapports_travaux.count()
        + rapports_materiaux.count()
        + rapports_vehicules.count()
    )

    return render(
        request,
        "projet/rapport.html",
        {
            "projet": projet,
            "rapports_projet": rapports_projet,
            "rapports_travaux": rapports_travaux,
            "rapports_materiaux": rapports_materiaux,
            "rapports_vehicules": rapports_vehicules,
            "total_rapports": total_rapports,
            "user": request.current_user,
            "peut_gerer": user_can_manage_projects(
                request.current_user
            ),
            "aujourd_hui": timezone.localdate(),
        },
    )


# ============================================================
# EQUIPE - LISTE
# ============================================================

@project_manager_required
def equipe_list(
    request,
    projet_id,
):

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    equipe = (
        EquipeProjet.objects
        .filter(
            projet=projet
        )
        .select_related(
            "personnel",
        )
        .order_by(
            "fonction",
            "personnel__nom",
            "personnel__prenom",
        )
    )

    return render(
        request,
        "projet/equipage/list.html",
        {
            "projet": projet,
            "equipe": equipe,
            "user": request.current_user,
            "peut_gerer": user_can_manage_projects(
                request.current_user
            ),
        },
    )


# ============================================================
# CREATION D'UNE AFFECTATION D'EQUIPE
# ============================================================

@project_manager_required
def equipe_create(
    request,
    projet_id,
):

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    if request.method == "POST":

        form = EquipeProjetForm(
            request.POST,
            projet=projet,
        )

        form.instance.projet = projet

        form = prepare_equipe_form(
            form,
            projet=projet,
        )

        if form.is_valid():

            affectation = form.save(
                commit=False
            )

            affectation.projet = projet
            affectation.save()

            messages.success(
                request,
                (
                    f"{affectation.personnel} a été affecté "
                    f"au projet « {projet.titre} » comme "
                    f"{affectation.get_fonction_display()}."
                ),
            )

            return redirect(
                "projet:equipe_list",
                projet_id=projet.pk,
            )

    else:

        form = EquipeProjetForm(
            projet=projet,
        )

        form.instance.projet = projet

        form = prepare_equipe_form(
            form,
            projet=projet,
        )

        if "date_debut" in form.fields:
            form.fields["date_debut"].initial = (
                projet.date_debut
            )

        if "date_fin" in form.fields:
            form.fields["date_fin"].initial = (
                projet.date_fin
            )

        if "actif" in form.fields:
            form.fields["actif"].initial = True

    return render(
        request,
        "projet/equipage/form.html",
        {
            "form": form,
            "projet": projet,
            "affectation": None,
            "mode": "creation",
            "titre_page": "Ajouter personnel",
            "user": request.current_user,
        },
    )


# ============================================================
# MODIFIER UNE AFFECTATION
# ============================================================

@project_manager_required
def equipe_update(
    request,
    projet_id,
    equipe_id,
):

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    affectation = get_object_or_404(
        EquipeProjet,
        pk=equipe_id,
        projet=projet,
    )

    if request.method == "POST":

        form = EquipeProjetForm(
            request.POST,
            instance=affectation,
            projet=projet,
        )

        form.instance.projet = projet

        form = prepare_equipe_form(
            form,
            projet=projet,
            affectation=affectation,
        )

        if form.is_valid():

            affectation_modifiee = form.save(
                commit=False
            )

            affectation_modifiee.projet = projet
            affectation_modifiee.save()

            messages.success(
                request,
                (
                    f"L'affectation de "
                    f"{affectation_modifiee.personnel} "
                    f"a été modifiée avec succès."
                ),
            )

            return redirect(
                "projet:equipe_list",
                projet_id=projet.pk,
            )

    else:

        form = EquipeProjetForm(
            instance=affectation,
            projet=projet,
        )

        form = prepare_equipe_form(
            form,
            projet=projet,
            affectation=affectation,
        )

    return render(
        request,
        "projet/equipage/form.html",
        {
            "form": form,
            "projet": projet,
            "affectation": affectation,
            "mode": "modification",
            "titre_page": "Modifier l'affectation",
            "user": request.current_user,
            "peut_gerer": user_can_manage_projects(
                request.current_user
            ),
        },
    )


# ============================================================
# SUPPRIMER UNE AFFECTATION
# ============================================================

@project_manager_required
def equipe_delete(
    request,
    projet_id,
    equipe_id,
):

    affectation = get_object_or_404(
        EquipeProjet,
        pk=equipe_id,
        projet_id=projet_id,
    )

    if request.method != "POST":

        messages.error(
            request,
            (
                "La suppression d'une affectation "
                "doit être effectuée par POST."
            ),
        )

        return redirect(
            "projet:equipe_list",
            projet_id=projet_id,
        )

    try:

        personnel = affectation.personnel

        affectation.delete()

        messages.success(
            request,
            (
                f"L'affectation de {personnel} "
                f"a été supprimée du projet."
            ),
        )

    except ProtectedError:

        messages.error(
            request,
            (
                "Cette affectation est utilisée "
                "par des données historiques "
                "et ne peut pas être supprimée."
            ),
        )

    return redirect(
        "projet:equipe_list",
        projet_id=projet_id,
    )


# ============================================================
# POINTS - LISTE
# ============================================================

@login_required_projet
def point_list(
    request,
    projet_id,
):

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    if not user_has_project_access(
        request.current_user,
        projet,
    ):
        return redirect(
            "projet:projet_list"
        )

    points = (
        PointProjet.objects
        .filter(
            projet=projet
        )
        .order_by(
            "nom"
        )
    )

    return render(
        request,
        "projet/point/list.html",
        {
            "projet": projet,
            "points": points,
            "user": request.current_user,
        },
    )


# ============================================================
# AJOUTER UN POINT
# ============================================================

@login_required_projet
def point_create(
    request,
    projet_id,
):

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    if request.method == "POST":

        form = PointProjetForm(
            request.POST,
            projet=projet,
        )

        form.instance.projet = projet

        if form.is_valid():

            point = form.save(
                commit=False
            )

            point.projet = projet
            point.save()

            messages.success(
                request,
                "Le point de chantier a été créé.",
            )

            return redirect(
                "projet:point_list",
                projet_id=projet.pk,
            )

    else:

        form = PointProjetForm(
            projet=projet,
        )

    return render(
        request,
        "projet/point/form.html",
        {
            "form": form,
            "projet": projet,
            "titre_page": "Nouveau point de chantier",
            "user": request.current_user,
        },
    )


# ============================================================
# MODIFIER UN POINT
# ============================================================

@project_manager_required
def point_update(
    request,
    projet_id,
    point_id,
):

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    point = get_object_or_404(
        PointProjet,
        pk=point_id,
        projet=projet,
    )

    if request.method == "POST":

        form = PointProjetForm(
            request.POST,
            instance=point,
            projet=projet,
        )

        form.instance.projet = projet

        if form.is_valid():

            point_modifie = form.save(
                commit=False
            )

            point_modifie.projet = projet
            point_modifie.save()

            messages.success(
                request,
                "Le point de chantier a été modifié.",
            )

            return redirect(
                "projet:point_list",
                projet_id=projet.pk,
            )

    else:

        form = PointProjetForm(
            instance=point,
            projet=projet,
        )

    return render(
        request,
        "projet/point_form.html",
        {
            "form": form,
            "projet": projet,
            "point": point,
            "titre_page": "Modifier le point de chantier",
            "user": request.current_user,
        },
    )


# ============================================================
# SUPPRIMER UN POINT
# ============================================================

@project_manager_required
def point_delete(
    request,
    projet_id,
    point_id,
):

    point = get_object_or_404(
        PointProjet,
        pk=point_id,
        projet_id=projet_id,
    )

    if request.method == "POST":

        try:

            point.delete()

            messages.success(
                request,
                "Le point de chantier a été supprimé.",
            )

        except ProtectedError:

            messages.error(
                request,
                (
                    "Impossible de supprimer ce point car "
                    "il est utilisé par des données du projet."
                ),
            )

    return redirect(
        "projet:point_list",
        projet_id=projet_id,
    )


@login_required_projet
def minier_list(request, projet_id):

    current_user = request.current_user

    if not current_user:
        messages.error(
            request,
            "Utilisateur connecté introuvable."
        )
        return redirect("users:login")

    # ============================================================
    # PROJET
    # ============================================================

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    # ============================================================
    # ACCÈS AU PROJET
    # ============================================================

    if not user_has_project_access(
        current_user,
        projet,
    ):
        messages.error(
            request,
            "Votre accès à ce projet n'est pas actif."
        )
        return redirect(
            "projet:projet_list"
        )

    # ============================================================
    # PERSONNEL CONNECTÉ
    # ============================================================

    personnel_connecte = getattr(
        current_user,
        "personnel",
        None,
    )

    # ============================================================
    # DROIT DE GESTION
    # ============================================================

    peut_gerer = user_can_manage_materiaux(
        current_user,
        projet,
    )

    # ============================================================
    # FILTRES GET
    # ============================================================

    filtre_nom = request.GET.get(
        "nom",
        "",
    ).strip()

    filtre_materiau = request.GET.get(
        "materiau",
        "",
    ).strip()

    filtre_date_debut = request.GET.get(
        "date_debut",
        "",
    ).strip()

    filtre_date_fin = request.GET.get(
        "date_fin",
        "",
    ).strip()

    # ============================================================
    # CONVERSION DES DATES
    # ============================================================

    date_debut = None
    date_fin = None

    if filtre_date_debut:
        try:
            date_debut = datetime.strptime(
                filtre_date_debut,
                "%Y-%m-%d",
            ).date()
        except ValueError:
            messages.warning(
                request,
                "La date de début est invalide."
            )
            filtre_date_debut = ""

    if filtre_date_fin:
        try:
            date_fin = datetime.strptime(
                filtre_date_fin,
                "%Y-%m-%d",
            ).date()
        except ValueError:
            messages.warning(
                request,
                "La date de fin est invalide."
            )
            filtre_date_fin = ""

    # ============================================================
    # QUERYSET DE BASE
    # ============================================================

    miniers_queryset = (
        PersonnelExecutionProjet.objects
        .filter(
            projet=projet,
            type_class="MINIER",
        )
        .select_related(
            "projet",
            "materiau_projet",
            "point_projet",
            "enregistre_par",
        )
    )

    # ============================================================
    # FILTRE NOM
    # ============================================================

    if filtre_nom:

        miniers_queryset = miniers_queryset.filter(
            nom__icontains=filtre_nom
        )

    # ============================================================
    # FILTRE MATÉRIAU
    #
    # MateriauProjet.materiau est un CharField.
    # ============================================================

    if filtre_materiau:

        miniers_queryset = miniers_queryset.filter(
            materiau_projet__materiau__icontains=filtre_materiau
        )

    # ============================================================
    # FILTRE DATE DE DÉBUT
    # ============================================================

    if date_debut:

        miniers_queryset = miniers_queryset.filter(
            date_production__gte=date_debut
        )

    # ============================================================
    # FILTRE DATE DE FIN
    # ============================================================

    if date_fin:

        miniers_queryset = miniers_queryset.filter(
            date_production__lte=date_fin
        )

    # ============================================================
    # SÉCURITÉ :
    # DATE DÉBUT > DATE FIN
    # ============================================================

    if date_debut and date_fin:

        if date_debut > date_fin:

            messages.warning(
                request,
                "La date de début ne peut pas être postérieure "
                "à la date de fin."
            )

            # On remet la liste à zéro afin d'éviter
            # un résultat incohérent.

            miniers_queryset = miniers_queryset.none()

    # ============================================================
    # ORDRE
    # ============================================================

    miniers_queryset = miniers_queryset.order_by(
        "-date_production",
        "nom",
        "id",
    )

    # ============================================================
    # NOMBRE DE MINIERS
    #
    # Ce nombre respecte les filtres.
    # ============================================================

    total_miniers = miniers_queryset.count()
    total_montant = (
        miniers_queryset.aggregate(
            total=Sum(
                ExpressionWrapper(
                    F("quantite") * F("prix_unitaire"),
                    output_field=DecimalField(
                        max_digits=20,
                        decimal_places=2,
                    ),
                )
            )
        )["total"]
    )

    # ============================================================
    # AUCUN RÉSULTAT
    # ============================================================

    if total_montant is None:

        total_montant = Decimal(
            "0.00"
        )

    # ============================================================
    # FORMAT DÉCIMAL
    # ============================================================

    total_montant = total_montant.quantize(
        Decimal("0.01")
    )

    # ============================================================
    # TRANSFORMATION EN LISTE
    # ============================================================

    miniers = list(
        miniers_queryset
    )

    # ============================================================
    # DROIT DE MODIFICATION / SUPPRESSION
    # ============================================================

    for minier in miniers:

        minier.peut_modifier = (
            personnel_connecte is not None
            and minier.enregistre_par_id is not None
            and minier.enregistre_par_id
            == personnel_connecte.pk
        )

    # ============================================================
    # CONTEXT
    # ============================================================

    context = {

        # --------------------------------------------------------
        # PROJET
        # --------------------------------------------------------

        "projet": projet,

        # --------------------------------------------------------
        # LISTE
        # --------------------------------------------------------

        "miniers": miniers,

        # --------------------------------------------------------
        # STATISTIQUES
        # --------------------------------------------------------

        "total_miniers": total_miniers,

        "total_montant": total_montant,

        # --------------------------------------------------------
        # UTILISATEUR
        # --------------------------------------------------------

        "current_user": current_user,

        "user": current_user,

        "personnel": personnel_connecte,

        # --------------------------------------------------------
        # DROITS
        # --------------------------------------------------------

        "peut_gerer": peut_gerer,

        # --------------------------------------------------------
        # VALEURS DES FILTRES
        #
        # Elles permettent de conserver les valeurs
        # dans les champs après validation.
        # --------------------------------------------------------

        "filtre_nom": filtre_nom,

        "filtre_materiau": filtre_materiau,

        "filtre_date_debut": filtre_date_debut,

        "filtre_date_fin": filtre_date_fin,
    }

    # ============================================================
    # RENDU
    # ============================================================

    return render(
        request,
        "projet/minier/list.html",
        context,
    )


# ============================================================
# MINIER PROJET - AJOUT
# ============================================================

@project_manager_required
def minier_projet_create(request, projet_id):

    projet = get_object_or_404(
        Projet,
        pk=projet_id
    )

    if request.method == "POST":

        form = MinierProjetForm(
            request.POST,
            request.FILES,
            projet=projet,
        )

        if form.is_valid():

            minier = form.save(
                commit=False
            )

            minier.projet = projet
            minier.type_class = "MINIER"
            minier.type_contrat = "PRE_PAYER"

            # ------------------------------------------------
            # Utilisateur connecté
            # ------------------------------------------------

            user_id = request.session.get(
                "user_id"
            )

            if user_id:

                try:

                    minier.enregistre_par = (
                        Personnel.objects.get(
                            pk=user_id
                        )
                    )

                except Personnel.DoesNotExist:

                    minier.enregistre_par = None

            minier.save()

            messages.success(
                request,
                "Le Minier a été enregistré avec succès."
            )

            return redirect(
                "projet:minier_projet_list",
                projet_id=projet.pk,
            )

    else:

        form = MinierProjetForm(
            projet=projet
        )

    return render(
        request,
        "projet/miniers/form.html",
        {
            "form": form,
            "projet": projet,
            "titre": "Ajouter un Minier",
        }
    )




# ============================================================
# MINIER PROJET - MODIFICATION
# ============================================================

@project_manager_required
def minier_projet_update(request, projet_id, pk):

    projet = get_object_or_404(
        Projet,
        pk=projet_id
    )

    minier = get_object_or_404(
        PersonnelExecutionProjet,
        pk=pk,
        projet=projet,
        type_class="MINIER",
    )

    # --------------------------------------------------------
    # Seul le créateur peut modifier
    # --------------------------------------------------------

    user_id = request.session.get(
        "user_id"
    )

    if (
        minier.enregistre_par_id
        and str(minier.enregistre_par_id) != str(user_id)
    ):

        messages.error(
            request,
            "Vous n'êtes pas autorisé à modifier ce Minier."
        )

        return redirect(
            "projet:minier_projet_list",
            projet_id=projet.pk,
        )

    if request.method == "POST":

        form = MinierProjetForm(
            request.POST,
            request.FILES,
            instance=minier,
            projet=projet,
        )

        if form.is_valid():

            minier = form.save(
                commit=False
            )

            minier.projet = projet
            minier.type_class = "MINIER"
            minier.type_contrat = "PRE_PAYER"

            minier.save()

            messages.success(
                request,
                "Le Minier a été modifié avec succès."
            )

            return redirect(
                "projet:minier_projet_list",
                projet_id=projet.pk,
            )

    else:

        form = MinierProjetForm(
            instance=minier,
            projet=projet,
        )

    return render(
        request,
        "projet/miniers/form.html",
        {
            "form": form,
            "projet": projet,
            "minier": minier,
            "titre": "Modifier le Minier",
        }
    )

# ============================================================
# RAPPORT PROJET - LISTE
# ============================================================

@project_access_required
def rapport_projet_list(
    request,
    projet_id,
):

    rapports = (
        RapportProjet.objects
        .filter(
            projet=request.projet
        )
        .select_related(
            "auteur"
        )
    )

    return render(
        request,
        "projet/rapport_projet_list.html",
        {
            "projet": request.projet,
            "rapports": rapports,
            "user": request.current_user,
        },
    )


# ============================================================
# SELECTION PROJET POUR RAPPORT
# ============================================================

@login_required_projet
def rapport_projet_selection(request):

    projets = (
        Projet.objects
        .all()
        .order_by(
            "-date_debut",
            "-id",
        )
    )

    if not user_can_manage_projects(
        request.current_user
    ):

        personnel = getattr(
            request.current_user,
            "personnel",
            None,
        )

        if not personnel:

            projets = Projet.objects.none()

        else:

            aujourd_hui = timezone.localdate()

            projets = (
                Projet.objects
                .filter(
                    equipe__personnel=personnel,
                    equipe__actif=True,
                    equipe__date_debut__lte=aujourd_hui,
                    equipe__date_fin__gte=aujourd_hui,
                )
                .distinct()
                .order_by(
                    "-date_debut",
                    "-id",
                )
            )

    return render(
        request,
        "projet/rapport_projet_selection.html",
        {
            "projets": projets,
            "user": request.current_user,
            "aujourd_hui": timezone.localdate(),
        },
    )


# ============================================================
# CREER RAPPORT PROJET
# ============================================================

@project_access_required
def rapport_projet_create(
    request,
    projet_id,
):

    projet = request.projet
    user = request.current_user

    if not user_has_project_function(
        user,
        projet,
        ["INGENIEUR"],
    ):

        messages.error(
            request,
            (
                "Seul l'Ingénieur Responsable du Chantier "
                "peut créer ce rapport."
            ),
        )

        return redirect(
            "projet:projet_detail",
            projet_id=projet.pk,
        )

    if request.method == "POST":

        form = RapportProjetForm(
            request.POST
        )

        if form.is_valid():

            rapport = form.save(
                commit=False
            )

            rapport.projet = projet
            rapport.auteur = user.personnel

            rapport.save()

            messages.success(
                request,
                "Le rapport de projet a été enregistré.",
            )

            return redirect(
                "projet:rapport_projet_list",
                projet_id=projet.pk,
            )

    else:

        form = RapportProjetForm()

    return render(
        request,
        "projet/rapport_projet_form.html",
        {
            "form": form,
            "projet": projet,
            "titre_page": "Nouveau rapport de projet",
            "user": user,
        },
    )


# ============================================================
# MODIFIER RAPPORT PROJET
# ============================================================

@project_access_required
def rapport_projet_update(
    request,
    projet_id,
    rapport_id,
):

    projet = request.projet

    rapport = get_object_or_404(
        RapportProjet,
        pk=rapport_id,
        projet=projet,
    )

    if request.method == "POST":

        form = RapportProjetForm(
            request.POST,
            instance=rapport,
        )

        if form.is_valid():

            rapport_modifie = form.save(
                commit=False
            )

            rapport_modifie.projet = projet
            rapport_modifie.auteur = rapport.auteur
            rapport_modifie.save()

            messages.success(
                request,
                "Le rapport a été modifié.",
            )

            return redirect(
                "projet:rapport_projet_list",
                projet_id=projet.pk,
            )

    else:

        form = RapportProjetForm(
            instance=rapport,
        )

    return render(
        request,
        "projet/rapport_projet_form.html",
        {
            "form": form,
            "projet": projet,
            "rapport": rapport,
            "titre_page": "Modifier le rapport",
            "user": request.current_user,
        },
    )


# ============================================================
# RAPPORT TRAVAIL - LISTE
# ============================================================

@project_access_required
def rapport_travail_list(
    request,
    projet_id,
):

    rapports = (
        RapportTravail.objects
        .filter(
            projet=request.projet
        )
        .select_related(
            "point",
            "auteur",
        )
    )

    return render(
        request,
        "projet/rapport_travail_list.html",
        {
            "projet": request.projet,
            "rapports": rapports,
            "user": request.current_user,
        },
    )


# ============================================================
# RAPPORT TRAVAIL - CREER
# ============================================================

@project_access_required
def rapport_travail_create(
    request,
    projet_id,
):

    projet = request.projet
    user = request.current_user

    if not user_has_project_function(
        user,
        projet,
        ["CHEF_CHANTIER"],
    ):

        messages.error(
            request,
            (
                "Seul le Chef de Chantier peut enregistrer "
                "un rapport de travail."
            ),
        )

        return redirect(
            "projet:projet_detail",
            projet_id=projet.pk,
        )

    if request.method == "POST":

        form = RapportTravailForm(
            request.POST,
            request.FILES,
            projet=projet,
        )

        if form.is_valid():

            rapport = form.save(
                commit=False
            )

            rapport.projet = projet
            rapport.auteur = user.personnel

            rapport.save()

            messages.success(
                request,
                "Le rapport de travail a été enregistré.",
            )

            return redirect(
                "projet:rapport_travail_list",
                projet_id=projet.pk,
            )

    else:

        form = RapportTravailForm(
            projet=projet,
        )

    return render(
        request,
        "projet/rapport_travail_form.html",
        {
            "form": form,
            "projet": projet,
            "titre_page": "Nouveau rapport de travail",
            "user": user,
        },
    )

# ============================================================
# RAPPORT MATERIAU - CREER
# ============================================================

# @login_required_projet
def rapport_materiau_create(request, projet_id):
    """
    Ajout d'un rapport matériau pour un projet.
    """

    # ============================================================
    # PROJET
    # ============================================================
    projet = get_object_or_404(
        Projet,
        pk=projet_id
    )
    # ============================================================
    # CONTRÔLE D'ACCÈS AU PROJET
    # ============================================================
    if not user_has_project_access(
        request.current_user,
        projet
    ):
        messages.error(
            request,
            "Votre accès à ce projet n'est pas actif."
        )
        return redirect(
            "projet:projet_list"
        )

    # ============================================================
    # DROIT DE GESTION
    # ============================================================
    if not user_can_manage_projects(
        request.current_user
    ):
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'ajouter "
            "un rapport matériau."
        )
        return redirect(
            "projet:rapport_materiau_list",
            projet_id=projet.id
        )

    # ============================================================
    # FORMULAIRE
    # ============================================================
    if request.method == "POST":

        form = RapportMateriauProjetForm(
            request.POST,
            request.FILES,
            projet=projet
        )

        if form.is_valid():

            rapport = form.save(
                commit=False
            )

            # ----------------------------------------------------
            # PROJET
            # ----------------------------------------------------
            rapport.projet = projet

            # ----------------------------------------------------
            # ENREGISTRÉ PAR
            # ----------------------------------------------------
            personnel_connecte = Personnel.objects.filter(
                pk=request.current_user.pk
            ).first()

            rapport.enregistre_par = personnel_connecte

            # ----------------------------------------------------
            # SAUVEGARDE
            # ----------------------------------------------------
            rapport.save()

            messages.success(
                request,
                "Le rapport matériau a été ajouté avec succès."
            )

            return redirect(
                "projet:rapport_materiau_list",
                projet_id=projet.id
            )

    else:

        form = RapportMateriauProjetForm(
            projet=projet
        )

    # ============================================================
    # CONTEXTE
    # ============================================================
    context = {
        "projet": projet,
        "form": form,
        "titre": "Ajouter un rapport matériau",
        "mode": "create",
        "user": request.current_user,
    }

    # ============================================================
    # TEMPLATE
    # ============================================================
    return render(
        request,
        "projet/rapport_materiau/form.html",
        context
    )



# ============================================================
# VÉHICULES / ENGIN AFFECTÉS AUX PROJETS
# CRUD COMPLET
# ============================================================


# ============================================================
# LISTE - READ
# ============================================================

@login_required_projet
def vehicule_projet_list(request,projet_id,):

    projet = get_object_or_404(Projet,pk=projet_id,)

    # --------------------------------------------------------
    # VÉRIFICATION DE L'ACCÈS AU PROJET
    # --------------------------------------------------------

    if not user_has_project_access(request.current_user,projet,):

        messages.error(request,"Votre accès à ce projet n'est pas actif.",)

        return redirect("projet:projet_list")

    # --------------------------------------------------------
    # LISTE DES AFFECTATIONS
    # --------------------------------------------------------

    affectations = (
        VehiculeProjet.objects
        .filter(
            projet=projet,
        )
        .select_related(
            "projet",
            "chauffeur",
        )
        .order_by(
            "-date_debut",
            "-id",
        )
    )

    # --------------------------------------------------------
    # STATISTIQUES
    # --------------------------------------------------------

    total_km = sum(
        (
            affectation.kilometres_parcourus
            for affectation in affectations
        ),
        Decimal("0.00"),
    )

    total_carburant = sum(
        (
            affectation.carburant_estime
            for affectation in affectations
        ),
        Decimal("0.00"),
    )

    total_actifs = sum(
        1
        for affectation in affectations
        if affectation.acces_actif
    )

    total_affectations = affectations.count()

    # --------------------------------------------------------
    # AFFICHAGE
    # --------------------------------------------------------

    return render(
        request,
        "projet/vehicule/list.html",
        {
            "projet": projet,
            "affectations": affectations,

            "total_affectations": total_affectations,
            "total_km": total_km,
            "total_carburant": total_carburant,
            "total_actifs": total_actifs,

            "user": request.current_user,
        },
    )


# ============================================================
# CRÉER - CREATE
# ============================================================

@project_manager_required
def vehicule_projet_create(request,projet_id,):

    projet = get_object_or_404(Projet,pk=projet_id,)

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == "POST":

        form = VehiculeProjetForm(request.POST,projet=projet,)

        if form.is_valid():

            affectation = form.save(commit=False)

            # ------------------------------------------------
            # PROJET
            # ------------------------------------------------

            affectation.projet = projet

            # ------------------------------------------------
            # SAUVEGARDE
            # ------------------------------------------------

            affectation.save()

            messages.success(
                request,
                (
                    f"Le véhicule / engin "
                    f"« {affectation.vehicule} » "
                    f"a été affecté au projet "
                    f"« {projet.titre} »."
                ),
            )

            return redirect(
                "projet:vehicule_projet_list",
                projet_id=projet.pk,
            )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    else:

        form = VehiculeProjetForm(
            projet=projet,
        )

    # --------------------------------------------------------
    # FORMULAIRE
    # --------------------------------------------------------

    return render(
        request,
        "projet/vehicule/form.html",
        {
            "form": form,
            "projet": projet,

            "affectation": None,

            "titre_page": (
                "Affecter un véhicule / engin au projet"
            ),

            "user": request.current_user,
        },
    )


# ============================================================
# MODIFIER - UPDATE
# ============================================================

@project_manager_required
def vehicule_projet_update(request,projet_id,vehicule_projet_id,):

    projet = get_object_or_404(Projet,pk=projet_id,)

    # --------------------------------------------------------
    # RÉCUPÉRATION DE L'AFFECTATION
    # --------------------------------------------------------

    affectation = get_object_or_404(
        VehiculeProjet.objects.select_related(
            "projet",
            "chauffeur",
        ),
        pk=vehicule_projet_id,
        projet=projet,
    )

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == "POST":

        form = VehiculeProjetForm(
            request.POST,
            instance=affectation,
            projet=projet,
        )

        # ----------------------------------------------------
        # GARANTIR LE PROJET
        # ----------------------------------------------------

        form.instance.projet = projet

        if form.is_valid():

            affectation_modifiee = form.save(commit=False)

            # ------------------------------------------------
            # GARANTIR LE PROJET
            # ------------------------------------------------

            affectation_modifiee.projet = projet

            # ------------------------------------------------
            # SAUVEGARDE
            # ------------------------------------------------

            affectation_modifiee.save()

            messages.success(
                request,
                (
                    f"L'affectation du véhicule "
                    f"« {affectation_modifiee.vehicule} » "
                    f"a été modifiée avec succès."
                ),
            )

            return redirect(
                "projet:vehicule_projet_list",
                projet_id=projet.pk,
            )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    else:

        form = VehiculeProjetForm(
            instance=affectation,
            projet=projet,
        )

    # --------------------------------------------------------
    # FORMULAIRE
    # --------------------------------------------------------

    return render(
        request,
        "projet/vehicule/form.html",
        {
            "form": form,
            "projet": projet,

            "affectation": affectation,

            "titre_page": (
                "Modifier l'affectation du véhicule / engin"
            ),

            "user": request.current_user,
        },
    )


# ============================================================
# SUPPRIMER - DELETE
# ============================================================

@project_manager_required
def vehicule_projet_delete(request,projet_id,vehicule_projet_id,):

    projet = get_object_or_404(Projet,pk=projet_id,)

    # --------------------------------------------------------
    # RÉCUPÉRATION DE L'AFFECTATION
    # --------------------------------------------------------

    affectation = get_object_or_404(VehiculeProjet,pk=vehicule_projet_id,projet=projet,)

    # --------------------------------------------------------
    # SUPPRESSION UNIQUEMENT EN POST
    # --------------------------------------------------------

    if request.method == "POST":

        vehicule = affectation.vehicule

        try:

            affectation.delete()

            messages.success(
                request,
                (
                    f"L'affectation du véhicule / engin "
                    f"« {vehicule} » "
                    f"a été supprimée avec succès."
                ),
            )

        except ProtectedError:

            messages.error(
                request,
                (
                    "Impossible de supprimer cette affectation "
                    "car elle est utilisée par d'autres données."
                ),
            )

        return redirect(
            "projet:vehicule_projet_list",
            projet_id=projet.pk,
        )

    # --------------------------------------------------------
    # SI GET
    # --------------------------------------------------------

    messages.warning(
        request,
        "La suppression doit être confirmée par une requête POST.",
    )

    return redirect(
        "projet:vehicule_projet_list",
        projet_id=projet.pk,
    )

# ============================================================
# LISTE DES ENGINS AFFECTÉS AU PROJET
# ============================================================

@login_required_projet
def engin_list(request, projet_id):
    """
    Affiche la liste des engins affectés à un projet.
    """

    # ============================================================
    # UTILISATEUR CONNECTÉ
    # ============================================================

    current_user = request.current_user

    if not current_user:
        messages.error(
            request,
            "Utilisateur connecté introuvable.",
        )

        return redirect("users:login")

    # ============================================================
    # PROJET
    # ============================================================

    projet = get_object_or_404(
        Projet.objects.select_related("enregistre_par"),
        pk=projet_id,
    )

    # ============================================================
    # VÉRIFICATION DE L'ACCÈS AU PROJET
    # ============================================================

    if not user_has_project_access(
        current_user,
        projet,
    ):
        messages.error(
            request,
            "Votre accès à ce projet n'est pas actif.",
        )

        return redirect(
            "projet:projet_list"
        )

    # ============================================================
    # ÉQUIPE DU PROJET
    # ============================================================

    equipe = (
        projet.equipe
        .all()
        .select_related(
            "personnel",
            "personnel_execution",
            "personnel_execution__point_projet",
            "personnel_execution__materiau_projet",
        )
        .order_by(
            "fonction",
            "personnel__nom",
            "personnel__prenom",
        )
    )

    # ============================================================
    # FONCTION DE L'UTILISATEUR DANS LE PROJET
    # ============================================================

    fonction_projet = None

    personnel_connecte_id = getattr(
        current_user,
        "personnel_id",
        None,
    )

    if personnel_connecte_id:

        for membre in equipe:

            # ----------------------------------------------------
            # PERSONNEL PRINCIPAL
            # ----------------------------------------------------

            if (
                membre.personnel_id
                and membre.personnel_id == personnel_connecte_id
            ):
                if membre.acces_actif:
                    fonction_projet = membre.fonction
                    break

            # ----------------------------------------------------
            # PERSONNEL D'EXÉCUTION
            # ----------------------------------------------------

            if (
                membre.personnel_execution_id
                and membre.personnel_execution
            ):

                personnel_execution = (
                    membre.personnel_execution
                )

                if (
                    personnel_execution.personnel_id
                    and personnel_execution.personnel_id
                    == personnel_connecte_id
                ):

                    if membre.acces_actif:
                        fonction_projet = membre.fonction
                        break

    # ============================================================
    # ENGINS DU PROJET
    # ============================================================

    engins = (
        EnginProjet.objects
        .filter(
            projet=projet
        )
        .select_related(
            "conducteur",
            "projet",
        )
        .order_by(
            "-date_debut",
            "-id",
        )
    )

    # ============================================================
    # STATISTIQUES
    # ============================================================

    total_engins = engins.count()

    engins_actifs = [
        engin
        for engin in engins
        if engin.acces_actif
    ]

    nombre_actifs = len(
        engins_actifs
    )

    total_heures = sum(
        (
            engin.heures_travail
            for engin in engins
        ),
        Decimal("0.00"),
    )

    total_carburant = sum(
        (
            engin.carburant_estime
            for engin in engins
        ),
        Decimal("0.00"),
    )

    # ============================================================
    # PERMISSIONS
    # ============================================================

    peut_gerer = user_can_manage_projects(
        current_user
    )

    peut_rapport_engin = (
        fonction_projet
        in {
            "CHAUFFEUR",
            "CHEF_CHANTIER",
            "INGENIEUR",
        }
        or current_user.role
        in {
            "UserEntreprise",
            "Admin",
            "Superviseur",
        }
    )

    # ============================================================
    # CONTEXTE
    # ============================================================

    context = {
        "projet": projet,
        "user": current_user,
        "current_user": current_user,

        "fonction_projet": fonction_projet,

        "engins": engins,

        "total_engins": total_engins,
        "nombre_actifs": nombre_actifs,

        "total_heures": total_heures,
        "total_carburant": total_carburant,

        "peut_gerer": peut_gerer,
        "peut_rapport_engin": peut_rapport_engin,

        "aujourd_hui": timezone.localdate(),
    }

    # ============================================================
    # AFFICHAGE
    # ============================================================

    return render(
        request,
        "projet/engin/list.html",
        context,
    )


# ============================================================
# AJOUT ENGIN
# ============================================================

@login_required_projet
def engin_create(request,projet_id,):
            
        """
        Ajout d'un EnginProjet au projet.
        """

        projet = get_object_or_404(
            Projet,
            pk=projet_id,
        )

        # ============================================================
        # ACCÈS
        # ============================================================

        if not user_has_project_access(
            request.current_user,
            projet,
        ):
            messages.error(
                request,
                "Votre accès à ce projet n'est pas actif.",
            )

            return redirect(
                "projet:projet_list"
            )

        # ============================================================
        # PERMISSION
        # ============================================================

        if not user_can_manage_projects(
            request.current_user
        ):
            messages.error(
                request,
                "Vous n'avez pas l'autorisation "
                "d'ajouter un engin.",
            )

            return redirect(
                "projet:engin_list",
                projet_id=projet.id,
            )

        # ============================================================
        # FORMULAIRE
        # ============================================================

        if request.method == "POST":

            form = EnginProjetForm(
                request.POST,
                projet=projet,
            )

            if form.is_valid():

                engin = form.save(
                    commit=False
                )

                engin.projet = projet

                engin.save()

                messages.success(
                    request,
                    (
                        f"L'engin « {engin.engin} » "
                        "a été ajouté au projet."
                    ),
                )

                return redirect(
                    "projet:engin_list",
                    projet_id=projet.id,
                )

        else:

            form = EnginProjetForm(
                projet=projet,
            )

        context = {
            "projet": projet,
            "form": form,
            "titre": "Ajouter un engin",
            "mode": "create",
            "user": request.current_user,
            "object": None,
        }

        return render(
            request,
            "projet/engin/form.html",
            context,
        )

# ============================================================

# MODIFICATION ENGIN

# ============================================================

@login_required_projet
def engin_update(request,projet_id,pk,):
        """
        Modification d'un EnginProjet.
        """

        projet = get_object_or_404(
            Projet,
            pk=projet_id,
        )

        # ============================================================
        # ACCÈS
        # ============================================================

        if not user_has_project_access(
            request.current_user,
            projet,
        ):
            messages.error(
                request,
                "Votre accès à ce projet n'est pas actif.",
            )

            return redirect(
                "projet:projet_list"
            )

        # ============================================================
        # PERMISSION
        # ============================================================

        if not user_can_manage_projects(
            request.current_user
        ):
            messages.error(
                request,
                "Vous n'avez pas l'autorisation "
                "de modifier cet engin.",
            )

            return redirect(
                "projet:engin_list",
                projet_id=projet.id,
            )

        # ============================================================
        # ENGIN
        # ============================================================

        engin = get_object_or_404(
            EnginProjet.objects.select_related(
                "conducteur",
                "projet",
            ),
            pk=pk,
            projet=projet,
        )

        # ============================================================
        # FORMULAIRE
        # ============================================================

        if request.method == "POST":

            form = EnginProjetForm(
                request.POST,
                instance=engin,
                projet=projet,
            )

            if form.is_valid():

                engin = form.save()

                messages.success(
                    request,
                    (
                        f"L'engin « {engin.engin} » "
                        "a été modifié."
                    ),
                )

                return redirect(
                    "projet:engin_list",
                    projet_id=projet.id,
                )

        else:

            form = EnginProjetForm(
                instance=engin,
                projet=projet,
            )

        context = {
            "projet": projet,
            "engin": engin,
            "object": engin,
            "form": form,
            "titre": "Modifier l'engin",
            "mode": "update",
            "user": request.current_user,
        }

        return render(
            request,
            "projet/engin/form.html",
            context,
        )
        

# ============================================================

# SUPPRESSION ENGIN

# ============================================================

@login_required_projet
def engin_delete(request,projet_id,pk,):
        """
        Suppression d'un EnginProjet.
        """
        projet = get_object_or_404(Projet,pk=projet_id,)

        # ============================================================
        # ACCÈS
        # ============================================================

        if not user_has_project_access(
            request.current_user,
            projet,
        ):
            messages.error(
                request,
                "Votre accès à ce projet n'est pas actif.",
            )

            return redirect(
                "projet:projet_list"
            )

        # ============================================================
        # PERMISSION
        # ============================================================

        if not user_can_manage_projects(
            request.current_user
        ):
            messages.error(
                request,
                "Vous n'avez pas l'autorisation "
                "de supprimer cet engin.",
            )

            return redirect(
                "projet:engin_list",
                projet_id=projet.id,
            )

        # ============================================================
        # ENGIN
        # ============================================================

        engin = get_object_or_404(
            EnginProjet,
            pk=pk,
            projet=projet,
        )

        # ============================================================
        # CONFIRMATION
        # ============================================================

        if request.method == "POST":

            nom_engin = engin.engin

            engin.delete()

            messages.success(
                request,
                (
                    f"L'engin « {nom_engin} » "
                    "a été supprimé."
                ),
            )

            return redirect(
                "projet:engin_list",
                projet_id=projet.id,
            )

        context = {
            "projet": projet,
            "engin": engin,
            "user": request.current_user,
        }

        return render(
            request,
            "projet/engin_delete.html",
            context,
        )


# ============================================================
# MATÉRIAUX DU PROJET
# ============================================================
# ============================================================
# LISTE DES MATÉRIAUX DU PROJET
# ============================================================

@login_required_projet
def materiau_list(request, projet_id):

    # ========================================================
    # UTILISATEUR CONNECTÉ
    # ========================================================
    current_user = get_current_user(request)

    if not current_user:
        messages.error(
            request,
            "Utilisateur connecté introuvable."
        )
        return redirect("users:login")

    # ========================================================
    # PROJET
    # ========================================================
    projet = get_object_or_404(
        Projet,
        pk=projet_id
    )

    # ========================================================
    # VÉRIFICATION DE L'ACCÈS AU PROJET
    # ========================================================
    if not user_has_project_access(
        current_user,
        projet
    ):
        messages.error(
            request,
            "Votre accès à ce projet n'est pas actif."
        )

        return redirect(
            "projet:projet_list"
        )

    # ========================================================
    # MATÉRIAUX DU PROJET
    #
    # IMPORTANT :
    # `materiau` est maintenant un CharField.
    #
    # Donc :
    #     PAS de select_related("materiau")
    # ========================================================
    materiaux = (
        MateriauProjet.objects
        .filter(projet=projet)
        .select_related("projet")
        .order_by("materiau", "id")
    )

    # ========================================================
    # DROITS
    # ========================================================
    peut_gerer = user_can_manage_materiaux(
        current_user,
        projet
    )

    # ========================================================
    # STATISTIQUES
    # ========================================================
    total_materiaux = materiaux.count()

    # ========================================================
    # CONTEXTE
    # ========================================================
    context = {
        "projet": projet,
        "materiaux": materiaux,

        "total_materiaux": total_materiaux,

        "user": current_user,
        "current_user": current_user,

        "personnel": getattr(
            current_user,
            "personnel",
            None
        ),

        "peut_gerer": peut_gerer,

        "peut_ajouter_materiau": peut_gerer,
    }

    # ========================================================
    # AFFICHAGE
    # ========================================================
    return render(
        request,
        "projet/materiau/list.html",
        context
    )


# ============================================================
# AJOUTER UN MATÉRIAU AU PROJET
# ============================================================

@login_required_projet
def materiau_create(request, projet_id):

    # ========================================================
    # UTILISATEUR CONNECTÉ
    # ========================================================
    current_user = get_current_user(request)

    if not current_user:
        messages.error(
            request,
            "Utilisateur connecté introuvable."
        )
        return redirect("users:login")

    # ========================================================
    # PROJET
    # ========================================================
    projet = get_object_or_404(
        Projet,
        pk=projet_id
    )

    # ========================================================
    # VÉRIFICATION DE L'ACCÈS AU PROJET
    # ========================================================
    if not user_has_project_access(
        current_user,
        projet
    ):
        messages.error(
            request,
            "Votre accès à ce projet n'est pas actif."
        )

        return redirect(
            "projet:projet_list"
        )

    peut_gerer = user_can_manage_materiaux(
        current_user,
        projet
    )

    if not peut_gerer:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'ajouter "
            "un matériau à ce projet."
        )

        return redirect(
            "projet:materiau_list",
            projet_id=projet.id
        )

    # ========================================================
    # TRAITEMENT DU FORMULAIRE
    # ========================================================
    if request.method == "POST":

        form = MateriauProjetForm(
            request.POST,
            projet=projet
        )

        if form.is_valid():

            # ----------------------------------------------
            # Création sécurisée
            # ----------------------------------------------
            materiau_projet = form.save(
                commit=False
            )

            # Le projet vient toujours de l'URL.
            # Il ne peut donc pas être modifié par le POST.
            materiau_projet.projet = projet

            materiau_projet.save()

            messages.success(
                request,
                f"Le matériau « {materiau_projet.materiau} » "
                "a été ajouté au projet."
            )

            return redirect(
                "projet:materiau_list",
                projet_id=projet.id
            )

    else:

        form = MateriauProjetForm(
            projet=projet
        )

    # ========================================================
    # CONTEXTE
    # ========================================================
    context = {
        "projet": projet,
        "form": form,

        "titre": "Ajouter un matériau",
        "mode": "create",

        "user": current_user,
        "current_user": current_user,

        "personnel": getattr(
            current_user,
            "personnel",
            None
        ),

        "peut_gerer": peut_gerer,
    }

    # ========================================================
    # AFFICHAGE
    # ========================================================
    return render(
        request,
        "projet/materiau/form.html",
        context
    )


# ============================================================
# MODIFIER UN MATÉRIAU
# ============================================================

@login_required_projet
def materiau_update(
    request,
    projet_id,
    pk,
):

    # ========================================================
    # UTILISATEUR CONNECTÉ
    # ========================================================

    current_user = get_current_user(request)

    if not current_user:

        messages.error(
            request,
            "Utilisateur connecté introuvable.",
        )

        return redirect(
            "users:login"
        )

    # ========================================================
    # PROJET
    # ========================================================

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    # ========================================================
    # VÉRIFICATION ACCÈS PROJET
    # ========================================================

    if not user_has_project_access(
        current_user,
        projet,
    ):

        messages.error(
            request,
            "Votre accès à ce projet n'est pas actif.",
        )

        return redirect(
            "projet:projet_list"
        )

    # ========================================================
    # PERMISSION MATÉRIAU
    # ========================================================

    peut_gerer = user_can_manage_materiaux(
        current_user,
        projet,
    )

    if not peut_gerer:

        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier "
            "un matériau de ce projet.",
        )

        return redirect(
            "projet:materiau_list",
            projet_id=projet.id,
        )

    # ========================================================
    # MATÉRIAU DU PROJET
    #
    # IMPORTANT :
    # `materiau` est un CharField.
    #
    # Donc on ne fait PAS :
    # select_related("materiau")
    # ========================================================

    materiau_projet = get_object_or_404(
        MateriauProjet.objects.select_related(
            "projet",
        ),
        pk=pk,
        projet=projet,
    )

    # ========================================================
    # TRAITEMENT POST
    # ========================================================

    if request.method == "POST":

        form = MateriauProjetForm(
            request.POST,
            instance=materiau_projet,
            projet=projet,
        )

        if form.is_valid():

            materiau_projet = form.save(
                commit=False
            )

            # Sécurité :
            # le projet reste celui de l'URL.
            materiau_projet.projet = projet

            materiau_projet.save()

            messages.success(
                request,
                "Le matériau a été modifié avec succès.",
            )

            return redirect(
                "projet:materiau_list",
                projet_id=projet.id,
            )

    # ========================================================
    # AFFICHAGE DU FORMULAIRE
    # ========================================================

    else:

        form = MateriauProjetForm(
            instance=materiau_projet,
            projet=projet,
        )

    # ========================================================
    # CONTEXTE
    # ========================================================

    context = {
        "projet": projet,
        "materiau_projet": materiau_projet,
        "form": form,

        "titre": "Modifier le matériau",
        "mode": "update",

        "user": current_user,
        "current_user": current_user,

        "personnel": getattr(
            current_user,
            "personnel",
            None,
        ),

        "peut_gerer": peut_gerer,
    }

    # ========================================================
    # TEMPLATE
    # ========================================================

    return render(
        request,
        "projet/materiau/form.html",
        context,
    )


# ============================================================
# SUPPRIMER UN MATÉRIAU
# ============================================================

@login_required_projet
def materiau_delete(
    request,
    projet_id,
    pk,
):

    # ========================================================
    # UTILISATEUR CONNECTÉ
    # ========================================================

    current_user = get_current_user(request)

    if not current_user:

        messages.error(
            request,
            "Utilisateur connecté introuvable.",
        )

        return redirect(
            "users:login"
        )

    # ========================================================
    # PROJET
    # ========================================================

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    # ========================================================
    # VÉRIFICATION ACCÈS PROJET
    # ========================================================

    if not user_has_project_access(
        current_user,
        projet,
    ):

        messages.error(
            request,
            "Votre accès à ce projet n'est pas actif.",
        )

        return redirect(
            "projet:projet_list"
        )

    # ========================================================
    # PERMISSION MATÉRIAU
    # ========================================================

    peut_gerer = user_can_manage_materiaux(
        current_user,
        projet,
    )

    if not peut_gerer:

        messages.error(
            request,
            "Vous n'avez pas l'autorisation de supprimer "
            "un matériau de ce projet.",
        )

        return redirect(
            "projet:materiau_list",
            projet_id=projet.id,
        )

    # ========================================================
    # MATÉRIAU DU PROJET
    #
    # `materiau` est un CharField.
    # Aucun select_related("materiau").
    # ========================================================

    materiau_projet = get_object_or_404(
        MateriauProjet.objects.select_related(
            "projet",
        ),
        pk=pk,
        projet=projet,
    )

    # ========================================================
    # SUPPRESSION
    # ========================================================

    if request.method == "POST":

        nom_materiau = str(
            materiau_projet.materiau
        )

        materiau_projet.delete()

        messages.success(
            request,
            f"Le matériau « {nom_materiau} » "
            "a été supprimé du projet.",
        )

        return redirect(
            "projet:materiau_list",
            projet_id=projet.id,
        )

    # ========================================================
    # CONFIRMATION DE SUPPRESSION
    # ========================================================

    context = {
        "projet": projet,
        "materiau_projet": materiau_projet,

        "user": current_user,
        "current_user": current_user,

        "personnel": getattr(
            current_user,
            "personnel",
            None,
        ),

        "peut_gerer": peut_gerer,
    }

    return render(
        request,
        "projet/materiau/delete.html",
        context,
    )


# ============================================================
# CRUD MINIER PROJET
# ============================================================


@login_required_projet
def minier_list(
    request,
    projet_id,
):
    """
    Liste les miniers affectés au projet.
    """

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    # --------------------------------------------------------
    # CONTRÔLE D'ACCÈS AU PROJET
    # --------------------------------------------------------

    if not user_has_project_access(
        request.current_user,
        projet,
    ):
        messages.error(
            request,
            "Votre accès à ce projet n'est pas actif.",
        )

        return redirect(
            "projet:projet_list"
        )

    # --------------------------------------------------------
    # MINERS
    # --------------------------------------------------------

    miniers = (
        PersonnelExecutionProjet.objects
        .filter(
            projet=projet,
            type_class="MINIER",
        )
        .select_related(
            "materiau_projet",
            # "materiau_projet__materiau",
            "enregistre_par",
        )
        .order_by(
            "nom",
            "id",
        )
    )

    # --------------------------------------------------------
    # STATISTIQUES
    # --------------------------------------------------------

    total_miniers = miniers.count()

    aujourd_hui = timezone.localdate()

    nombre_actifs = sum(
        1
        for minier in miniers
        if minier.acces_actif
    )

    # --------------------------------------------------------
    # TOTAL PRODUCTION
    #
    # Pour un MINIER :
    # quantité × prix unitaire
    # --------------------------------------------------------

    total_production = sum(
        (
            minier.montant_total_production
            for minier in miniers
        ),
        Decimal("0.00"),
    )

    context = {
        "projet": projet,

        "miniers": miniers,

        "total_miniers": total_miniers,

        "nombre_actifs": nombre_actifs,

        "total_production": total_production,

        "peut_gerer": (
            user_can_manage_projects(
                request.current_user
            )
        ),

        "user": request.current_user,

        "aujourd_hui": aujourd_hui,
    }

    return render(
        request,
        "projet/minier/list.html",
        context,
    )

 
@login_required_projet
def minier_create(request, projet_id):
    """
    Ajouter un minier au projet.

    Autorisés à ajouter :
        - Admin
        - Superviseur
        - UserEntreprise
        - Ingénieur du projet
        - Chef de chantier du projet
        - Chef d'équipe du projet

    L'utilisateur connecté devient automatiquement
    l'enregistreur du minier.
    """

    current_user = request.current_user

    # ============================================================
    # PROJET
    # ============================================================

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    # ============================================================
    # VÉRIFICATION ACCÈS AU PROJET
    # ============================================================

    if not user_has_project_access(
        current_user,
        projet,
    ):
        messages.error(
            request,
            "Votre accès à ce projet n'est pas actif.",
        )
        return redirect(
            "projet:projet_list"
        )

    # ============================================================
    # VÉRIFICATION DROIT D'AJOUT D'UN MINIER
    # ============================================================

    if not user_can_manage_materiaux(
        current_user,
        projet,
    ):
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'ajouter "
            "un minier sur ce projet.",
        )
        return redirect(
            "projet:minier_list",
            projet_id=projet.id,
        )

    # ============================================================
    # PERSONNEL CONNECTÉ
    # ============================================================

    personnel_connecte = getattr(
        current_user,
        "personnel",
        None,
    )

    if not personnel_connecte:
        messages.error(
            request,
            "Aucun personnel n'est associé à votre "
            "compte utilisateur.",
        )
        return redirect(
            "projet:minier_list",
            projet_id=projet.id,
        )

    # ============================================================
    # TRAITEMENT POST
    # ============================================================

    if request.method == "POST":

        form = MinierProjetForm(
            request.POST,
            request.FILES,
            projet=projet,
        )

        # --------------------------------------------------------
        # VALIDATION DU FORMULAIRE
        # --------------------------------------------------------

        if form.is_valid():

            # ----------------------------------------------------
            # CRÉATION DE L'INSTANCE
            # ----------------------------------------------------

            minier = form.save(
                commit=False
            )

            # ----------------------------------------------------
            # DONNÉES AUTOMATIQUES DU MINIER
            # ----------------------------------------------------

            # Projet
            minier.projet = projet

            # Un minier est une personne externe.
            # Il ne doit donc pas être lié à Personnel.
            minier.personnel = None

            # Type d'exécution
            minier.type_class = "MINIER"

            # Un minier n'est pas directement affecté
            # à un PointProjet.
            minier.point_projet = None

            # Pour un minier, le montant est calculé
            # automatiquement à partir de :
            #
            # quantité × prix unitaire
            #
            # Le champ montant reste donc à zéro.
            minier.montant = Decimal("0.00")

            # ----------------------------------------------------
            # ENREGISTREUR
            # ----------------------------------------------------

            # IMPORTANT :
            # enregistre_par attend un Personnel,
            # pas un AppUser.
            minier.enregistre_par = personnel_connecte

            # ----------------------------------------------------
            # SAUVEGARDE
            # ----------------------------------------------------

            minier.save()

            # ----------------------------------------------------
            # MESSAGE
            # ----------------------------------------------------

            messages.success(
                request,
                f"Le minier « {minier.nom} » a été ajouté "
                f"avec succès.",
            )

            # ----------------------------------------------------
            # RETOUR À LA LISTE
            # ----------------------------------------------------

            return redirect(
                "projet:minier_list",
                projet_id=projet.id,
            )

    # ============================================================
    # GET
    # ============================================================

    else:

        form = MinierProjetForm(
            projet=projet,
        )

    # ============================================================
    # CONTEXTE
    # ============================================================

    context = {
        "form": form,
        "projet": projet,
        "current_user": current_user,
        "user": current_user,
        "personnel": personnel_connecte,

        # L'utilisateur a déjà été autorisé
        # par user_can_manage_materiaux().
        "peut_gerer": True,

        "mode": "create",
        "titre": "Ajouter un minier",
    }

    # ============================================================
    # AFFICHAGE
    # ============================================================

    return render(
        request,
        "projet/minier/form.html",
        context,
    )

 
# ============================================================
# MODIFICATION MINIER
# ============================================================

@login_required_projet
def minier_update(
    request,
    projet_id,
    pk,
):
    """
    Modifie un minier existant.

    RÈGLE IMPORTANTE :
    Seul l'utilisateur qui a enregistré le minier
    peut le modifier.

    Les autres utilisateurs, même s'ils sont :
        - Admin
        - Superviseur
        - UserEntreprise
        - Ingénieur
        - Chef de chantier
        - Chef d'équipe

    ne peuvent pas modifier cet enregistrement.
    """

    current_user = request.current_user

    # --------------------------------------------------------
    # PROJET
    # --------------------------------------------------------

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    # --------------------------------------------------------
    # ACCÈS AU PROJET
    # --------------------------------------------------------

    if not user_has_project_access(
        current_user,
        projet,
    ):
        messages.error(
            request,
            "Votre accès à ce projet n'est pas actif.",
        )

        return redirect(
            "projet:projet_list"
        )

    # --------------------------------------------------------
    # PERSONNEL CONNECTÉ
    # --------------------------------------------------------

    personnel_connecte = getattr(
        current_user,
        "personnel",
        None,
    )

    if not personnel_connecte:
        messages.error(
            request,
            "Aucun personnel n'est associé à votre compte.",
        )

        return redirect(
            "projet:minier_list",
            projet_id=projet.id,
        )

    # --------------------------------------------------------
    # MINIER
    # --------------------------------------------------------

    minier = get_object_or_404(
        PersonnelExecutionProjet.objects
        .select_related(
            "projet",
            "materiau_projet",
            "enregistre_par",
        ),
        pk=pk,
        projet=projet,
        type_class="MINIER",
    )

    # --------------------------------------------------------
    # CONTRÔLE DE L'ENREGISTREUR
    # --------------------------------------------------------
    #
    # Seul celui qui a créé l'enregistrement peut modifier.
    # --------------------------------------------------------

    if (
        not minier.enregistre_par_id
        or minier.enregistre_par_id != personnel_connecte.pk
    ):
        messages.error(
            request,
            "Vous ne pouvez pas modifier ce minier. "
            "Seul l'utilisateur qui l'a enregistré "
            "peut le modifier.",
        )

        return redirect(
            "projet:minier_list",
            projet_id=projet.id,
        )

    # --------------------------------------------------------
    # FORMULAIRE
    # --------------------------------------------------------

    if request.method == "POST":

        form = MinierProjetForm(
            request.POST,
            request.FILES,
            instance=minier,
            projet=projet,
        )

        if form.is_valid():

            minier = form.save(
                commit=False
            )

            # ------------------------------------------------
            # VALEURS IMPOSÉES
            # ------------------------------------------------

            minier.projet = projet

            minier.type_class = "MINIER"

            minier.personnel = None

            minier.point_projet = None

            # ------------------------------------------------
            # IMPORTANT
            # ------------------------------------------------
            #
            # On conserve l'enregistreur original.
            #
            # Il ne faut PAS remplacer enregistre_par par
            # l'utilisateur qui modifie.
            # ------------------------------------------------

            minier.enregistre_par = personnel_connecte

            # ------------------------------------------------
            # SAUVEGARDE
            # ------------------------------------------------

            minier.save()

            messages.success(
                request,
                (
                    f"Le minier « {minier.nom} » "
                    "a été modifié avec succès."
                ),
            )

            return redirect(
                "projet:minier_list",
                projet_id=projet.id,
            )

    else:

        form = MinierProjetForm(
            instance=minier,
            projet=projet,
        )

    # --------------------------------------------------------
    # CONTEXTE
    # --------------------------------------------------------

    context = {
        "projet": projet,
        "minier": minier,
        "form": form,
        "titre": "Modifier le minier",
        "mode": "update",
        "user": current_user,
        "current_user": current_user,
        "personnel": personnel_connecte,
        "peut_gerer": True,
    }

    return render(
        request,
        "projet/minier/form.html",
        context,
    )


# ============================================================
# SUPPRESSION MINIER
# ============================================================

@login_required_projet
def minier_delete(
    request,
    projet_id,
    pk,
):
    """
    Supprime un minier du projet.

    RÈGLE IMPORTANTE :
    Seul l'utilisateur qui a enregistré le minier
    peut le supprimer.
    """

    current_user = request.current_user

    # --------------------------------------------------------
    # PROJET
    # --------------------------------------------------------

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    # --------------------------------------------------------
    # ACCÈS AU PROJET
    # --------------------------------------------------------

    if not user_has_project_access(
        current_user,
        projet,
    ):
        messages.error(
            request,
            "Votre accès à ce projet n'est pas actif.",
        )

        return redirect(
            "projet:projet_list"
        )

    # --------------------------------------------------------
    # PERSONNEL CONNECTÉ
    # --------------------------------------------------------

    personnel_connecte = getattr(
        current_user,
        "personnel",
        None,
    )

    if not personnel_connecte:
        messages.error(
            request,
            "Aucun personnel n'est associé à votre compte.",
        )

        return redirect(
            "projet:minier_list",
            projet_id=projet.id,
        )

    # --------------------------------------------------------
    # MINIER
    # --------------------------------------------------------

    minier = get_object_or_404(
        PersonnelExecutionProjet.objects
        .select_related(
            "projet",
            "materiau_projet",
            "enregistre_par",
        ),
        pk=pk,
        projet=projet,
        type_class="MINIER",
    )

    # --------------------------------------------------------
    # CONTRÔLE DE L'ENREGISTREUR
    # --------------------------------------------------------
    #
    # Seul celui qui a créé le minier peut le supprimer.
    # --------------------------------------------------------

    if (
        not minier.enregistre_par_id
        or minier.enregistre_par_id != personnel_connecte.pk
    ):
        messages.error(
            request,
            "Vous ne pouvez pas supprimer ce minier. "
            "Seul l'utilisateur qui l'a enregistré "
            "peut le supprimer.",
        )

        return redirect(
            "projet:minier_list",
            projet_id=projet.id,
        )

    # --------------------------------------------------------
    # SUPPRESSION
    # --------------------------------------------------------

    if request.method == "POST":

        nom_minier = minier.nom

        minier.delete()

        messages.success(
            request,
            (
                f"Le minier « {nom_minier} » "
                "a été supprimé avec succès."
            ),
        )

        return redirect(
            "projet:minier_list",
            projet_id=projet.id,
        )

    # --------------------------------------------------------
    # PAGE DE CONFIRMATION
    # --------------------------------------------------------

    context = {
        "projet": projet,
        "minier": minier,
        "user": current_user,
        "current_user": current_user,
        "personnel": personnel_connecte,
    }

    return render(
        request,
        "projet/minier_delete.html",
        context,
    )

# ============================================================
# RAPPORT VEHICULE - LISTE
# ============================================================

@project_access_required
def rapport_vehicule_list(
    request,
    projet_id,
):

    rapports = (
        RapportVehicule.objects
        .filter(
            projet=request.projet
        )
        .select_related(
            "vehicule",
            "chauffeur",
        )
    )

    return render(
        request,
        "projet/vehicule/rapport_list.html",
        {
            "projet": request.projet,
            "rapports": rapports,
            "user": request.current_user,
        },
    )


# ============================================================
# RAPPORT VEHICULE - CREER
# ============================================================

@project_access_required
def rapport_vehicule_create(
    request,
    projet_id,
):

    projet = request.projet

    if request.method == "POST":

        form = RapportVehiculeForm(
            request.POST,
            request.FILES,
            projet=projet,
        )

        if form.is_valid():

            vehicule = form.cleaned_data.get(
                "vehicule"
            )

            chauffeur = form.cleaned_data.get(
                "chauffeur"
            )

            if vehicule is None:

                form.add_error(
                    "vehicule",
                    "Veuillez sélectionner un véhicule.",
                )

            if chauffeur is None:

                form.add_error(
                    "chauffeur",
                    "Veuillez sélectionner un chauffeur.",
                )

            if not form.errors:

                rapport = form.save(
                    commit=False
                )

                rapport.projet_id = projet.pk
                rapport.vehicule_id = vehicule.pk
                rapport.chauffeur_id = chauffeur.pk

                rapport.save()

                messages.success(
                    request,
                    "Rapport véhicule enregistré avec succès.",
                )

                return redirect(
                    "projet:rapport_vehicule_list",
                    projet_id=projet.pk,
                )

    else:

        form = RapportVehiculeForm(
            projet=projet,
        )

    return render(
        request,
        "projet/vehicule/rapport_form.html",
        {
            "form": form,
            "projet": projet,
            "user": request.current_user,
        },
    )


# ============================================================
# SELECTION PROJET POUR EQUIPE
# ============================================================

@login_required_projet
def equipe_projet_selection(request):

    projets = (
        Projet.objects
        .all()
        .order_by(
            "-date_debut",
            "-id",
        )
    )

    if not user_can_manage_projects(
        request.current_user
    ):

        messages.error(
            request,
            "Vous n'avez pas l'autorisation de gérer les équipes.",
        )

        return redirect(
            "projet:projet_list"
        )

    return render(
        request,
        "projet/equipage/selection.html",
        {
            "projets": projets,
            "user": request.current_user,
        },
    )


# ============================================================
# ACTIVITES TRANSPORT DU PROJET
# ============================================================

@project_manager_required
def activite_transport_projet_list(
    request,
    projet_id,
):

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    activites = (
        ActiviteTransportProjet.objects
        .filter(
            projet=projet
        )
        .select_related(
            "projet",
            "chauffeur",
            "enregistre_par",
        )
        .order_by(
            "-date_transport",
            "-id",
        )
    )

    total_km = sum(
        (
            activite.kilometres_parcourus
            for activite in activites
        ),
        Decimal("0.00"),
    )

    total_carburant = sum(
        (
            activite.carburant_estime
            for activite in activites
        ),
        Decimal("0.00"),
    )

    total_activites = activites.count()

    return render(
        request,
        "projet/activite_transport_projet_list.html",
        {
            "projet": projet,
            "activites": activites,
            "total_km": total_km,
            "total_carburant": total_carburant,
            "total_activites": total_activites,
            "user": request.current_user,
        },
    )


# ============================================================
# ACTIVITE TRANSPORT - CREER
# ============================================================

@project_manager_required
def activite_transport_projet_create(
    request,
    projet_id,
):

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    if request.method == "POST":

        form = ActiviteTransportProjetForm(
            request.POST,
            projet=projet,
        )

        if form.is_valid():

            activite = form.save(
                commit=False
            )

            activite.projet = projet
            activite.enregistre_par = (
                request.current_user
            )

            activite.save()

            messages.success(
                request,
                (
                    "L'activité de transport "
                    "a été enregistrée avec succès."
                ),
            )

            return redirect(
                "projet:activite_transport_projet_list",
                projet_id=projet.pk,
            )

    else:

        form = ActiviteTransportProjetForm(
            projet=projet,
        )

    return render(
        request,
        "projet/activite_transport_projet_form.html",
        {
            "form": form,
            "projet": projet,
            "titre_page": "Nouvelle activité de transport",
            "mode": "create",
            "user": request.current_user,
        },
    )


# ============================================================
# ACTIVITE TRANSPORT - MODIFIER
# ============================================================

@project_manager_required
def activite_transport_projet_update(
    request,
    projet_id,
    activite_id,
):

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    activite = get_object_or_404(
        ActiviteTransportProjet.objects.select_related(
            "projet",
            "chauffeur",
            "enregistre_par",
        ),
        pk=activite_id,
        projet=projet,
    )

    user = request.current_user

    if activite.enregistre_par_id != user.pk:

        messages.error(
            request,
            (
                "Vous n'êtes pas autorisé à modifier "
                "cette activité."
            ),
        )

        return redirect(
            "projet:activite_transport_projet_list",
            projet_id=projet.pk,
        )

    if request.method == "POST":

        form = ActiviteTransportProjetForm(
            request.POST,
            instance=activite,
            projet=projet,
        )

        if form.is_valid():

            activite_modifiee = form.save(
                commit=False
            )

            activite_modifiee.projet = projet
            activite_modifiee.enregistre_par_id = (
                activite.enregistre_par_id
            )

            activite_modifiee.save()

            messages.success(
                request,
                (
                    "L'activité de transport "
                    "a été modifiée avec succès."
                ),
            )

            return redirect(
                "projet:activite_transport_projet_list",
                projet_id=projet.pk,
            )

    else:

        form = ActiviteTransportProjetForm(
            instance=activite,
            projet=projet,
        )

    return render(
        request,
        "projet/activite_transport_projet_form.html",
        {
            "form": form,
            "projet": projet,
            "activite": activite,
            "titre_page": (
                "Modifier l'activité de transport"
            ),
            "mode": "update",
            "user": request.current_user,
        },
    )


# ============================================================
# ACTIVITE TRANSPORT - SUPPRIMER
# ============================================================

@project_manager_required
def activite_transport_projet_delete(request,projet_id,activite_id,):

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    activite = get_object_or_404(
        ActiviteTransportProjet,
        pk=activite_id,
        projet=projet,
    )

    user = request.current_user

    if activite.enregistre_par_id != user.pk:

        messages.error(
            request,
            (
                "Vous n'êtes pas autorisé à supprimer "
                "cette activité."
            ),
        )

        return redirect(
            "projet:activite_transport_projet_list",
            projet_id=projet.pk,
        )

    if request.method == "POST":

        try:

            activite.delete()

            messages.success(
                request,
                (
                    "L'activité de transport "
                    "a été supprimée avec succès."
                ),
            )

        except ProtectedError:

            messages.error(
                request,
                (
                    "Impossible de supprimer cette activité "
                    "car elle est utilisée par d'autres données."
                ),
            )

        return redirect(
            "projet:activite_transport_projet_list",
            projet_id=projet.pk,
        )

    return render(
        request,
        "projet/activite_transport_projet_confirm_delete.html",
        {
            "projet": projet,
            "activite": activite,
            "user": request.current_user,
        },
    )



# ============================================================
# OUTILS - MOUVEMENT VÉHICULE / ENGIN
# ============================================================

def _mouvement_est_createur(mouvement, user):
    """Vérifie si l'utilisateur connecté est le créateur."""
    return (
        user is not None
        and mouvement.enregistre_par_id == getattr(user, "pk", None)
    )


def _mouvement_peut_gerer(mouvement, user):
    """Créateur ou administrateur."""
    if _mouvement_est_createur(mouvement, user):
        return True

    role = getattr(user, "role", "") if user else ""
    return role in ("Admin", "SuperAdmin")


# ============================================================
# MOUVEMENTS - LISTE ET BILAN DU PROJET
# ============================================================
def mouvement_vehicule_projet_list(request, projet_id):
    projet = get_object_or_404(Projet, pk=projet_id)

    vehicules_projet = VehiculeProjet.objects.filter(
        projet=projet
    ).order_by("vehicule")

    mouvements_qs = MouvementVehiculeProjet.objects.filter(
        vehicule_projet__projet=projet
    ).select_related(
        "vehicule_projet",
        "point_depart",
        "point_arrivee",
        "enregistre_par",
    ).order_by("-date_mouvement", "-id")

    # Filtre sélectionné
    vehicule_filtre = request.GET.get("vehicule", "").strip()

    if vehicule_filtre.isdigit():
        mouvements_qs = mouvements_qs.filter(
            vehicule_projet_id=int(vehicule_filtre)
        )
    else:
        vehicule_filtre = ""

    mouvements = list(mouvements_qs)

    # Statistiques correspondant aux mouvements affichés
    total_km = sum(
        (
            m.kilometres_parcourus
            for m in mouvements
            if m.type_vehicule != "ENGIN"
        ),
        Decimal("0.00"),
    )

    total_heures_moteur = sum(
        (
            m.heures_travail
            for m in mouvements
            if m.type_vehicule == "ENGIN"
        ),
        Decimal("0.00"),
    )

    total_carburant = sum(
        (m.carburant_litre for m in mouvements),
        Decimal("0.00"),
    )

    total_duree_minutes = sum(
        (m.duree_minutes for m in mouvements),
        0,
    )

    context = {
        "projet": projet,
        "vehicules_projet": vehicules_projet,
        "vehicule_filtre": vehicule_filtre,
        "mouvements": mouvements,
        "total_km": total_km,
        "total_heures_moteur": total_heures_moteur,
        "total_carburant": total_carburant,
        "total_duree_minutes": total_duree_minutes,
    }

    return render(
        request,
        "projet/mouvement_vehicule_projet_list.html",
        context,
    )


# ============================================================
# MOUVEMENTS - DÉTAIL
# ============================================================

@project_access_required
def mouvement_vehicule_projet_detail(
    request,
    projet_id,
    mouvement_id,
):
    mouvement = get_object_or_404(
        MouvementVehiculeProjet.objects.select_related(
            "vehicule_projet",
            "vehicule_projet__projet",
            "point_depart",
            "point_arrivee",
            "enregistre_par",
        ),
        pk=mouvement_id,
        vehicule_projet__projet=request.projet,
    )

    return render(
        request,
        "projet/mouvement_vehicule_projet_detail.html",
        {
            "projet": request.projet,
            "mouvement": mouvement,
            "user": request.current_user,
            "peut_modifier": _mouvement_peut_gerer(
                mouvement,
                request.current_user,
            ),
        },
    )


# ============================================================
# MOUVEMENTS - CRÉER
# ============================================================

@project_access_required
def mouvement_vehicule_projet_create(request, projet_id):
    projet = request.projet
    user = request.current_user

    if request.method == "POST":
        form = MouvementVehiculeProjetForm(
            request.POST,
            projet=projet,
        )

        if form.is_valid():
            mouvement = form.save(commit=False)

            # Sécurité : l'affectation doit appartenir au projet.
            if mouvement.vehicule_projet.projet_id != projet.pk:
                raise PermissionDenied(
                    "Ce véhicule n'appartient pas à ce projet."
                )

            mouvement.enregistre_par = user
            mouvement.save()

            messages.success(
                request,
                "Le mouvement a été enregistré avec succès.",
            )

            return redirect(
                "projet:mouvement_vehicule_projet_list",
                projet_id=projet.pk,
            )
    else:
        form = MouvementVehiculeProjetForm(projet=projet)

    return render(
        request,
        "projet/mouvement_vehicule_projet_form.html",
        {
            "form": form,
            "projet": projet,
            "mouvement": None,
            "titre_page": "Nouveau rapport d'activité",
            "user": user,
        },
    )


# ============================================================
# MOUVEMENTS - MODIFIER
# ============================================================

@project_access_required
def mouvement_vehicule_projet_update(
    request,
    projet_id,
    mouvement_id,
):
    projet = request.projet
    user = request.current_user

    mouvement = get_object_or_404(
        MouvementVehiculeProjet,
        pk=mouvement_id,
        vehicule_projet__projet=projet,
    )

    if not _mouvement_peut_gerer(mouvement, user):
        messages.error(
            request,
            "Vous ne pouvez modifier que vos propres mouvements.",
        )
        return redirect(
            "projet:mouvement_vehicule_projet_list",
            projet_id=projet.pk,
        )

    if request.method == "POST":
        form = MouvementVehiculeProjetForm(
            request.POST,
            instance=mouvement,
            projet=projet,
        )

        if form.is_valid():
            mouvement_modifie = form.save(commit=False)

            if mouvement_modifie.vehicule_projet.projet_id != projet.pk:
                raise PermissionDenied(
                    "Ce véhicule n'appartient pas à ce projet."
                )

            # Ne pas remplacer le créateur lors d'une modification.
            mouvement_modifie.enregistre_par = mouvement.enregistre_par
            mouvement_modifie.save()

            messages.success(
                request,
                "Le mouvement a été modifié avec succès.",
            )

            return redirect(
                "projet:mouvement_vehicule_projet_list",
                projet_id=projet.pk,
            )
    else:
        form = MouvementVehiculeProjetForm(
            instance=mouvement,
            projet=projet,
        )

    return render(
        request,
        "projet/mouvement_vehicule_projet_form.html",
        {
            "form": form,
            "projet": projet,
            "mouvement": mouvement,
            "titre_page": "Modifier le rapport d'activité",
            "user": user,
        },
    )


# ============================================================
# MOUVEMENTS - SUPPRIMER
# ============================================================

@project_access_required
def mouvement_vehicule_projet_delete(
    request,
    projet_id,
    mouvement_id,
):
    projet = request.projet
    user = request.current_user

    mouvement = get_object_or_404(
        MouvementVehiculeProjet,
        pk=mouvement_id,
        vehicule_projet__projet=projet,
    )

    if not _mouvement_peut_gerer(mouvement, user):
        messages.error(
            request,
            "Vous ne pouvez supprimer que vos propres mouvements.",
        )
        return redirect(
            "projet:mouvement_vehicule_projet_list",
            projet_id=projet.pk,
        )

    try:
        mouvement.delete()

        messages.success(
            request,
            "Le mouvement a été supprimé avec succès.",
        )
    except Exception:
        messages.error(
            request,
            "Impossible de supprimer ce mouvement. "
            "Vérifiez s'il est utilisé par d'autres données.",
        )

    return redirect(
        "projet:mouvement_vehicule_projet_list",
        projet_id=projet.pk,
    )