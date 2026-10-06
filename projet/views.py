from functools import wraps
from decimal import Decimal

from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db.models import ProtectedError, Sum
from django.shortcuts import get_object_or_404, redirect, render

from users.models import AppUser
from personnel.models import Personnel
from materiaux.models import Materiaux, Vehicule

from .forms import (
    ProjetForm,
    EquipeProjetForm,
    ChefEquipeProjetForm,
    PointProjetForm,
    RapportProjetForm,
    RapportTravailForm,
    RapportMateriauForm,
    VehiculeProjetForm,
    RapportVehiculeForm,
    ActiviteTransportProjetForm,
)

from .models import (
    Projet,
    EquipeProjet,
    PointProjet,
    RapportProjet,
    RapportTravail,
    RapportMateriau,
    VehiculeProjet,
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
# UTILISATEUR CONNECTÉ
# IMPORTANT :
# Cette fonction doit être définie AVANT les décorateurs.
# ============================================================

def get_current_user(request):
    user_id = request.session.get("user_id")

    if not user_id:
        return None

    return (
        AppUser.objects
        .select_related("personnel")
        .filter(pk=user_id)
        .first()
    )


# ============================================================
# AUTHENTIFICATION DU PROJET
# ============================================================

def login_required_projet(view_func):
    """
    Vérifie qu'un utilisateur est connecté à l'application
    avec le système de session personnalisé.
    """

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        user = get_current_user(request)

        if not user:
            return redirect("users:login")

        request.current_user = user

        return view_func(request, *args, **kwargs)

    return wrapper


# ============================================================
# DROITS DE GESTION DES PROJETS
# ============================================================

def user_can_manage_projects(user):
    """
    Utilisateurs autorisés à gérer les projets.
    """

    if not user:
        return False

    return user.role in {
        "Admin",
        "Superviseur",
        "UserEntreprise",
    }


def project_manager_required(view_func):
    """
    Décorateur réservé aux utilisateurs pouvant gérer
    les projets.
    """

    @wraps(view_func)
    @login_required_projet
    def wrapper(request, *args, **kwargs):

        if not user_can_manage_projects(
            request.current_user
        ):
            messages.error(
                request,
                "Vous n'avez pas l'autorisation de gérer les projets.",
            )

            return redirect(
                "projet:projet_list"
            )

        return view_func(request, *args, **kwargs)

    return wrapper


# ============================================================
# PERSONNEL DE L'UTILISATEUR
# ============================================================

def get_current_personnel(request):
    user = getattr(
        request,
        "current_user",
        None,
    )

    if not user:
        return None

    return getattr(
        user,
        "personnel",
        None,
    )


# ============================================================
# PREPARATION FORMULAIRE EQUIPE
# ============================================================

def prepare_equipe_form(
    form,
    projet=None,
    affectation=None,
):
    """
    Prépare le champ personnel pour une affectation
    interne à l'entreprise.
    """

    if "personnel" in form.fields:

        form.fields["personnel"].label = (
            "Personnel de l'entreprise"
        )

        queryset = (
            Personnel.objects
            .filter(
                typeTravail="Construction"
            )
            .order_by(
                "nom",
                "prenom",
            )
        )

        if projet:

            deja_affectes = (
                EquipeProjet.objects
                .filter(
                    projet=projet
                )
                .values_list(
                    "personnel_id",
                    flat=True,
                )
            )

            if affectation and affectation.personnel_id:

                deja_affectes = deja_affectes.exclude(
                    personnel_id=affectation.personnel_id
                )

            queryset = queryset.exclude(
                id__in=deja_affectes
            )

        form.fields["personnel"].queryset = queryset

    return form


# ============================================================
# VERIFICATION D'ACCES A UN PROJET
# ============================================================

def user_has_project_access(
    user,
    projet,
):
    """
    Vérifie si l'utilisateur possède actuellement
    une affectation active sur le projet.
    """

    if not user:
        return False

    if user_can_manage_projects(user):
        return True

    personnel = getattr(
        user,
        "personnel",
        None,
    )

    if not personnel:
        return False

    aujourd_hui = timezone.localdate()

    return (
        EquipeProjet.objects
        .filter(
            projet=projet,
            personnel=personnel,
            actif=True,
            date_debut__lte=aujourd_hui,
            date_fin__gte=aujourd_hui,
        )
        .exists()
    )


# ============================================================
# PROJECT ACCESS REQUIRED
# ============================================================

def project_access_required(view_func):

    @wraps(view_func)
    @login_required_projet
    def wrapper(request, *args, **kwargs):

        projet_id = kwargs.get(
            "projet_id"
        )

        if not projet_id:
            raise PermissionDenied(
                "Projet non spécifié."
            )

        projet = get_object_or_404(
            Projet,
            pk=projet_id,
        )

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

        request.projet = projet

        return view_func(
            request,
            *args,
            **kwargs,
        )

    return wrapper


# ============================================================
# CONTRÔLE DES FONCTIONS
# ============================================================

def user_has_project_function(
    user,
    projet,
    fonctions,
):
    """
    Vérifie si l'utilisateur possède l'une des fonctions
    demandées dans l'équipe du projet.
    """

    if not user:
        return False

    if user_can_manage_projects(user):
        return True

    personnel = getattr(
        user,
        "personnel",
        None,
    )

    if not personnel:
        return False

    aujourd_hui = timezone.localdate()

    return (
        EquipeProjet.objects
        .filter(
            projet=projet,
            personnel=personnel,
            actif=True,
            date_debut__lte=aujourd_hui,
            date_fin__gte=aujourd_hui,
            fonction__in=fonctions,
        )
        .exists()
    )


# ============================================================
# CRUD CHEF D'ÉQUIPE
# ============================================================

@project_manager_required
def chef_equipe_list(
    request,
    projet_id,
):
    """
    Liste des chefs d'équipe enregistrés pour le projet.
    """

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    chefs = (
        PersonnelExecutionProjet.objects
        .filter(
            projet=projet,
            type_class="CHEF_EQUIPE",
        )
        .select_related(
            "enregistre_par",
        )
        .order_by(
            "-date_debut",
            "nom",
        )
    )

    return render(
        request,
        "projet/chef_equipe_list.html",
        {
            "projet": projet,
            "chefs": chefs,
            "user": request.current_user,
            "peut_gerer": user_can_manage_projects(
                request.current_user
            ),
            "aujourd_hui": timezone.localdate(),
        },
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

    if request.method == "POST":

        form = ChefEquipeProjetForm(
            request.POST,
            request.FILES,
            projet=projet,
        )

        form.instance.projet = projet
        form.instance.type_class = "CHEF_EQUIPE"

        if form.is_valid():

            chef = form.save(
                commit=False
            )

            chef.projet = projet
            chef.type_class = "CHEF_EQUIPE"
            chef.enregistre_par = request.current_user

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

    else:

        form = ChefEquipeProjetForm(
            projet=projet,
        )

        form.instance.projet = projet
        form.instance.type_class = "CHEF_EQUIPE"

        if "date_debut" in form.fields:
            form.fields["date_debut"].initial = (
                projet.date_debut
            )

        if "date_fin" in form.fields:
            form.fields["date_fin"].initial = (
                projet.date_fin
            )

        if "type_contrat" in form.fields:
            form.fields["type_contrat"].initial = (
                "FORFAITAIRE"
            )

    return render(
        request,
        "projet/chef_equipe_form.html",
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

    Seul l'utilisateur ayant enregistré le chef
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

    if chef.enregistre_par_id != request.current_user.pk:

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

    if request.method == "POST":

        form = ChefEquipeProjetForm(
            request.POST,
            request.FILES,
            instance=chef,
            projet=projet,
        )

        form.instance.projet = projet
        form.instance.type_class = "CHEF_EQUIPE"

        if form.is_valid():

            chef_modifie = form.save(
                commit=False
            )

            chef_modifie.projet = projet
            chef_modifie.type_class = "CHEF_EQUIPE"

            chef_modifie.enregistre_par_id = (
                chef.enregistre_par_id
            )

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

    else:

        form = ChefEquipeProjetForm(
            instance=chef,
            projet=projet,
        )

        form.instance.projet = projet
        form.instance.type_class = "CHEF_EQUIPE"

    return render(
        request,
        "projet/chef_equipe_form.html",
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
def chef_equipe_delete(
    request,
    projet_id,
    pk,
):
    """
    Supprimer un chef d'équipe.
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

    if chef.enregistre_par_id != request.current_user.pk:

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

    projet = get_object_or_404(
        Projet.objects
        .select_related(
            "enregistre_par",
        )
        .prefetch_related(
            "equipe__personnel",
            "rapports_projet__auteur",
            "rapports_travaux__auteur",
            "rapports_materiaux__materiau",
            "rapports_materiaux__auteur",
            "rapports_vehicules__vehicule",
            "rapports_vehicules__chauffeur",
        ),
        pk=projet_id,
    )

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

    equipe = (
        projet.equipe
        .all()
        .select_related(
            "personnel",
        )
        .order_by(
            "fonction",
            "personnel__nom",
            "personnel__prenom",
        )
    )

    points = (
        projet.points
        .all()
        .order_by(
            "nom"
        )
    )

    rapports_projet = (
        projet.rapports_projet
        .all()
        .select_related(
            "auteur",
        )
    )

    rapports_travaux = (
        projet.rapports_travaux
        .all()
        .select_related(
            "auteur",
        )
    )

    rapports_materiaux = (
        projet.rapports_materiaux
        .all()
        .select_related(
            "materiau",
            "auteur",
        )
    )

    rapports_vehicules = (
        projet.rapports_vehicules
        .all()
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

    # ========================================================
    # MODELES DU PROJET MATERIAUX
    # ========================================================

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

    # ========================================================
    # SORTIES MATERIAUX
    # ========================================================

    sorties_materiaux = (
        MateriauxOut.objects
        .filter(
            projet=projet
        )
        .select_related(
            "materiau",
            "division",
            "point_projet",
        )
    )

    # ========================================================
    # ACTIVITES TRANSPORT
    # ========================================================

    transports = (
        ActiviteTransport.objects
        .filter(
            projet=projet
        )
        .select_related(
            "vehicule",
            "chauffeur_personnel",
            "point_projet",
            "sortie_materiau",
        )
    )

    # ========================================================
    # RECEPTIONS
    # ========================================================

    receptions = (
        ReceptionMateriau.objects
        .filter(
            projet=projet
        )
        .select_related(
            "transport",
            "point",
            "nom",
        )
    )

    # ========================================================
    # UTILISATIONS
    # ========================================================

    utilisations = (
        UtilisationMateriau.objects
        .filter(
            reception__projet=projet
        )
    )

    # ========================================================
    # RETOURS
    # ========================================================

    retours = (
        MateriauxRetour.objects
        .filter(
            sortie__projet=projet
        )
    )

    # ========================================================
    # DEPENSES
    # ========================================================

    depenses = (
        Depense.objects
        .filter(
            projet=projet
        )
    )

    depenses_gasoil = (
        DepenseGasoil.objects
        .filter(
            projet=projet
        )
    )

    reparations = (
        ReparationVehicule.objects
        .filter(
            projet=projet
        )
    )

    paiements_dockers = (
        PaiementDocker.objects
        .filter(
            projet=projet
        )
    )

    # ========================================================
    # TOTAUX
    # ========================================================

    total_sorties = (
        sorties_materiaux
        .aggregate(
            total=Sum("quantite")
        )["total"]
        or 0
    )

    total_transport = (
        transports
        .aggregate(
            total=Sum("quantite")
        )["total"]
        or 0
    )

    total_reception = (
        receptions
        .aggregate(
            total=Sum("quantite_recue")
        )["total"]
        or 0
    )

    total_utilisation = (
        utilisations
        .aggregate(
            total=Sum("quantite_utilisee")
        )["total"]
        or 0
    )

    total_retour = (
        retours
        .aggregate(
            total=Sum("quantite")
        )["total"]
        or 0
    )

    total_depenses = (
        depenses
        .aggregate(
            total=Sum("montant")
        )["total"]
        or 0
    )

    total_gasoil = (
        depenses_gasoil
        .aggregate(
            total=Sum("total")
        )["total"]
        or 0
    )

    total_reparations = (
        reparations
        .aggregate(
            total=Sum("total")
        )["total"]
        or 0
    )

    total_dockers = (
        paiements_dockers
        .aggregate(
            total=Sum("montant")
        )["total"]
        or 0
    )

    total_depenses_projet = (
        total_depenses
        + total_gasoil
        + total_reparations
        + total_dockers
    )

    context = {
        "projet": projet,

        "equipe": equipe,
        "points": points,

        "rapports_projet": rapports_projet,
        "rapports_travaux": rapports_travaux,
        "rapports_materiaux": rapports_materiaux,
        "rapports_vehicules": rapports_vehicules,

        "total_rapports": total_rapports,

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

        "depenses": depenses,
        "depenses_gasoil": depenses_gasoil,
        "reparations": reparations,
        "paiements_dockers": paiements_dockers,

        "total_depenses": total_depenses,
        "total_gasoil": total_gasoil,
        "total_reparations": total_reparations,
        "total_dockers": total_dockers,
        "total_depenses_projet": total_depenses_projet,

        "user": request.current_user,

        "peut_gerer": user_can_manage_projects(
            request.current_user
        ),

        "acces_actuel": user_has_project_access(
            request.current_user,
            projet,
        ),

        "aujourd_hui": timezone.localdate(),
    }

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
        "projet/equipe_list.html",
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
        "projet/equipe_form.html",
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
        "projet/equipe_form.html",
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
        "projet/point_list.html",
        {
            "projet": projet,
            "points": points,
            "user": request.current_user,
        },
    )


# ============================================================
# AJOUTER UN POINT
# ============================================================

@project_manager_required
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
        "projet/point_form.html",
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
# RAPPORT MATERIAU - LISTE
# ============================================================

@project_access_required
def rapport_materiau_list(
    request,
    projet_id,
):

    rapports = (
        RapportMateriau.objects
        .filter(
            projet=request.projet
        )
        .select_related(
            "point",
            "materiau",
            "auteur",
        )
    )

    return render(
        request,
        "projet/rapport_materiau_list.html",
        {
            "projet": request.projet,
            "rapports": rapports,
            "user": request.current_user,
        },
    )


# ============================================================
# RAPPORT MATERIAU - CREER
# ============================================================

@project_access_required
def rapport_materiau_create(
    request,
    projet_id,
):

    projet = request.projet
    user = request.current_user

    if not user_has_project_function(
        user,
        projet,
        [
            "CHEF_MAGASIN",
            "MAGASINIER",
        ],
    ):

        messages.error(
            request,
            (
                "Seul le Chef Magasinier ou le Magasinier "
                "peut enregistrer un rapport matériau."
            ),
        )

        return redirect(
            "projet:projet_detail",
            projet_id=projet.pk,
        )

    if request.method == "POST":

        form = RapportMateriauForm(
            request.POST,
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
                "Le rapport matériau a été enregistré.",
            )

            return redirect(
                "projet:rapport_materiau_list",
                projet_id=projet.pk,
            )

    else:

        form = RapportMateriauForm(
            projet=projet,
        )

    return render(
        request,
        "projet/rapport_materiau_form.html",
        {
            "form": form,
            "projet": projet,
            "titre_page": "Nouveau rapport matériau",
            "user": user,
        },
    )


# ============================================================
# VEHICULES AFFECTES AUX PROJETS - LISTE
# ============================================================

@login_required_projet
def vehicule_projet_list(
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
        messages.error(
            request,
            "Votre accès à ce projet n'est pas actif.",
        )

        return redirect(
            "projet:projet_list"
        )

    affectations = (
        VehiculeProjet.objects
        .filter(
            projet=projet
        )
        .select_related(
            "chauffeur",
            "projet",
        )
        .order_by(
            "-date_debut",
            "-id",
        )
    )

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

    return render(
        request,
        "projet/vehicule_projet_list.html",
        {
            "projet": projet,
            "affectations": affectations,
            "user": request.current_user,
            "total_km": total_km,
            "total_carburant": total_carburant,
            "total_actifs": total_actifs,
        },
    )


# ============================================================
# VEHICULE - CREER
# ============================================================

@project_manager_required
def vehicule_projet_create(
    request,
    projet_id,
):

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    if request.method == "POST":

        form = VehiculeProjetForm(
            request.POST,
            projet=projet,
        )

        form.instance.projet = projet

        if form.is_valid():

            affectation = form.save(
                commit=False
            )

            affectation.projet = projet
            affectation.save()

            messages.success(
                request,
                (
                    f"Le véhicule {affectation.vehicule} "
                    f"a été affecté au projet "
                    f"« {projet.titre} »."
                ),
            )

            return redirect(
                "projet:vehicule_projet_list",
                projet_id=projet.pk,
            )

    else:

        form = VehiculeProjetForm(
            projet=projet,
        )

    return render(
        request,
        "projet/vehicule_projet_form.html",
        {
            "form": form,
            "projet": projet,
            "titre_page": "Affecter un véhicule au projet",
            "user": request.current_user,
        },
    )


# ============================================================
# VEHICULE - MODIFIER
# ============================================================

@project_manager_required
def vehicule_projet_update(
    request,
    projet_id,
    vehicule_projet_id,
):

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    affectation = get_object_or_404(
        VehiculeProjet.objects.select_related(
            "chauffeur",
            "projet",
        ),
        pk=vehicule_projet_id,
        projet=projet,
    )

    if request.method == "POST":

        form = VehiculeProjetForm(
            request.POST,
            instance=affectation,
            projet=projet,
        )

        form.instance.projet = projet

        if form.is_valid():

            affectation_modifiee = form.save(
                commit=False
            )

            affectation_modifiee.projet = projet
            affectation_modifiee.save()

            messages.success(
                request,
                (
                    "L'affectation du véhicule "
                    "a été modifiée avec succès."
                ),
            )

            return redirect(
                "projet:vehicule_projet_list",
                projet_id=projet.pk,
            )

    else:

        form = VehiculeProjetForm(
            instance=affectation,
            projet=projet,
        )

    return render(
        request,
        "projet/vehicule_projet_form.html",
        {
            "form": form,
            "projet": projet,
            "affectation": affectation,
            "titre_page": (
                "Modifier l'affectation du véhicule"
            ),
            "user": request.current_user,
        },
    )


# ============================================================
# VEHICULE - SUPPRIMER
# ============================================================

@project_manager_required
def vehicule_projet_delete(
    request,
    projet_id,
    vehicule_projet_id,
):

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    affectation = get_object_or_404(
        VehiculeProjet,
        pk=vehicule_projet_id,
        projet=projet,
    )

    if request.method == "POST":

        try:

            vehicule = str(
                affectation.vehicule
            )

            affectation.delete()

            messages.success(
                request,
                (
                    f"L'affectation du véhicule "
                    f"« {vehicule} » a été supprimée avec succès."
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

    return redirect(
        "projet:vehicule_projet_list",
        projet_id=projet.pk,
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
        "projet/rapport_vehicule_list.html",
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
        "projet/rapport_vehicule_form.html",
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
        "projet/equipe_projet_selection.html",
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
def activite_transport_projet_delete(
    request,
    projet_id,
    activite_id,
):

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
