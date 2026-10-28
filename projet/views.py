from decimal import Decimal, InvalidOperation
from functools import wraps
from django.db.models import Max
from django.contrib import messages
from django.contrib.auth.hashers import make_password
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import DecimalField, ExpressionWrapper, F, ProtectedError, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import path, reverse, reverse_lazy
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from materiaux.models import (
    ActiviteTransport,
    Depense,
    DepenseGasoil,
    MateriauxOut,
    MateriauxRetour,
    PaiementDocker,
    ReceptionMateriau,
    ReparationVehicule,
    UtilisationMateriau,
)
from django.db.models import ProtectedError
from personnel.models import Personnel
from projet.models import (
    AchatMateriauProjet,
    ConsommationMateriauProjet,
    DistributionMateriauProjet,
    ReceptionMateriauProjet,
    RetourMateriauProjet,
)
from datetime import datetime
from users.decorators import (
    get_current_personnel,
    get_current_user,
    login_required_projet,
    project_access_required,
    project_manager_required,
    user_can_manage_materiaux,
    user_can_manage_projects,
    user_has_project_access,
    user_has_project_function,
)
from users.models import AppUser
from .models import MateriauProjet, ReparationVehicule
from .forms import (
    AchatMateriauProjetForm,
    ActiviteTransportProjetForm,
    AvanceEquipeProjetForm,
    ChefEquipeProjetForm,
    ConsommationMateriauProjetForm,
    DistributionMateriauProjetForm,
    EnginProjetForm,
    EquipeProjetForm,
    MateriauProjetForm,
    MinierProjetForm,
    MouvementMateriauProjetForm,
    MouvementVehiculeProjetForm,
    PointProjetForm,
    ProjetForm,
    RapportMateriauForm,
    RapportProjetForm,
    RapportTravailForm,
    RapportVehiculeForm,
    ReceptionMateriauProjetForm,
    RetourMateriauProjetForm,
    VehiculeProjetForm,
)
from .models import (
    ActiviteTransportProjet,
    AvanceEquipeProjet,
    EnginProjet,
    EquipageProjet,
    EquipeMateriauProjet,
    EquipeProjet,
    MateriauProjet,
    MouvementMateriauProjet,
    MouvementPersonnelProjet,
    MouvementVehiculeProjet,
    PersonnelExecutionProjet,
    PointProjet,
    Projet,
    RapportMateriau,
    RapportProjet,
    RapportTravail,
    RapportVehicule,
    VehiculeLourdsProjet,
    VehiculeProjet,
)
from django.utils.dateparse import parse_date

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


def synchroniser_affectations_equipe(projet):
    correspondances = {
        "CHEF_EQUIPE": "CHEF_EQUIPE",
        "MINIER": "MINIER",
    }

    resultat = {
        "crees": 0,
        "existantes": 0,
        "ignores": 0,
        "erreurs": [],
    }

    executions = PersonnelExecutionProjet.objects.filter(
        projet_id=projet.pk,
        type_class__in=correspondances.keys(),
    ).select_related(
        "projet",
        "personnel",
        "point_projet",
        "materiau_projet",
    )

    for execution in executions:
        fonction = correspondances.get(execution.type_class)

        if not fonction:
            resultat["ignores"] += 1
            continue

        # Ne pas crÃ©er de doublon.
        if EquipeProjet.objects.filter(
            projet_id=projet.pk,
            personnel_execution_id=execution.pk,
        ).exists():
            resultat["existantes"] += 1
            continue

        # Utiliser les dates individuelles ou celles du projet.
        date_debut = execution.date_debut or projet.date_debut
        date_fin = execution.date_fin or projet.date_fin

        # VÃ©rifier que les deux dates sont disponibles.
        if not date_debut or not date_fin:
            resultat["ignores"] += 1
            resultat["erreurs"].append(
                {
                    "execution_id": execution.pk,
                    "nom": execution.nom,
                    "erreur": (
                        "Date de dÃ©but ou de fin absente "
                        "dans l'inscription et dans le projet."
                    ),
                }
            )
            continue

        affectation = EquipeProjet(
            projet=projet,
            personnel_execution=execution,
            fonction=fonction,
            date_debut=date_debut,
            date_fin=date_fin,
        )

        try:
            with transaction.atomic():
                affectation.full_clean()
                affectation.save()

            resultat["crees"] += 1

        except ValidationError as exc:
            resultat["ignores"] += 1
            resultat["erreurs"].append(
                {
                    "execution_id": execution.pk,
                    "nom": execution.nom,
                    "erreur": (
                        exc.message_dict
                        if hasattr(exc, "message_dict")
                        else exc.messages
                    ),
                }
            )

    return resultat


# ============================================================
# CRUD CHEF D'EQUIPE
# ============================================================
@project_manager_required
def chef_equipe_list(request, projet_id):

    current_user = request.current_user

    # ============================================================
    # PROJET
    # ============================================================

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    # ============================================================
    # VÃ‰RIFICATION DE L'ACCÃˆS
    # ============================================================

    if not user_has_project_access(current_user, projet):
        messages.error(
            request,
            "Votre accÃ¨s Ã  ce projet n'est pas actif.",
        )
        return redirect("projet:projet_list")

    # ============================================================
    # DROITS
    # ============================================================

    peut_gerer = user_can_manage_projects(current_user)

    personnel_connecte = getattr(
        current_user,
        "personnel",
        None,
    )

    # ============================================================
    # FILTRES
    # ============================================================

    nom = request.GET.get("nom", "").strip()
    date_debut = request.GET.get("date_debut", "").strip()
    date_fin = request.GET.get("date_fin", "").strip()

    # ============================================================
    # REQUÃŠTE DES CHEFS D'Ã‰QUIPE
    # ============================================================

    chefs_queryset = PersonnelExecutionProjet.objects.filter(
        projet=projet,
        type_class="CHEF_EQUIPE",
    ).select_related(
        "projet",
        "enregistre_par",
        "point_projet",
    )

    if nom:
        chefs_queryset = chefs_queryset.filter(
            nom__icontains=nom,
        )

    if date_debut:
        chefs_queryset = chefs_queryset.filter(
            date_debut__gte=date_debut,
        )

    if date_fin:
        chefs_queryset = chefs_queryset.filter(
            date_fin__lte=date_fin,
        )

    chefs_queryset = chefs_queryset.order_by(
        "-date_debut",
        "nom",
        "id",
    )

    # ============================================================
    # LISTE ET STATISTIQUES
    # ============================================================

    chefs = list(chefs_queryset)

    total_remuneration = Decimal("0.00")
    total_avances = Decimal("0.00")
    total_solde = Decimal("0.00")

    for chef in chefs:

        # Montant forfaitaire total du contrat
        montant_forfait = chef.montant or Decimal("0.00")
        avances_queryset = AvanceEquipeProjet.objects.filter(
            equipe_execution__projet=projet,
            equipe_execution__personnel_execution=chef,
        )

        montant_avances = avances_queryset.aggregate(
            total=Sum("montant"),
        )[
            "total"
        ] or Decimal("0.00")

        chef.montant_forfait = montant_forfait
        chef.total_avances = montant_avances
        chef.solde = montant_forfait - montant_avances

        total_remuneration += montant_forfait
        total_avances += montant_avances
        total_solde += chef.solde

        chef.peut_modifier = (
            personnel_connecte is not None
            and chef.enregistre_par_id == personnel_connecte.pk
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
        "total_avances": total_avances,
        "total_solde": total_solde,
    }

    return render(
        request,
        "projet/chefEquipe/list.html",
        context,
    )


# ============================================================
# AJOUTER UN CHEF D'EQUIPE
# ============================================================
@project_manager_required
def chef_equipe_create(    request,    projet_id,):
    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )
    personnel_connecte = get_object_or_404(
        Personnel,
        pk=request.current_user.pk,
    )
    if request.method == "POST":
        form = ChefEquipeProjetForm(
            request.POST,
            request.FILES,
            projet=projet,
        )
        if form.is_valid():
            chef = form.save(commit=False)
            chef.projet = projet
            chef.type_class = "CHEF_EQUIPE"
            chef.type_contrat = "FORFAITAIRE"
            chef.enregistre_par = personnel_connecte
            chef.save()
            messages.success(
                request,
                (
                    f"Le chef d'équipe  {chef.nom} a été dans le  {projet.titre}."
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
# MODIFIER UN CHEF D'Ã‰QUIPE
# ============================================================
@project_manager_required
def chef_equipe_update(    request,    projet_id,   pk,):
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
    personnel_connecte = get_object_or_404(
        Personnel,
        pk=request.current_user.pk,
    )
    if chef.enregistre_par_id != personnel_connecte.pk:
        messages.error(
            request,
            (
                "Vous ne pouvez modifier que les chefs d'équipe que vous avez enregistrés."
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
        if form.is_valid():
            chef_modifie = form.save(commit=False)
            chef_modifie.projet = projet
            chef_modifie.type_class = "CHEF_EQUIPE"
            chef_modifie.type_contrat = "FORFAITAIRE"
            chef_modifie.enregistre_par = chef.enregistre_par
            chef_modifie.save()
            messages.success(
                request,
                (
                    f"La modification de {chef_modifie.nom} comme chef d'équipe a été avec succé."
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
# SUPPRIMER UN CHEF D'Ã‰QUIPE
# ============================================================
@project_manager_required
def chef_equipe_delete(request, projet_id, pk):
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
    personnel_connecte = get_object_or_404(
        Personnel,
        pk=request.current_user.pk,
    )
    if chef.enregistre_par_id != personnel_connecte.pk:
        messages.error(
            request,
            "Vous ne pouvez supprimer que les chefs "
            "d'Ã©quipe que vous avez enregistrÃ©s.",
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
        with transaction.atomic():
            # Verrouiller le chef et ses affectations
            chef = PersonnelExecutionProjet.objects.select_for_update().get(
                pk=pk,
                projet=projet,
                type_class="CHEF_EQUIPE",
            )

            affectations = list(
                EquipeProjet.objects.select_for_update().filter(
                    personnel_execution=chef
                )
            )

            # Ne pas supprimer une affectation utilisÃ©e
            for affectation in affectations:
                if (
                    affectation.avances_equipe.exists()
                    or affectation.avances_miniers.exists()
                ):
                    raise ProtectedError(
                        "Une affectation possÃ¨de des avances.",
                        [affectation],
                    )

            # Supprimer les affectations inutilisÃ©es
            for affectation in affectations:
                affectation.delete()

            # Supprimer ensuite le chef
            chef.delete()

        messages.success(
            request,
            f"Le chef d'équipe {nom} et ses affectations inutilisés ont étés supprimés.",
        )

    except ProtectedError:
        messages.error(
            request,
            "Impossible de supprimer ce chef d'équipe : "
            "d'autres donnÃ©es du projet utilisent encore ce chef ou l'une de ses affectations. "
            "Aucune suppression partielle n'a étés conservée.",
        )

    except PersonnelExecutionProjet.DoesNotExist:
        messages.error(
            request,
            "Ce chef d'équipe n'existe plus ou a déjà supprimé.",
        )

    return redirect(
        "projet:chef_equipe_list",
        projet_id=projet.pk,
    )


# ============================================================
# CREER UN COMPTE UTILISATEUR POUR UN MEMBRE DU PROJET
# ============================================================
@project_manager_required
def utilisateur_projet_create(    request,    projet_id,    equipe_id,):
    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )
    affectation = get_object_or_404(
        EquipeProjet.objects.select_related("personnel"),
        pk=equipe_id,
        projet=projet,
    )

    personnel = affectation.personnel

    if not personnel:

        messages.error(
            request,
            "Cette affectation ne posséde pas de personnel interne.",
        )

        return redirect(
            "projet:equipe_list",
            projet_id=projet.pk,
        )

    compte_existant = AppUser.objects.filter(personnel=personnel).first()

    if compte_existant:

        messages.warning(
            request,
            (
                f"{personnel} poste de déjà un compte utilisateur {compte_existant.username}."
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

        elif AppUser.objects.filter(username=username).exists():

            messages.error(
                request,
                (f"Le nom d'utilisateur {username} existe déjà."),
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
                    f"Le compte {utilisateur.username} a été crée pour {personnel}."
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
                Projet.objects.filter(
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
        form = ProjetForm(request.POST)
        if form.is_valid():
            projet = form.save(commit=False)
            projet.enregistre_par = request.current_user
            projet.save()
            messages.success(
                request,
                "Le projet a été crée avec succés.",
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
def projet_update(    request,    projet_id,):

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
            projet_modifie = form.save(commit=False)
            projet_modifie.enregistre_par_id = projet.enregistre_par_id
            projet_modifie.save()
            messages.success(
                request,
                "Le projet a été modifié avec succés.",
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
def projet_delete(    request,    projet_id,):
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
            "Le projet a éte supprimé.",
        )

    except ProtectedError:

        messages.error(
            request,
            (
                "Impossible de supprimer ce projet car "
                "il possÃ¨de des données liées."
            ),
        )

    return redirect("projet:projet_list")


# ============================================================
# DETAIL D'UN PROJET
# ============================================================
@login_required_projet
def projet_detail(    request,    projet_id,):
    current_user = request.current_user
    if not current_user:
        messages.error(
            request,
            "Utilisateur connecté introuvable.",
        )

        return redirect("users:login")
    projet = get_object_or_404(
        Projet.objects.select_related(
            "enregistre_par",
        ),
        pk=projet_id,
    )
    if not user_has_project_access(
        current_user,
        projet,
    ):
        messages.error(
            request,
            "Votre accés à ce projet n'est pas actif.",
        )

        return redirect("projet:projet_list")
    equipe = (
        projet.equipe.all()
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
    equipe_active = sum(1 for membre in equipe if membre.acces_actif)
    fonction_projet = None
    personnel_connecte_id = getattr(
        current_user,
        "personnel_id",
        None,
    )

    if personnel_connecte_id:

        for membre in equipe:
            if membre.personnel_id and membre.personnel_id == personnel_connecte_id:

                if membre.acces_actif:

                    fonction_projet = membre.fonction

                    break
            if membre.personnel_execution_id and membre.personnel_execution:

                personnel_execution = membre.personnel_execution

                if (
                    personnel_execution.personnel_id
                    and personnel_execution.personnel_id == personnel_connecte_id
                ):

                    if membre.acces_actif:

                        fonction_projet = membre.fonction

                        break
    points = projet.points.all().order_by(
        "nom",
    )
    chefs_equipe = (
        PersonnelExecutionProjet.objects.filter(
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

    nombre_chefs_equipe = chefs_equipe.count()
    personnels_execution = (
        PersonnelExecutionProjet.objects.filter(
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
    miniers = personnels_execution.filter(
        type_class="MINIER",
    )

    nombre_miniers = miniers.count()
    materiaux_projet = (
        projet.materiaux_projet.all()
        .select_related(
            "projet",
        )
        .order_by(
            "materiau",
            "id",
        )
    )

    nombre_materiaux_projet = materiaux_projet.count()
    rapports_projet = (
        projet.rapports_projet.all()
        .select_related(
            "auteur",
        )
        .order_by(
            "-date_rapport",
        )
    )
    rapports_travaux = (
        projet.rapports_travaux.all()
        .select_related(
            "auteur",
        )
        .order_by(
            "-date_debut",
        )
    )
    rapports_materiaux = (
        projet.rapports_materiaux.all()
        .select_related(
            "materiau",
            "auteur",
        )
        .order_by(
            "-date_ravitaillement",
        )
    )
    rapports_vehicules = (
        projet.rapports_vehicules.all()
        .select_related(
            "vehicule",
            "chauffeur",
        )
        .order_by(
            "-date_rapport",
        )
    )
    total_rapports = (
        rapports_projet.count()
        + rapports_travaux.count()
        + rapports_materiaux.count()
        + rapports_vehicules.count()
    )

    nombre_rapports_travaux = rapports_travaux.count()
    sorties_materiaux = MateriauxOut.objects.filter(
        projet=projet,
    ).select_related(
        "materiau",
        "division",
        "point_projet",
    )
    transports = ActiviteTransport.objects.filter(
        projet=projet,
    ).select_related(
        "vehicule",
        "chauffeur_personnel",
        "point_projet",
        "sortie_materiau",
    )
    receptions = ReceptionMateriau.objects.filter(
        projet=projet,
    ).select_related(
        "transport",
        "point",
    )
    utilisations = UtilisationMateriau.objects.filter(
        reception__projet=projet,
    )
    retours = MateriauxRetour.objects.filter(
        sortie__projet=projet,
    )
    depenses = Depense.objects.filter(
        projet=projet,
    )
    depenses_gasoil = DepenseGasoil.objects.filter(
        projet=projet,
    )
    reparations = (ReparationVehicule.objects
    .filter(projet=projet)
    .select_related(
        "vehicule",
        "chauffeur_personnel",
        "enregistre_par",
    )
)
    paiements_dockers = PaiementDocker.objects.filter(
        projet=projet,
    )
    total_sorties = (
        sorties_materiaux.aggregate(
            total=Sum("quantite"),
        )["total"]
        or 0
    )

    total_transport = (
        transports.aggregate(
            total=Sum("quantite"),
        )["total"]
        or 0
    )

    total_reception = (
        receptions.aggregate(
            total=Sum("quantite_recue"),
        )["total"]
        or 0
    )

    total_utilisation = (
        utilisations.aggregate(
            total=Sum("quantite_utilisee"),
        )["total"]
        or 0
    )

    total_retour = (
        retours.aggregate(
            total=Sum("quantite"),
        )["total"]
        or 0
    )

    # ============================================================
    # TOTAL MATÃ‰RIAUX RAVITAILLÃ‰S
    # ============================================================

    total_materiaux = total_sorties

    # ============================================================
    # TOTAUX DÃ‰PENSES
    # ============================================================

    total_depenses = (
        depenses.aggregate(
            total=Sum("montant"),
        )["total"]
        or 0
    )

    total_gasoil = (
        depenses_gasoil.aggregate(
            total=Sum("total"),
        )["total"]
        or 0
    )

    total_reparations = (
        reparations.aggregate(
            total=Sum("total"),
        )["total"]
        or 0
    )

    total_dockers = (
        paiements_dockers.aggregate(
            total=Sum("montant"),
        )["total"]
        or 0
    )

    # ============================================================
    # TOTAL GLOBAL DÃ‰PENSES PROJET
    # ============================================================

    total_depenses_projet = (
        total_depenses + total_gasoil + total_reparations + total_dockers
    )

    # ============================================================
    # PERMISSION DE GESTION
    # ============================================================

    peut_gerer = user_can_manage_projects(current_user)

    # ============================================================
    # ACCÃˆS ACTUEL
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
        # Ã‰QUIPE
        # --------------------------------------------------------
        "equipe": equipe,
        "equipe_active": equipe_active,
        # --------------------------------------------------------
        # CHEFS D'Ã‰QUIPE
        # --------------------------------------------------------
        "chefs_equipe": chefs_equipe,
        "nombre_chefs_equipe": nombre_chefs_equipe,
        # --------------------------------------------------------
        # PERSONNEL D'EXÃ‰CUTION
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
        # MATÃ‰RIAUX DU PROJET
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
        # MATÃ‰RIAUX / LOGISTIQUE
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
        # DÃ‰PENSES
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
# RAPPORT FINANCIER GLOBAL DU PROJET
# ============================================================
@project_access_required
def rapport_projet_global(request, projet_id):
    projet = request.projet

    ZERO = Decimal("0.00")

    # --------------------------------------------------------
    # 1. ACHATS DE MATÃ‰RIAUX
    # --------------------------------------------------------
    achats_materiaux = (
        AchatMateriauProjet.objects.filter(materiau_projet__projet=projet)
        .select_related(
            "materiau_projet",
            "enregistre_par",
        )
        .order_by("-date_achat", "-id")
    )

    total_achats = ZERO

    for achat in achats_materiaux:
        total_achats += achat.montant_total

    # --------------------------------------------------------
    # 2. RÃ‰MUNÃ‰RATION PRÃ‰VUE DU PERSONNEL D'EXÃ‰CUTION
    # --------------------------------------------------------
    personnels_execution = (
        PersonnelExecutionProjet.objects.filter(projet=projet)
        .select_related(
            "point_projet",
            "materiau_projet",
        )
        .order_by("type_class", "nom")
    )

    total_chefs_equipe = ZERO
    total_miniers = ZERO
    total_autres_personnels = ZERO

    for personne in personnels_execution:
        montant = personne.montant_total_paiement or ZERO

        if personne.type_class == "CHEF_EQUIPE":
            total_chefs_equipe += montant

        elif personne.type_class == "MINIER":
            total_miniers += montant

        else:
            total_autres_personnels += montant

    total_remunerations = total_chefs_equipe + total_miniers + total_autres_personnels

    # --------------------------------------------------------
    # 3. AVANCES VERSÃ‰ES AUX Ã‰QUIPES
    # --------------------------------------------------------
    avances_equipe = (
        AvanceEquipeProjet.objects.filter(
            # Les avances sont rattachées Ã  EquipeProjet.
            # On recherche les équipes du projet concerné.
            # Le filtre exact dépend de la relation utilisée.
            # Voir la correction ci-dessous si nécessaire.
            equipe_execution__projet=projet
        )
        .select_related(
            "equipe_execution",
            "miniers_execution",
            "enregistre_par",
        )
        .order_by("-date_avance", "-id")
    )

    # Inclure aussi les avances rattachées aux équipes de miniers.
    avances_miniers = (
        AvanceEquipeProjet.objects.filter(miniers_execution__projet=projet)
        .select_related(
            "equipe_execution",
            "miniers_execution",
            "enregistre_par",
        )
        .order_by("-date_avance", "-id")
    )

    # Ã‰viter les doublons si une avance correspond Ã  une seule équipe.
    avances_equipe = (
        (avances_equipe | avances_miniers).distinct().order_by("-date_avance", "-id")
    )

    total_avances = avances_equipe.aggregate(total=Sum("montant"))["total"] or ZERO

    # --------------------------------------------------------
    # 4. SYNTHESE FINANCIERE
    # --------------------------------------------------------
    budget_previsionnel = projet.budget_previsionnel or ZERO

    total_depenses_identifiees = total_achats + total_remunerations

    solde_budget = budget_previsionnel - total_depenses_identifiees

    depassement_budget = max(
        ZERO,
        -solde_budget,
    )

    taux_utilisation = (
        total_depenses_identifiees / budget_previsionnel * Decimal("100")
        if budget_previsionnel > ZERO
        else ZERO
    )

    return render(
        request,
        "projet/rapport_financier.html",
        {
            "projet": projet,
            "aujourd_hui": timezone.localdate(),
            # Budget
            "budget_previsionnel": budget_previsionnel,
            "total_achats": total_achats,
            # Rémunérations
            "personnels_execution": personnels_execution,
            "total_chefs_equipe": total_chefs_equipe,
            "total_miniers": total_miniers,
            "total_autres_personnels": total_autres_personnels,
            "total_remunerations": total_remunerations,
            # Achats et avances
            "achats_materiaux": achats_materiaux,
            "avances_equipe": avances_equipe,
            "total_avances": total_avances,
            # SynthÃ¨se
            "total_depenses_identifiees": total_depenses_identifiees,
            "solde_budget": solde_budget,
            "depassement_budget": depassement_budget,
            "taux_utilisation": taux_utilisation,
            "user": request.current_user,
            "peut_gerer": user_can_manage_projects(request.current_user),
        },
    )


# ============================================================
# EQUIPE - LISTE
# ============================================================
@project_manager_required
def equipe_list(    request,    projet_id,):

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    equipe = (
        EquipeProjet.objects.filter(projet=projet)
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
            "peut_gerer": user_can_manage_projects(request.current_user),
        },
    )


# ============================================================
# CRÃ‰ATION D'UNE AFFECTATION D'Ã‰QUIPE
# ============================================================
@project_manager_required
def equipe_create(request, projet_id):

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

        if form.is_valid():

            affectation = form.save(
                commit=False,
            )

            affectation.projet = projet
            affectation.save()

            messages.success(
                request,
                (
                    f"{affectation.personnel} a été affecté au projet {projet.titre} comme "
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
def equipe_update(request, projet_id, equipe_id):
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

        if form.is_valid():
            affectation_modifiee = form.save(commit=False)
            affectation_modifiee.projet = projet
            affectation_modifiee.save()

            messages.success(
                request,
                (
                    f"L'affectation de {affectation_modifiee.personnel} a été modifiée avec succès."
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
def equipe_delete(    request,    projet_id,    equipe_id,):

    affectation = get_object_or_404(
        EquipeProjet,
        pk=equipe_id,
        projet_id=projet_id,
    )

    if request.method != "POST":

        messages.error(
            request,
            ("La suppression d'une affectation doit Ãªtre effectuée par POST."),
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
            (f"L'affectation de {personnel} a été supprimée du projet."),
        )

    except ProtectedError:

        messages.error(
            request,
            (
                "Cette affectation est utilisée par des données historiques et ne peut pas être supprimee."
            ),
        )

    return redirect(
        "projet:equipe_list",
        projet_id=projet_id,
    )


# ============================================================
# DROITS DE GESTION PAR POINT
# ============================================================
def peut_gerer_point_utilisateur(user, point):
    """
    Autorise le gestionnaire du projet ou l'enregistreur du point.
    Prend en charge un utilisateur AppUser ou son Personnel associé.
    """
    if user is None or point is None:
        return False

    # Les gestionnaires conservent leurs droits habituels.
    if user_can_manage_projects(user):
        return True

    # Normaliser l'utilisateur en AppUser si nécessaire.
    if not isinstance(user, AppUser):
        personnel_id = getattr(user, "pk", None)

        if personnel_id is None:
            return False

        user = AppUser.objects.filter(
            personnel_id=personnel_id
        ).first()

    if user is None:
        return False

    # Seul l'enregistreur du point peut le gérer,
    # en dehors des gestionnaires autorisés.
    return (
        point.enregistre_par_id is not None
        and point.enregistre_par_id == user.pk
    )
# ============================================================
# POINTS - LISTE
# ============================================================
@login_required_projet
def point_list(request, projet_id):
    current_user = request.current_user

    # --------------------------------------------------------
    # RÉCUPÉRATION DU PROJET
    # --------------------------------------------------------
    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    # --------------------------------------------------------
    # VÉRIFICATION DE L'ACCÈS AU PROJET
    # --------------------------------------------------------
    if not user_has_project_access(current_user, projet):
        messages.error(
            request,
            "Votre accès à ce projet n'est pas actif.",
        )
        return redirect("projet:projet_list")

    # --------------------------------------------------------
    # FILTRES
    # --------------------------------------------------------
    localisation = request.GET.get(
        "localisation", ""
    ).strip()

    observation = request.GET.get(
        "observation", ""
    ).strip()

    distance_min = request.GET.get(
        "distance_min", ""
    ).strip()

    distance_max = request.GET.get(
        "distance_max", ""
    ).strip()

    queryset = (
        PointProjet.objects
        .filter(projet=projet)
        .select_related("enregistre_par")
    )

    if localisation:
        queryset = queryset.filter(
            localisation__icontains=localisation,
        )

    if observation:
        queryset = queryset.filter(
            observation__icontains=observation,
        )

    # --------------------------------------------------------
    # DISTANCE MINIMALE
    # --------------------------------------------------------
    if distance_min:
        try:
            valeur_min = Decimal(distance_min)

            if not valeur_min.is_finite() or valeur_min < 0:
                raise InvalidOperation

            queryset = queryset.filter(
                distance_km__gte=valeur_min,
            )

        except (InvalidOperation, ValueError):
            messages.warning(
                request,
                "La distance minimale saisie n'est pas valide.",
            )
            distance_min = ""

    # --------------------------------------------------------
    # DISTANCE MAXIMALE
    # --------------------------------------------------------
    if distance_max:
        try:
            valeur_max = Decimal(distance_max)

            if not valeur_max.is_finite() or valeur_max < 0:
                raise InvalidOperation

            queryset = queryset.filter(
                distance_km__lte=valeur_max,
            )

        except (InvalidOperation, ValueError):
            messages.warning(
                request,
                "La distance maximale saisie n'est pas valide.",
            )
            distance_max = ""

    # --------------------------------------------------------
    # STATISTIQUES
    # --------------------------------------------------------
    total_points = queryset.count()

    total_distance = (
        queryset.aggregate(
            distance_max=Max("distance_km"),
        )["distance_max"]
        or Decimal("0.00")
    )

    # --------------------------------------------------------
    # PAGINATION : 10 POINTS PAR PAGE
    # --------------------------------------------------------
    paginator = Paginator(
        queryset.order_by(
            "distance_km",
            "nom",
            "pk",
        ),
        10,
    )

    page_obj = paginator.get_page(
        request.GET.get("page"),
    )

    points = list(page_obj.object_list)

    # --------------------------------------------------------
    # DROITS DE GESTION DE CHAQUE POINT
    # --------------------------------------------------------
    for point in points:
        point.peut_gerer = peut_gerer_point_utilisateur(
            current_user,
            point,
        )

    # --------------------------------------------------------
    # CONTEXTE DU TEMPLATE
    # --------------------------------------------------------
    context = {
        "projet": projet,
        "points": points,
        "page_obj": page_obj,
        "paginator": paginator,
        "total_points": total_points,
        "total_distance": total_distance,
        "localisation_filtre": localisation,
        "observation_filtre": observation,
        "distance_min": distance_min,
        "distance_max": distance_max,
        "user": current_user,
        "current_user": current_user,
    }

    # --------------------------------------------------------
    # AFFICHAGE DE LA LISTE
    # --------------------------------------------------------
    return render(
        request,
        "projet/point/list.html",
        context,
    )

# ============================================================
# AJOUTER UN POINT DE CHANTIER
# ============================================================
@login_required_projet
def point_create(request, projet_id):

    # ========================================================
    # UTILISATEUR CONNECTÃ‰
    # ========================================================
    current_user = request.current_user

    if not current_user:
        messages.error(
            request,
            "Utilisateur connecté introuvable.",
        )
        return redirect("users:login")

    # ========================================================
    # RECUPERER LE PROJET
    # ========================================================
    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    # ========================================================
    # VÃ‰RIFIER L'ACCÃˆS AU PROJET
    # ========================================================
    if not user_has_project_access(current_user, projet):
        messages.error(
            request,
            "Votre accés à ce projet n'est pas actif.",
        )
        return redirect("projet:projet_list")

    # ========================================================
    # TRAITEMENT DU FORMULAIRE
    # ========================================================
    if request.method == "POST":

        form = PointProjetForm(
            request.POST,
            projet=projet,
        )

        if form.is_valid():

            point = form.save(commit=False)

            # Associer le projet courant.
            point.projet = projet

            point.enregistre_par = current_user

            point.save()

            form.save_m2m()

            messages.success(
                request,
                f"Le point {point.nom} a été créer avec succées.",
            )

            return redirect(
                "projet:point_list",
                projet_id=projet.pk,
            )

        else:
            messages.error(
                request,
                "Veuillez corriger les erreurs du formulaire.",
            )

    # ========================================================
    # AFFICHAGE DU FORMULAIRE
    # ========================================================
    else:
        form = PointProjetForm(
            projet=projet,
        )

    # ========================================================
    # CONTEXTE
    # ========================================================
    context = {
        "form": form,
        "projet": projet,
        "user": current_user,
        "current_user": current_user,
        "titre_page": "Nouveau point de chantier",
    }

    # ========================================================
    # AFFICHAGE
    # ========================================================
    return render(
        request,
        "projet/point/form.html",
        context,
    )


# ============================================================
# MODIFIER UN POINT DE CHANTIER
# ============================================================
@login_required_projet
def point_update(request, projet_id, point_id):

    current_user = request.current_user

    # --------------------------------------------------------
    # RECUPERATION LE PROJET ET LE POINT
    # --------------------------------------------------------
    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    point = get_object_or_404(
        PointProjet.objects.select_related("enregistre_par"),
        pk=point_id,
        projet=projet,
    )

    # --------------------------------------------------------
    # VERIFIER L'ACCES AU PROJET
    # --------------------------------------------------------
    if not user_has_project_access(current_user, projet):
        messages.error(
            request,
            "Votre accÃ¨s Ã  ce projet n'est pas actif.",
        )
        return redirect("projet:projet_list")

    # --------------------------------------------------------
    # DROITS : GESTIONNAIRE OU ENREGISTREUR DU POINT
    # --------------------------------------------------------
    est_gestionnaire = user_can_manage_projects(current_user)

    est_enregistreur = (
        current_user is not None
        and point.enregistre_par_id is not None
        and point.enregistre_par_id == current_user.pk
    )

    if not (est_gestionnaire or est_enregistreur):
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de modifier ce point.",
        )
        return redirect(
            "projet:point_list",
            projet_id=projet.pk,
        )

    # --------------------------------------------------------
    # TRAITEMENT DU FORMULAIRE
    # --------------------------------------------------------
    if request.method == "POST":

        form = PointProjetForm(
            request.POST,
            instance=point,
            projet=projet,
        )

        if form.is_valid():

            point_modifie = form.save(commit=False)

            # Conserver le projet et le créateur d'origine.
            point_modifie.projet = projet
            point_modifie.enregistre_par = point.enregistre_par

            point_modifie.save()
            form.save_m2m()

            messages.success(
                request,
                f"Le point {point.nom} a été modifié avec succés.",
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

    # --------------------------------------------------------
    # AFFICHAGE
    # --------------------------------------------------------
    return render(
        request,
        "projet/point/form.html",
        {
            "form": form,
            "projet": projet,
            "point": point,
            "titre_page": "Modifier le point de chantier",
            "user": current_user,
            "current_user": current_user,
        },
    )


# ============================================================
# SUPPRIMER UN POINT DE CHANTIER
# ============================================================
@login_required_projet
def point_delete(request, projet_id, point_id):

    current_user = request.current_user

    # --------------------------------------------------------
    # RÃ‰CUPÃ‰RER LE PROJET ET LE POINT
    # --------------------------------------------------------
    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    point = get_object_or_404(
        PointProjet.objects.select_related("enregistre_par"),
        pk=point_id,
        projet=projet,
    )

    # --------------------------------------------------------
    # VÃ‰RIFIER L'ACCÃˆS AU PROJET
    # --------------------------------------------------------
    if not user_has_project_access(current_user, projet):
        messages.error(
            request,
            "Votre accÃ¨s Ã  ce projet n'est pas actif.",
        )
        return redirect("projet:projet_list")

    # --------------------------------------------------------
    # DROITS : GESTIONNAIRE OU ENREGISTREUR DU POINT
    # --------------------------------------------------------
    est_gestionnaire = user_can_manage_projects(current_user)

    est_enregistreur = (
        current_user is not None
        and point.enregistre_par_id is not None
        and point.enregistre_par_id == current_user.pk
    )

    if not (est_gestionnaire or est_enregistreur):
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de supprimer ce point.",
        )
        return redirect(
            "projet:point_list",
            projet_id=projet.pk,
        )

    # --------------------------------------------------------
    # SUPPRESSION UNIQUEMENT PAR POST
    # --------------------------------------------------------
    if request.method != "POST":
        messages.warning(
            request,
            "La suppression doit être confirmée depuis le formulaire.",
        )
        return redirect(
            "projet:point_list",
            projet_id=projet.pk,
        )

    nom_point = point.nom

    try:
        point.delete()

        messages.success(
            request,
            f"Le point {nom_point} a été supprimé avec succés.",
        )

    except ProtectedError:
        messages.error(
            request,
            (
                "Impossible de supprimer ce point, car il est utilisé par des données du projet."
            ),
        )

    return redirect(
        "projet:point_list",
        projet_id=projet.pk,
    )


@login_required_projet
def minier_list(request, projet_id):
    """
    Affiche les miniers d'un projet avec filtres,
    nombre de résultats et montant total de production.
    """
    from decimal import Decimal

    from django.contrib import messages
    from django.shortcuts import get_object_or_404, redirect, render
    from django.utils.dateparse import parse_date

    # ---------------------------------------------------------
    # 1. Utilisateur connecté
    # ---------------------------------------------------------
    current_user = getattr(request, "current_user", None)

    if current_user is None:
        return redirect("users:login")

    personnel_connecte = getattr(current_user, "personnel", None)

    # ---------------------------------------------------------
    # 2. Projet
    # ---------------------------------------------------------
    projet = get_object_or_404(Projet, pk=projet_id)

    # IMPORTANT :
    # Réintégrer ici les vérifications originales d'accès au projet
    # et la définition originale de peut_gerer.
    # Ne pas remplacer les contrôles d'autorisation par une valeur fixe.
    #
    # Exemple de variable attendue par le template :
    # peut_gerer = ... (selon tes règles existantes)

    peut_gerer = False  # Provisoire : à remplacer par la logique originale.

    # ---------------------------------------------------------
    # 3. Queryset des miniers de ce projet
    # ---------------------------------------------------------
    miniers_queryset = (
        PersonnelExecutionProjet.objects.filter(
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

    # ---------------------------------------------------------
    # 4. Récupération des filtres
    # ---------------------------------------------------------
    nom = request.GET.get("nom", "").strip()
    materiau = request.GET.get("materiau", "").strip()
    date_debut_str = request.GET.get("date_debut", "").strip()
    date_fin_str = request.GET.get("date_fin", "").strip()

    date_debut = parse_date(date_debut_str) if date_debut_str else None
    date_fin = parse_date(date_fin_str) if date_fin_str else None

    # ---------------------------------------------------------
    # 5. Application des filtres
    # ---------------------------------------------------------
    if nom:
        miniers_queryset = miniers_queryset.filter(
            nom__icontains=nom
        )

    if materiau:
        if materiau.isdigit():
            miniers_queryset = miniers_queryset.filter(
                materiau_projet_id=int(materiau)
            )
        else:
            messages.warning(
                request,
                "Le matériau sélectionné est invalide.",
            )

    if date_debut_str:
        if date_debut:
            miniers_queryset = miniers_queryset.filter(
                date_production__gte=date_debut
            )
        else:
            messages.warning(
                request,
                "La date de début est invalide.",
            )

    if date_fin_str:
        if date_fin:
            miniers_queryset = miniers_queryset.filter(
                date_production__lte=date_fin
            )
        else:
            messages.warning(
                request,
                "La date de fin est invalide.",
            )

    if date_debut and date_fin and date_debut > date_fin:
        messages.warning(
            request,
            "La date de début ne peut pas être postérieure à la date de fin.",
        )
        miniers_queryset = miniers_queryset.none()

    miniers_queryset = miniers_queryset.order_by(
        "-date_production",
        "nom",
        "id",
    )

    # ---------------------------------------------------------
    # 6. Calcul des totaux à partir des résultats filtrés
    # ---------------------------------------------------------
    miniers = list(miniers_queryset)

    total_miniers = len(miniers)
    total_montant = Decimal("0.00")

    for minier in miniers:
        quantite = Decimal(str(minier.quantite or 0))
        prix_unitaire = Decimal(str(minier.prix_unitaire or 0))

        total_montant += quantite * prix_unitaire

    total_montant = total_montant.quantize(Decimal("0.01"))

    # ---------------------------------------------------------
    # 7. Matériaux disponibles dans le projet
    # ---------------------------------------------------------
    materiaux = MateriauProjet.objects.filter(
        projet=projet
    ).order_by("id")

    # ---------------------------------------------------------
    # 8. Contexte du template
    # ---------------------------------------------------------
    context = {
        "projet": projet,
        "miniers": miniers,
        "total_miniers": total_miniers,
        "total_montant": total_montant,
        "materiaux": materiaux,
        "nom": nom,
        "materiau": materiau,
        "date_debut": date_debut_str,
        "date_fin": date_fin_str,
        "personnel_connecte": personnel_connecte,
        "peut_gerer": peut_gerer,
    }

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

    projet = get_object_or_404(Projet, pk=projet_id)

    if request.method == "POST":

        form = MinierProjetForm(
            request.POST,
            request.FILES,
            projet=projet,
        )

        if form.is_valid():

            minier = form.save(commit=False)

            minier.projet = projet
            minier.type_class = "MINIER"
            minier.type_contrat = "PRE_PAYER"

            # ------------------------------------------------
            # Utilisateur connectÃ©
            # ------------------------------------------------

            user_id = request.session.get("user_id")

            if user_id:

                try:

                    minier.enregistre_par = Personnel.objects.get(pk=user_id)

                except Personnel.DoesNotExist:

                    minier.enregistre_par = None

            minier.save()

            messages.success(request, "Le Minier a été enregistré avec succés.")

            return redirect(
                "projet:minier_projet_list",
                projet_id=projet.pk,
            )

    else:

        form = MinierProjetForm(projet=projet)

    return render(
        request,
        "projet/miniers/form.html",
        {
            "form": form,
            "projet": projet,
            "titre": "Ajouter un Minier",
        },
    )


# ============================================================
# MINIER PROJET - MODIFICATION
# ============================================================
@project_manager_required
def minier_projet_update(request, projet_id, pk):

    projet = get_object_or_404(Projet, pk=projet_id)

    minier = get_object_or_404(
        PersonnelExecutionProjet,
        pk=pk,
        projet=projet,
        type_class="MINIER",
    )

    # --------------------------------------------------------
    # Seul le crÃ©ateur peut modifier
    # --------------------------------------------------------

    user_id = request.session.get("user_id")

    if minier.enregistre_par_id and str(minier.enregistre_par_id) != str(user_id):

        messages.error(request, "Vous n'êtes pas autorisé à modifier ce Minier.")

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

            minier = form.save(commit=False)

            minier.projet = projet
            minier.type_class = "MINIER"
            minier.type_contrat = "PRE_PAYER"

            minier.save()

            messages.success(request, "Le Minier a été modifié avec succés.")

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
        },
    )


# ============================================================
# RAPPORT PROJET - LISTE
# ============================================================
@project_access_required
def rapport_projet_list(    request,    projet_id,):

    rapports = RapportProjet.objects.filter(projet=request.projet).select_related(
        "auteur"
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

    projets = Projet.objects.all().order_by(
        "-date_debut",
        "-id",
    )

    if not user_can_manage_projects(request.current_user):

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
                Projet.objects.filter(
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
def rapport_projet_create(    request,    projet_id,):

    projet = request.projet
    user = request.current_user

    if not user_has_project_function(
        user,
        projet,
        ["INGENIEUR"],
    ):

        messages.error(
            request,
            ("Seul l'Ingénieur Responsable du Chantier " "peut créer ce rapport."),
        )

        return redirect(
            "projet:projet_detail",
            projet_id=projet.pk,
        )

    if request.method == "POST":

        form = RapportProjetForm(request.POST)

        if form.is_valid():

            rapport = form.save(commit=False)

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
def rapport_projet_update(    request,    projet_id,    rapport_id,):

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

            rapport_modifie = form.save(commit=False)

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
def rapport_travail_list(    request,    projet_id,):

    rapports = RapportTravail.objects.filter(projet=request.projet).select_related(
        "point",
        "auteur",
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
def rapport_travail_create(    request,    projet_id,):

    projet = request.projet
    user = request.current_user

    if not user_has_project_function(
        user,
        projet,
        ["CHEF_CHANTIER"],
    ):

        messages.error(
            request,
            ("Seul le Chef de Chantier peut enregistrer " "un rapport de travail."),
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

            rapport = form.save(commit=False)

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
def rapport_materiau_create(request, projet_id):
    """
    Ajout d'un rapport matériau pour un projet.
    """

    # ============================================================
    # PROJET
    # ============================================================
    projet = get_object_or_404(Projet, pk=projet_id)
    # ============================================================
    # CONTRÃ”LE D'ACCÃˆS AU PROJET
    # ============================================================
    if not user_has_project_access(request.current_user, projet):
        messages.error(request, "Votre accés  à ce projet n'est pas actif.")
        return redirect("projet:projet_list")

    # ============================================================
    # DROIT DE GESTION
    # ============================================================
    if not user_can_manage_projects(request.current_user):
        messages.error(
            request, "Vous n'avez pas l'autorisation d'ajouter un rapport matériau."
        )
        return redirect("projet:rapport_materiau_list", projet_id=projet.id)

    # ============================================================
    # FORMULAIRE
    # ============================================================
    if request.method == "POST":

        form = RapportMateriauForm(
            request.POST,
            request.FILES,
            projet=projet,
        )

        if form.is_valid():

            rapport = form.save(commit=False)

            # ----------------------------------------------------
            # PROJET
            # ----------------------------------------------------
            rapport.projet = projet

            # ----------------------------------------------------
            # ENREGISTRÃ‰ PAR
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
                request, "Le rapport matériau a été ajouté avec succés."
            )

            return redirect("projet:rapport_materiau_list", projet_id=projet.id)

    else:

        form = RapportMateriauForm(projet=projet)

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
    return render(request, "projet/rapport_materiau/form.html", context)


# ============================================================
# VEHICULES / ENGIN AFFECTÃ‰S AUX PROJETS
# CRUD COMPLET
# ============================================================
# ============================================================
# LISTE - READ
# ============================================================
@login_required_projet
def vehicule_projet_list(    request,    projet_id,):

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    # --------------------------------------------------------
    # VÃ‰RIFICATION DE L'ACCÃˆS AU PROJET
    # --------------------------------------------------------

    if not user_has_project_access(
        request.current_user,
        projet,
    ):

        messages.error(
            request,
            "Votre accÃ¨s Ã  ce projet n'est pas actif.",
        )

        return redirect("projet:projet_list")

    # --------------------------------------------------------
    # LISTE DES AFFECTATIONS
    # --------------------------------------------------------

    affectations = (
        VehiculeProjet.objects.filter(
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
        (affectation.kilometres_parcourus for affectation in affectations),
        Decimal("0.00"),
    )

    total_carburant = sum(
        (affectation.carburant_estime for affectation in affectations),
        Decimal("0.00"),
    )

    total_actifs = sum(1 for affectation in affectations if affectation.acces_actif)

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
# VEHICULE - CREATE
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

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == "POST":

        form = VehiculeProjetForm(
            request.POST,
            projet=projet,
        )

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
                    f"Le véhicule / engin  {affectation.vehicule} a été affecté au projet "
                    f"{projet.titre}."
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
            "titre_page": ("Affecter un véhicule / engin au projet"),
            "user": request.current_user,
        },
    )


# ============================================================
# MODIFIER - UPDATE
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

    # --------------------------------------------------------
    # RÃ‰CUPÃ‰RATION DE L'AFFECTATION
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
                    f"L'affectation du véhicule {affectation_modifiee.vehicule} a été modifiée avec succés."
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
            "titre_page": ("Modifier l'affectation du véhicule / engin"),
            "user": request.current_user,
        },
    )


# ============================================================
# SUPPRIMER - DELETE
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

    # --------------------------------------------------------
    # RÃ‰CUPÃ‰RATION DE L'AFFECTATION
    # --------------------------------------------------------

    affectation = get_object_or_404(
        VehiculeProjet,
        pk=vehicule_projet_id,
        projet=projet,
    )

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
                    f"L'affectation du véhicule / engin  {vehicule} a été supprimée avec succés."
                ),
            )

        except ProtectedError:

            messages.error(
                request,
                (
                    "Impossible de supprimer cette affectation car elle est utilisée par d'autres données."
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
        "La suppression doit étre confirmée par une requête POST.",
    )

    return redirect(
        "projet:vehicule_projet_list",
        projet_id=projet.pk,
    )


# ============================================================
# LISTE DES ENGINS AFFECTÃ‰S AU PROJET
# ============================================================
@login_required_projet
def engin_list(request, projet_id):
    """
    Affiche la liste des engins affectés à un projet.
    """

    # ============================================================
    # UTILISATEUR CONNECTÃ‰
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
    # VÃ‰RIFICATION DE L'ACCÃˆS AU PROJET
    # ============================================================

    if not user_has_project_access(
        current_user,
        projet,
    ):
        messages.error(
            request,
            "Votre accÃ¨s Ã  ce projet n'est pas actif.",
        )

        return redirect("projet:projet_list")

    # ============================================================
    # Ã‰QUIPE DU PROJET
    # ============================================================

    equipe = (
        projet.equipe.all()
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

            if membre.personnel_id and membre.personnel_id == personnel_connecte_id:
                if membre.acces_actif:
                    fonction_projet = membre.fonction
                    break

            # ----------------------------------------------------
            # PERSONNEL D'EXÃ‰CUTION
            # ----------------------------------------------------

            if membre.personnel_execution_id and membre.personnel_execution:

                personnel_execution = membre.personnel_execution

                if (
                    personnel_execution.personnel_id
                    and personnel_execution.personnel_id == personnel_connecte_id
                ):

                    if membre.acces_actif:
                        fonction_projet = membre.fonction
                        break

    # ============================================================
    # ENGINS DU PROJET
    # ============================================================

    engins = (
        EnginProjet.objects.filter(projet=projet)
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

    engins_actifs = [engin for engin in engins if engin.acces_actif]

    nombre_actifs = len(engins_actifs)

    total_heures = sum(
        (engin.heures_travail for engin in engins),
        Decimal("0.00"),
    )

    total_carburant = sum(
        (engin.carburant_estime for engin in engins),
        Decimal("0.00"),
    )

    # ============================================================
    # PERMISSIONS
    # ============================================================

    peut_gerer = user_can_manage_projects(current_user)

    peut_rapport_engin = fonction_projet in {
        "CHAUFFEUR",
        "CHEF_CHANTIER",
        "INGENIEUR",
    } or current_user.role in {
        "UserEntreprise",
        "Admin",
        "Superviseur",
    }

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
def engin_create(    request,    projet_id,):
    """
    Ajout d'un EnginProjet au projet.
    """

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    # ============================================================
    # ACCÃˆS
    # ============================================================

    if not user_has_project_access(
        request.current_user,
        projet,
    ):
        messages.error(
            request,
            "Votre accÃ¨s Ã  ce projet n'est pas actif.",
        )

        return redirect("projet:projet_list")

    # ============================================================
    # PERMISSION
    # ============================================================

    if not user_can_manage_projects(request.current_user):
        messages.error(
            request,
            "Vous n'avez pas l'autorisation " "d'ajouter un engin.",
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

            engin = form.save(commit=False)

            engin.projet = projet

            engin.save()

            messages.success(
                request,
                (f"L'engin {engin.engin} a été ajouté au projet."),
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
def engin_update(    request,    projet_id,    pk,):
    """
    Modification d'un EnginProjet.
    """

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    # ============================================================
    # ACCÃˆS
    # ============================================================

    if not user_has_project_access(
        request.current_user,
        projet,
    ):
        messages.error(
            request,
            "Votre accés à ce projet n'est pas actif.",
        )

        return redirect("projet:projet_list")

    # ============================================================
    # PERMISSION
    # ============================================================

    if not user_can_manage_projects(request.current_user):
        messages.error(
            request,
            "Vous n'avez pas l'autorisation " "de modifier cet engin.",
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
                (f"L'engin {engin.engin} a été modifié."),
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
def engin_delete(    request,    projet_id,    pk,):
    """
    Suppression d'un EnginProjet.
    """
    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    # ============================================================
    # ACCÃˆS
    # ============================================================

    if not user_has_project_access(
        request.current_user,
        projet,
    ):
        messages.error(
            request,
            "Votre accés à ce projet n'est pas actif.",
        )

        return redirect("projet:projet_list")

    # ============================================================
    # PERMISSION
    # ============================================================

    if not user_can_manage_projects(request.current_user):
        messages.error(
            request,
            "Vous n'avez pas l'autorisation " "de supprimer cet engin.",
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
            (f"L'engin {nom_engin} a été supprimé."),
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
# MATÃ‰RIAUX DU PROJET
# ============================================================
def _peut_modifier_mouvement_materiau(
    request,
    projet,
    mouvement,
):
    """
    Autorise la modification d'un mouvement de matériau
    uniquement à son enregistreur initial.

    Vérifie également que le mouvement appartient au projet
    demandé et que l'utilisateur est identifié.
    """
    if not request or not projet or not mouvement:
        return False

    projet_mouvement_id = getattr(
        mouvement,
        "projet_id",
        None,
    )

    if projet_mouvement_id is not None:
        if projet_mouvement_id != projet.pk:
            return False

    current_user = get_current_user(request)

    if not current_user: return False

    enregistreur_id = getattr(
        mouvement,
        "enregistre_par_id",
        None,
    )

    utilisateur_id = getattr(
        current_user,
        "pk",
        None,
    )

    return (
        enregistreur_id is not None
        and utilisateur_id is not None
        and enregistreur_id == utilisateur_id
    )


# ============================================================
# LISTE DES MATÃ‰RIAUX DU PROJET
# ============================================================
@login_required_projet
def materiau_list(request, projet_id):
    from decimal import Decimal

    from django.db.models import Q
    from django.shortcuts import get_object_or_404, redirect, render
    from django.contrib import messages

    from projet.models import (
        MateriauProjet,
        MouvementMateriauProjet,
        PointProjet,
    )

    # ========================================================
    # UTILISATEUR CONNECTÉ
    # ========================================================
    current_user = get_current_user(request)

    if not current_user:
        messages.error(
            request,
            "Utilisateur connecté introuvable.",
        )
        return redirect("users:login")

    # ========================================================
    # PROJET ET AUTORISATIONS
    # ========================================================
    projet = get_object_or_404(Projet, pk=projet_id)

    if not user_has_project_access(current_user, projet):
        messages.error(
            request,
            "Votre accès à ce projet n'est pas actif.",
        )
        return redirect("projet:projet_list")

    ZERO = Decimal("0.00")

    # ========================================================
    # IDENTIFICATION DU MAGASIN
    # ========================================================
    points = list(
        PointProjet.objects.filter(projet=projet).order_by("id")
    )

    points_magasin = [
        point
        for point in points
        if "magasin" in (point.nom or "").casefold()
    ]

    point_magasin = points_magasin[0] if points_magasin else None

    if point_magasin is None:
        messages.warning(
            request,
            "Aucun point dont le nom contient « magasin » "
            "n'a été identifié. Le stock du magasin sera affiché à zéro.",
        )

    # ========================================================
    # RECHERCHE PAR NOM DE MATÉRIAU
    # ========================================================
    recherche_materiau = request.GET.get("q", "").strip()

    materiaux_queryset = MateriauProjet.objects.filter(
        projet=projet,
    )

    if recherche_materiau:
        materiaux_queryset = materiaux_queryset.filter(
            materiau__icontains=recherche_materiau,
        )

    materiaux = list(
        materiaux_queryset.order_by("materiau", "id")
    )

    # ========================================================
    # TOTAUX GÉNÉRAUX
    # ========================================================
    total_quantite_prevue = ZERO
    total_stock_magasin = ZERO
    total_distribue = ZERO
    total_stock_global = ZERO

    # ========================================================
    # CALCUL DES STOCKS À PARTIR DES MOUVEMENTS UNIFIÉS
    # ========================================================
    for materiau in materiaux:
        mouvements = list(
            MouvementMateriauProjet.objects.filter(
                materiau_projet=materiau,
            ).select_related(
                "point_depart",
                "point_arrivee",
            )
        )

        quantite_prevue = materiau.quantite_prevue or ZERO
        stocks_points = {}

        # ----------------------------------------------------
        # Chaque mouvement transfère la quantité entre points.
        # Une entrée sans origine augmente uniquement la
        # destination. Une sortie ou un retour transfère
        # la quantité de l'origine vers la destination.
        # ----------------------------------------------------
        for mouvement in mouvements:
            quantite = mouvement.quantite or ZERO

            if mouvement.point_depart_id:
                stocks_points[mouvement.point_depart_id] = (
                    stocks_points.get(
                        mouvement.point_depart_id,
                        ZERO,
                    )
                    - quantite
                )

            if mouvement.point_arrivee_id:
                stocks_points[mouvement.point_arrivee_id] = (
                    stocks_points.get(
                        mouvement.point_arrivee_id,
                        ZERO,
                    )
                    + quantite
                )

        # ----------------------------------------------------
        # STOCK DU MAGASIN ET STOCK GLOBAL
        # ----------------------------------------------------
        if point_magasin is not None:
            stock_magasin = stocks_points.get(
                point_magasin.pk,
                ZERO,
            )
        else:
            stock_magasin = ZERO

        stock_global = sum(stocks_points.values(), ZERO)

        # ----------------------------------------------------
        # QUANTITÉ NETTE DISTRIBUÉE DEPUIS LE MAGASIN
        # Sorties du magasin moins retours vers ce magasin.
        # ----------------------------------------------------
        quantite_sortie_magasin = sum(
            (
                mouvement.quantite or ZERO
                for mouvement in mouvements
                if mouvement.type_mouvement
                == MouvementMateriauProjet.TypeMouvement.SORTIE
                and point_magasin is not None
                and mouvement.point_depart_id == point_magasin.pk
            ),
            ZERO,
        )

        quantite_retournee_magasin = sum(
            (
                mouvement.quantite or ZERO
                for mouvement in mouvements
                if mouvement.type_mouvement
                == MouvementMateriauProjet.TypeMouvement.RETOUR
                and point_magasin is not None
                and mouvement.point_arrivee_id == point_magasin.pk
            ),
            ZERO,
        )

        quantite_distribuee = (
            quantite_sortie_magasin
            - quantite_retournee_magasin
        )

        # ----------------------------------------------------
        # ATTRIBUTS ATTENDUS PAR LE TEMPLATE EXISTANT
        # ----------------------------------------------------
        materiau.quantite_prevue_affichee = quantite_prevue
        materiau.stock_magasin = stock_magasin
        materiau.total_distribue = quantite_distribuee
        materiau.stock_total = stock_global
        materiau.stock_entrepot = ZERO

        # ----------------------------------------------------
        # TOTAUX
        # ----------------------------------------------------
        total_quantite_prevue += quantite_prevue
        total_stock_magasin += stock_magasin
        total_distribue += quantite_distribuee
        total_stock_global += stock_global

    # ========================================================
    # DROITS DE GESTION
    # ========================================================
    peut_gerer = user_can_manage_materiaux(
        current_user,
        projet,
    )

    # ========================================================
    # DROITS D'AJOUT DE MATÉRIAUX
    # ========================================================
    roles_ajout_materiau = {
        "Admin",
        "ChefMagasin",
        "Magasin",
        "UserEntreprise",
    }

    role_utilisateur = getattr(
        current_user,
        "role",
        "",
    )

    peut_ajouter_materiau = (
        role_utilisateur in roles_ajout_materiau
    )

    # ========================================================
    # CONTEXTE DU TEMPLATE
    # ========================================================
    context = {
        "projet": projet,
        "materiaux": materiaux,
        "recherche_materiau": recherche_materiau,
        "total_materiaux": len(materiaux),
        "total_quantite_prevue": total_quantite_prevue,
        "total_stock_magasin": total_stock_magasin,
        "total_distribue": total_distribue,
        "total_stock_global": total_stock_global,
        "user": current_user,
        "current_user": current_user,
        "personnel": getattr(
            current_user,
            "personnel",
            None,
        ),
        "peut_gerer": peut_gerer,
        "peut_ajouter_materiau": peut_ajouter_materiau,
    }

    return render(
        request,
        "projet/materiaux/materiaux_list.html",
        context,
    )

# ============================================================
# AJOUTER UN MATERIAU AU PROJET
# ============================================================
@login_required_projet
def materiau_create(request, projet_id):
    current_user = get_current_user(request)

    # ========================================================
    # 1. VERIFICATION DE L'UTILISATEUR CONNECTE
    # ========================================================
    if not current_user:
        messages.error(
            request, "Utilisateur connecté introuvable. Veuillez vous reconnecter."
        )
        return redirect("users:login")

    # ========================================================
    # 2. RÃ‰CUPÃ‰RATION DU PROJET
    # ========================================================
    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    # ========================================================
    # 3. VERIFICATION DE L'ACCÃˆS AU PROJET
    # ========================================================
    if not user_has_project_access(current_user, projet):
        messages.error(request, "Votre accés à ce projet n'est pas actif.")
        return redirect("projet:projet_list")

    # ========================================================
    # 4. VÃ‰RIFICATION DES DROITS D'AJOUT
    # RÃ´les autorisÃ©s :
    # Admin, ChefMagasin, Magasin, UserEntreprise
    # ========================================================
    roles_autorises_ajout = {
        "Admin",
        "ChefMagasin",
        "Magasin",
        "UserEntreprise",
    }

    role_utilisateur = getattr(current_user, "role", "")

    peut_gerer = user_can_manage_materiaux(
        current_user,
        projet,
    )

    peut_ajouter = role_utilisateur in roles_autorises_ajout or peut_gerer

    if not peut_ajouter:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'ajouter un matériau à ce projet.",
        )
        return redirect(
            "projet:materiau_list",
            projet_id=projet.id,
        )

    # ========================================================
    # 5. TRAITEMENT DU FORMULAIRE
    # ========================================================
    if request.method == "POST":
        form = MateriauProjetForm(
            request.POST,
            projet=projet,
        )

        if form.is_valid():
            materiau_projet = form.save(commit=False)

            # Le projet est imposé à cette serveur.
            materiau_projet.projet = projet

            # ================================================
            # ENREGISTREMENT DE L'UTILISATEUR CONNECTÃ‰
            # ================================================
            from users.models import AppUser

            if not isinstance(current_user, AppUser):
                messages.error(
                    request,
                    "L'utilisateur connecté n'est pas un compte AppUser valide. Le matériau n'a pas été enregistré.",
                )
            else:
                materiau_projet.enregistre_par = current_user

                # Enregistrer le matÃ©riau.
                materiau_projet.save()

                messages.success(
                    request,
                    f"Le matériau {materiau_projet.materiau} a été ajouté au projet.",
                )

                return redirect(
                    "projet:materiau_list",
                    projet_id=projet.id,
                )
        else:
            messages.error(request, "Veuillez corriger les erreurs du formulaire.")

    else:
        # Affichage initial du formulaire.
        form = MateriauProjetForm(
            projet=projet,
        )

    # ========================================================
    # 6. CONTEXTE DU TEMPLATE
    # ========================================================
    context = {
        "projet": projet,
        "form": form,
        "titre": "Ajouter un matériau au projet",
        "mode": "creation",
        "user": current_user,
        "current_user": current_user,
        "personnel": getattr(
            current_user,
            "personnel",
            None,
        ),
        "peut_gerer": peut_gerer,
        "peut_ajouter": peut_ajouter,
    }

    # ========================================================
    # 7. AFFICHAGE DU FORMULAIRE
    # ========================================================
    return render(
        request,
        "projet/materiaux/materiaux_form.html",
        context,
    )


# ============================================================
# MODIFIER UN MATÃ‰RIAU
# ============================================================
def materiau_update(request, projet_id, pk):

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    materiau = get_object_or_404(
        MateriauProjet,
        pk=pk,
        projet=projet,
    )

    # RÃ©cupÃ©rer l'utilisateur de la session GALAXY.
    utilisateur = getattr(request, "current_user", None)

    if utilisateur is None:
        from users.decorators import get_current_user

        utilisateur = get_current_user(request)

    # VÃ©rifier l'enregistreur initial.
    if (
        utilisateur is None
        or materiau.enregistre_par_id is None
        or materiau.enregistre_par_id != utilisateur.pk
    ):
        messages.error(
            request,
            "Modification refusée : seul l'enregistreur initial peut modifier ce matériau.",
        )
        return redirect(
            "projet:materiau_list",
            projet_id=projet.pk,
        )

    if request.method == "POST":
        form = MateriauProjetForm(
            request.POST,
            request.FILES,
            instance=materiau,
            projet=projet,
        )

        if form.is_valid():
            objet_modifie = form.save(commit=False)

            objet_modifie.projet = projet
            objet_modifie.enregistre_par_id = materiau.enregistre_par_id

            objet_modifie.save()
            form.save_m2m()

            messages.success(
                request,
                "Matériau modifié avec succés.",
            )

            return redirect(
                "projet:materiau_list",
                projet_id=projet.pk,
            )
    else:
        form = MateriauProjetForm(
            instance=materiau,
            projet=projet,
        )

    return render(
        request,
        "projet/materiaux/materiaux_form.html",
        {
            "projet": projet,
            "form": form,
            "materiau": materiau,
            "objet": materiau,
            "mode_modification": True,
            "mode": "update",
            "titre_page": "Modifier un matériau",
            "url_retour": redirect(
                "projet:materiau_list",
                projet_id=projet.pk,
            ).url,
        },
    )


# ============================================================
# SUPPRIMER UN MATÃ‰RIAU
# ============================================================
@login_required_projet
def materiau_delete(request, projet_id, pk):
    from django.contrib import messages
    from django.shortcuts import get_object_or_404, redirect, render

    # ========================================================
    # 1. UTILISATEUR CONNECTÃ‰
    # ========================================================

    current_user = get_current_user(request)

    if not current_user:
        messages.error(
            request,
            "Utilisateur connecté introuvable.",
        )
        return redirect("users:login")

    # ========================================================
    # 2. PROJET
    # ========================================================

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    # ========================================================
    # 3. VÃ‰RIFICATION DE L'ACCÃˆS AU PROJET
    # ========================================================

    if not user_has_project_access(current_user, projet):
        messages.error(
            request,
            "Votre accées à ce projet n'est pas actif.",
        )
        return redirect("projet:projet_list")

    # ========================================================
    # 4. RÃ‰CUPÃ‰RER LE MATÃ‰RIAU DU PROJET
    # ========================================================

    materiau_projet = get_object_or_404(
        MateriauProjet.objects.select_related("projet"),
        pk=pk,
        projet=projet,
    )

    # ========================================================
    # 5. IDENTIFIER L'ENREGISTREUR DU MATÃ‰RIAU
    # ========================================================

    # Plusieurs noms possibles sont pris en charge.
    # Le premier champ existant dans le modÃ¨le est utilisÃ©.
    champs_enregistreur = (
        "enregistre_par",
        "enregistreur",
        "cree_par",
        "created_by",
    )

    champ_trouve = next(
        (
            nom
            for nom in champs_enregistreur
            if any(champ.name == nom for champ in MateriauProjet._meta.fields)
        ),
        None,
    )

    enregistreur_id = None

    if champ_trouve:
        champ = MateriauProjet._meta.get_field(champ_trouve)

        if champ.is_relation:
            enregistreur_id = getattr(
                materiau_projet,
                f"{champ_trouve}_id",
                None,
            )

    # L'utilisateur est le crÃ©ateur du matÃ©riau.
    est_enregistreur = enregistreur_id is not None and str(enregistreur_id) == str(
        current_user.pk
    )

    # ========================================================
    # 6. AUTORISATION
    # ========================================================

    # Les utilisateurs dÃ©jÃ  autorisÃ©s par la rÃ¨gle mÃ©tier
    # conservent leurs droits.
    # Le crÃ©ateur peut Ã©galement supprimer son propre matÃ©riau.
    peut_gerer = user_can_manage_materiaux(current_user, projet) or est_enregistreur

    if not peut_gerer:
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de supprimer " "ce matériau de ce projet.",
        )
        return redirect(
            "projet:materiau_list",
            projet_id=projet.id,
        )

        # ========================================================
    # 7. SUPPRESSION DU STOCK ET DE SES MOUVEMENTS
    # ========================================================

    if request.method == "POST":
        from django.db import transaction
        from django.contrib import messages
        from django.db.models import ProtectedError

        nom_materiau = str(materiau_projet.materiau)

        try:
            with transaction.atomic():

                # Supprimer les distributions liées au stock.
                DistributionMateriauProjet.objects.filter(
                    materiau_projet=materiau_projet
                ).delete()

                # Supprimer les réceptions liées au stock.
                ReceptionMateriauProjet.objects.filter(
                    materiau_projet=materiau_projet
                ).delete()

                # Supprimer le stock du projet.
                materiau_projet.delete()

            messages.success(
                request,
                f"Le stock « {nom_materiau} » et ses mouvements "
                "associés ont été supprimés définitivement.",
            )

        except ProtectedError:
            messages.error(
                request,
                "Suppression impossible : d'autres enregistrements "
                "protègent encore ce stock.",
            )

        return redirect(
            "projet:materiau_list",
            projet_id=projet.id,
        )

    # ========================================================
    # 8. CONFIRMATION
    # ========================================================

    context = {
        "projet": projet,
        "materiau_projet": materiau_projet,
        "user": current_user,
        "current_user": current_user,
        "personnel": getattr(current_user, "personnel", None),
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
@project_manager_required
def minier_list(
    request,
    projet_id,
):
    """
    Liste les miniers affectÃ©s au projet.
    """

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    # --------------------------------------------------------
    # CONTRÃ”LE D'ACCÃˆS AU PROJET
    # --------------------------------------------------------

    if not user_has_project_access(
        request.current_user,
        projet,
    ):
        messages.error(
            request,
            "Votre accÃ¨s Ã  ce projet n'est pas actif.",
        )

        return redirect("projet:projet_list")

    # --------------------------------------------------------
    # MINERS
    # --------------------------------------------------------

    miniers = (
        PersonnelExecutionProjet.objects.filter(
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

    nombre_actifs = sum(1 for minier in miniers if minier.acces_actif)

    # --------------------------------------------------------
    # TOTAL PRODUCTION
    #
    # Pour un MINIER :
    # quantitÃ© Ã— prix unitaire
    # --------------------------------------------------------

    total_production = sum(
        (minier.montant_total_production for minier in miniers),
        Decimal("0.00"),
    )

    context = {
        "projet": projet,
        "miniers": miniers,
        "total_miniers": total_miniers,
        "nombre_actifs": nombre_actifs,
        "total_production": total_production,
        "total_montant": total_production,
        "peut_gerer": (user_can_manage_projects(request.current_user)),
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

    Autorisée à ajouter :
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
    # VÃ‰RIFICATION ACCÃˆS AU PROJET
    # ============================================================

    if not user_has_project_access(
        current_user,
        projet,
    ):
        messages.error(
            request,
            "Votre accées à ce projet n'est pas actif.",
        )
        return redirect("projet:projet_list")

    # ============================================================
    # VÃ‰RIFICATION DROIT D'AJOUT D'UN MINIER
    # ============================================================

    if not user_can_manage_materiaux(
        current_user,
        projet,
    ):
        messages.error(
            request,
            "Vous n'avez pas l'autorisation d'ajouter un minier sur ce projet.",
        )
        return redirect(
            "projet:minier_list",
            projet_id=projet.id,
        )

    # ============================================================
    # PERSONNEL CONNECTÃ‰
    # ============================================================

    personnel_connecte = getattr(
        current_user,
        "personnel",
        None,
    )

    if not personnel_connecte:
        messages.error(
            request,
            "Aucun personnel n'est associé à votre compte utilisateur.",
        )
        return redirect(
            "projet:minier_list",
            projet_id=projet.id,
        )

    # ============================================================
    # TRAITEMENT POST
    # ============================================================

    if request.method == "POST":

        form = MinierProjetForm(request.POST,request.FILES,projet=projet,)

        # --------------------------------------------------------
        # VALIDATION DU FORMULAIRE
        # --------------------------------------------------------

        if form.is_valid():

            minier = form.save(commit=False)
            minier.projet = projet
            minier.personnel = None

            minier.type_class = "MINIER"
            minier.point_projet = None

            
            minier.montant = Decimal("0.00")

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
                f"Le minier {minier.nom.upper()} a été ajouté avec succés.",
            )

            # ----------------------------------------------------
            # RETOUR Ã€ LA LISTE
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
        # L'utilisateur a dÃ©jÃ  Ã©tÃ© autorisÃ©
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
def minier_update(request,projet_id,pk,):
    """
    Modifie un minier existant.
    """

    current_user = request.current_user

    # --------------------------------------------------------
    # PROJET
    # --------------------------------------------------------

    projet = get_object_or_404(Projet,pk=projet_id,)

    # --------------------------------------------------------
    # ACCÃˆS AU PROJET
    # --------------------------------------------------------

    if not user_has_project_access(
        current_user,
        projet,
    ):
        messages.error(
            request,
            "Votre accés à ce projet n'est pas actif.",
        )

        return redirect("projet:projet_list")

    # --------------------------------------------------------
    # PERSONNEL CONNECTÃ‰
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
        PersonnelExecutionProjet.objects.select_related(
            "projet",
            "materiau_projet",
            "enregistre_par",
        ),
        pk=pk,
        projet=projet,
        type_class="MINIER",
    )

    # --------------------------------------------------------
    # CONTRÃ”LE DE L'ENREGISTREUR
    # --------------------------------------------------------
    #
    # Seul celui qui a crÃ©Ã© l'enregistrement peut modifier.
    # --------------------------------------------------------

    if (
        not minier.enregistre_par_id
        or minier.enregistre_par_id != personnel_connecte.pk
    ):
        messages.error(
            request,
            "Vous ne pouvez pas modifier ce minier. Seul l'utilisateur qui l'a enregistré "
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

            minier = form.save(commit=False)

            # ------------------------------------------------
            # VALEURS IMPOSÃ‰ES
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
                (f"Le minier {minier.nom} a été modifié avec succés."),
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
def minier_delete(request, projet_id, pk):
    """
    Supprime un minier du projet.

    Seul le personnel ayant enregistré le minier peut le supprimer.
    Les affectations inutilisées sont supprimées avec le minier.
    Les données historiques protégées sont conservées.
    """

    current_user = request.current_user

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    # --------------------------------------------------------
    # CONTRÃ”LE D'ACCÃˆS AU PROJET
    # --------------------------------------------------------

    if not user_has_project_access(current_user, projet):
        messages.error(
            request,
            "Votre accÃ¨s Ã  ce projet n'est pas actif.",
        )
        return redirect("projet:projet_list")

    # --------------------------------------------------------
    # PERSONNEL CONNECTÃ‰
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
            projet_id=projet.pk,
        )

    # --------------------------------------------------------
    # MINIER
    # --------------------------------------------------------

    minier = get_object_or_404(
        PersonnelExecutionProjet.objects.select_related(
            "projet",
            "materiau_projet",
            "enregistre_par",
        ),
        pk=pk,
        projet=projet,
        type_class="MINIER",
    )

    # --------------------------------------------------------
    # VÃ‰RIFICATION DU CRÃ‰ATEUR
    # --------------------------------------------------------

    if (
        not minier.enregistre_par_id
        or minier.enregistre_par_id != personnel_connecte.pk
    ):
        messages.error(
            request,
            "Vous ne pouvez pas supprimer ce minier. "
            "Seul le personnel qui l'a enregistrÃ© "
            "peut le supprimer.",
        )
        return redirect(
            "projet:minier_list",
            projet_id=projet.pk,
        )

    # --------------------------------------------------------
    # PAGE DE CONFIRMATION
    # --------------------------------------------------------

    if request.method != "POST":
        return render(
            request,
            "projet/minier_delete.html",
            {
                "projet": projet,
                "minier": minier,
                "user": current_user,
                "current_user": current_user,
                "personnel": personnel_connecte,
            },
        )

    nom_minier = minier.nom

    # --------------------------------------------------------
    # SUPPRESSION ATOMIQUE
    # --------------------------------------------------------

    try:
        with transaction.atomic():

            # Recharger le minier pour Ã©viter de travailler
            # sur une instance devenue obsolÃ¨te.
            minier = PersonnelExecutionProjet.objects.select_for_update().get(
                pk=pk,
                projet=projet,
                type_class="MINIER",
            )

            # VÃ©rifier Ã  nouveau le crÃ©ateur.
            if (
                not minier.enregistre_par_id
                or minier.enregistre_par_id != personnel_connecte.pk
            ):
                messages.error(
                    request,
                    "Vous n'Ãªtes plus autorisÃ© Ã  supprimer " "ce minier.",
                )
                return redirect(
                    "projet:minier_list",
                    projet_id=projet.pk,
                )

            # RÃ©cupÃ©rer les affectations du minier.
            affectations = list(
                EquipeProjet.objects.select_for_update().filter(
                    personnel_execution=minier,
                    projet=projet,
                )
            )

            # Ne jamais supprimer une affectation
            # qui possÃ¨de des avances.
            for affectation in affectations:
                if (
                    affectation.avances_equipe.exists()
                    or affectation.avances_miniers.exists()
                ):
                    messages.error(
                        request,
                        "Impossible de supprimer ce minier : "
                        "une affectation possÃ¨de des avances. "
                        "Les donnÃ©es existantes ont Ã©tÃ© conservÃ©es.",
                    )
                    return redirect(
                        "projet:minier_list",
                        projet_id=projet.pk,
                    )

            # Supprimer les affectations inutilisÃ©es.
            for affectation in affectations:
                affectation.delete()

            # Supprimer ensuite le minier.
            # Si une autre relation protÃ©gÃ©e existe,
            # ProtectedError annulera toute la transaction.
            minier.delete()

        messages.success(
            request,
            f"Le minier {nom_minier} et ses affectations inutilisées ont été supprimés.",
        )

    except ProtectedError:
        messages.error(
            request,
            "Impossible de supprimer ce minier : "
            "d'autres données du projet utilisent encore ce minier. Aucune suppression partielle n'a été conservée.",
        )

    except PersonnelExecutionProjet.DoesNotExist:
        messages.error(
            request,
            "Ce minier n'existe plus ou a déjà été supprimé.",
        )

    return redirect(
        "projet:minier_list",
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

    rapports = RapportVehicule.objects.filter(projet=request.projet).select_related(
        "vehicule",
        "chauffeur",
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

            vehicule = form.cleaned_data.get("vehicule")

            chauffeur = form.cleaned_data.get("chauffeur")

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

                rapport = form.save(commit=False)

                rapport.projet_id = projet.pk
                rapport.vehicule_id = vehicule.pk
                rapport.chauffeur_id = chauffeur.pk

                rapport.save()

                messages.success(
                    request,
                    "Rapport véhicule enregistré avec succés.",
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

    projets = Projet.objects.all().order_by(
        "-date_debut",
        "-id",
    )

    if not user_can_manage_projects(request.current_user):

        messages.error(
            request,
            "Vous n'avez pas l'autorisation de gérer les équipes.",
        )

        return redirect("projet:projet_list")

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
        ActiviteTransportProjet.objects.filter(projet=projet)
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
        (activite.kilometres_parcourus for activite in activites),
        Decimal("0.00"),
    )

    total_carburant = sum(
        (activite.carburant_estime for activite in activites),
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

            activite = form.save(commit=False)

            activite.projet = projet
            activite.enregistre_par = request.current_user

            activite.save()

            messages.success(
                request,
                ("L'activité de transport " "a été enregistrée avec succés."),
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
            ("Vous n'étes pas autorisé à modifier " "cette activitÃ©."),
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

            activite_modifiee = form.save(commit=False)

            activite_modifiee.projet = projet
            activite_modifiee.enregistre_par_id = activite.enregistre_par_id

            activite_modifiee.save()

            messages.success(
                request,
                ("L'activité de transport " "a été modifiée avec succés."),
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
            "titre_page": ("Modifier l'activitÃ© de transport"),
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
            ("Vous n'êtes pas autorisé à supprimer " "cette activité."),
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
                ("L'activité de transport " "a été supprimée avec succés."),
            )

        except ProtectedError:

            messages.error(
                request,
                (
                    "Impossible de supprimer cette activité car elle est utilisée par d'autres données."
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
# OUTILS - MOUVEMENT VÃ‰HICULE / ENGIN
# ============================================================
def _mouvement_est_createur(mouvement, user):
    """VÃ©rifie si l'utilisateur connecté est le créateur."""
    return user is not None and mouvement.enregistre_par_id == getattr(user, "pk", None)


def _mouvement_peut_gerer(mouvement, user):
    """CrÃ©ateur ou administrateur."""
    if _mouvement_est_createur(mouvement, user):
        return True

    role = getattr(user, "role", "") if user else ""
    return role in ("Admin", "SuperAdmin")


# ============================================================
# MOUVEMENTS - LISTE ET BILAN DU PROJET
# ============================================================
@project_access_required
def mouvement_vehicule_projet_list(request, projet_id):
    projet = request.projet
    user = request.current_user

    vehicules_projet = VehiculeProjet.objects.filter(
        projet=projet,
    ).order_by("vehicule")

    engins_projet = EnginProjet.objects.filter(
        projet=projet,
    ).order_by("engin")

    mouvements_qs = (
        MouvementVehiculeProjet.objects.filter(
            Q(vehicule_projet__projet=projet) | Q(engin_projet__projet=projet)
        )
        .select_related(
            "vehicule_projet",
            "vehicule_projet__projet",
            "engin_projet",
            "engin_projet__projet",
            "point_depart",
            "point_arrivee",
            "enregistre_par",
        )
        .order_by("-date_mouvement", "-id")
    )

    
    # --------------------------------------------------------
    # FILTRES
    # --------------------------------------------------------

    type_filtre = request.GET.get("type", "").strip().upper()
    materiel_filtre = request.GET.get("materiel", "").strip()

    if type_filtre not in ("ROUTIER", "ENGIN"):
        type_filtre = ""

    if type_filtre == "ROUTIER":
        mouvements_qs = mouvements_qs.filter(
            vehicule_projet__isnull=False,
            engin_projet__isnull=True,
        )
    elif type_filtre == "ENGIN":
        mouvements_qs = mouvements_qs.filter(
            engin_projet__isnull=False,
            vehicule_projet__isnull=True,
        )

    # Le format du filtre est : vehicule-12 ou engin-3.
    if materiel_filtre:
        try:
            categorie_materiel, identifiant = materiel_filtre.split("-", 1)
        except ValueError:
            categorie_materiel, identifiant = "", ""

        if (
            categorie_materiel not in ("vehicule", "engin")
            or not identifiant.isdigit()
        ):
            materiel_filtre = ""
        else:
            materiel_id = int(identifiant)

            if categorie_materiel == "vehicule":
                mouvements_qs = mouvements_qs.filter(
                    vehicule_projet_id=materiel_id,
                    engin_projet__isnull=True,
                )
                if type_filtre == "ENGIN":
                    mouvements_qs = mouvements_qs.none()

            elif categorie_materiel == "engin":
                mouvements_qs = mouvements_qs.filter(
                    engin_projet_id=materiel_id,
                    vehicule_projet__isnull=True,
                )
                if type_filtre == "ROUTIER":
                    mouvements_qs = mouvements_qs.none()

    mouvements = list(mouvements_qs)


    # --------------------------------------------------------
    # STATISTIQUES DES MOUVEMENTS AFFICHÃ‰S
    # --------------------------------------------------------

    total_km = sum(
        (
            mouvement.kilometres_parcourus
            for mouvement in mouvements
            if mouvement.vehicule_projet_id is not None
        ),
        Decimal("0.00"),
    )

    total_heures_moteur = sum(
        (
            mouvement.heures_travail
            for mouvement in mouvements
            if mouvement.engin_projet_id is not None
        ),
        Decimal("0.00"),
    )

    total_carburant = sum(
        (mouvement.carburant_litre for mouvement in mouvements),
        Decimal("0.00"),
    )

    total_duree_minutes = sum(
        (mouvement.duree_minutes for mouvement in mouvements),
        0,
    )

    total_duree_heures, total_duree_reste = divmod(
        total_duree_minutes,
        60,
    )

    # --------------------------------------------------------
    # AUTORISATIONS D'ACTION
    # --------------------------------------------------------

    mouvements_gerables = {
        mouvement.pk: _mouvement_peut_gerer(mouvement, user) for mouvement in mouvements
    }

    context = {
        "projet": projet,
        "user": user,
        "vehicules_projet": vehicules_projet,
        "engins_projet": engins_projet,
        "type_filtre": type_filtre,
        "materiel_filtre": materiel_filtre,
        "mouvements": mouvements,
        "mouvements_gerables": mouvements_gerables,
        "total_km": total_km,
        "total_heures_moteur": total_heures_moteur,
        "total_carburant": total_carburant,
        "total_duree_minutes": total_duree_minutes,
        "total_duree_heures": total_duree_heures,
        "total_duree_reste": total_duree_reste,
    }

    return render(
        request,
        "projet/mouvement_vehicule_projet_list.html",
        context,
    )


# ============================================================
# MOUVEMENTS - DÃ‰TAIL
# ============================================================
@project_access_required
def mouvement_vehicule_projet_detail(
    request,
    projet_id,
    mouvement_id,
):
    projet = request.projet

    mouvement = get_object_or_404(
        MouvementVehiculeProjet.objects.select_related(
            "vehicule_projet",
            "vehicule_projet__projet",
            "engin_projet",
            "engin_projet__projet",
            "point_depart",
            "point_arrivee",
            "enregistre_par",
        ).filter(pk=mouvement_id),
    )

    # VÃ©rifier que le mouvement appartient au projet.
    appartient_au_projet = (
        mouvement.vehicule_projet is not None
        and mouvement.vehicule_projet.projet_id == projet.pk
    ) or (
        mouvement.engin_projet is not None
        and mouvement.engin_projet.projet_id == projet.pk
    )

    if not appartient_au_projet:
        raise PermissionDenied("Ce mouvement n'appartient pas à ce projet.")

    return render(
        request,
        "projet/mouvement_vehicule_projet_detail.html",
        {
            "projet": projet,
            "mouvement": mouvement,
            "user": request.current_user,
            "peut_modifier": _mouvement_peut_gerer(
                mouvement,
                request.current_user,
            ),
        },
    )


# ============================================================
# MOUVEMENTS - CRÃ‰ER
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

            # Un mouvement doit concerner un vÃ©hicule OU un engin
            # appartenant au projet courant.
            vehicule = mouvement.vehicule_projet
            engin = mouvement.engin_projet

            if bool(vehicule) == bool(engin):
                form.add_error(
                    None,
                    "Sélectionnez un seul véhicule ou un seul engin.",
                )
            elif vehicule and vehicule.projet_id != projet.pk:
                raise PermissionDenied("Ce véhicule n'appartient pas à ce projet.")
            elif engin and engin.projet_id != projet.pk:
                raise PermissionDenied("Cet engin n'appartient pas à ce projet.")
            else:
                mouvement.enregistre_par = user
                mouvement.save()

                messages.success(
                    request,
                    "Le rapport d'activitÃ© a été enregistrÃ© avec succés.",
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
            "titre_page": "Nouveau rapport d'activitÃ©",
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
        MouvementVehiculeProjet.objects.select_related(
            "vehicule_projet",
            "engin_projet",
        ),
        pk=mouvement_id,
    )

    appartient_au_projet = (
        mouvement.vehicule_projet is not None
        and mouvement.vehicule_projet.projet_id == projet.pk
    ) or (
        mouvement.engin_projet is not None
        and mouvement.engin_projet.projet_id == projet.pk
    )

    if not appartient_au_projet:
        raise PermissionDenied("Ce mouvement n'appartient pas à ce projet.")

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

            vehicule = mouvement_modifie.vehicule_projet
            engin = mouvement_modifie.engin_projet

            if bool(vehicule) == bool(engin):
                form.add_error(
                    None,
                    "Sélectionnez un seul véhicule ou un seul engin.",
                )
            elif vehicule and vehicule.projet_id != projet.pk:
                raise PermissionDenied("Ce véhicule n'appartient pas à ce projet.")
            elif engin and engin.projet_id != projet.pk:
                raise PermissionDenied("Cet engin n'appartient pas à ce projet.")
            else:
                # Conserver le crÃ©ateur initial.
                mouvement_modifie.enregistre_par = mouvement.enregistre_par
                mouvement_modifie.save()

                messages.success(
                    request,
                    "Le rapport d'activité a été modifié avec succés.",
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
            "titre_page": "Modifier le rapport d'activitÃ©",
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
        MouvementVehiculeProjet.objects.select_related(
            "vehicule_projet",
            "engin_projet",
        ),
        pk=mouvement_id,
    )

    appartient_au_projet = (
        mouvement.vehicule_projet is not None
        and mouvement.vehicule_projet.projet_id == projet.pk
    ) or (
        mouvement.engin_projet is not None
        and mouvement.engin_projet.projet_id == projet.pk
    )

    if not appartient_au_projet:
        raise PermissionDenied("Ce mouvement n'appartient pas à ce projet.")

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
            "Le rapport d'activité a été supprimé avec succés.",
        )
    except Exception:
        messages.error(
            request,
            "Impossible de supprimer ce mouvement. Vérifiez s'il est utilisÃ© par d'autres données.",
        )

    return redirect(
        "projet:mouvement_vehicule_projet_list",
        projet_id=projet.pk,
    )


# ================================================
# AVANCE
# ================================================
def _avances_du_projet(projet):
    """
    Retourne uniquement les avances rattachées à ce projet
    via leur équipe d'exécution ou leur équipe de miniers.
    """
    return (
        AvanceEquipeProjet.objects.filter(
            Q(equipe_execution__projet=projet) | Q(miniers_execution__projet=projet)
        )
        .select_related(
            "equipe_execution",
            "miniers_execution",
            "enregistre_par",
        )
        .distinct()
    )


def _peut_gerer_avance(request, avance):
    """
    L'auteur peut modifier ou supprimer son avance.
    Admin et Superviseur disposent également de ce droit.
    """
    role = request.session.get("role")
    user_id = request.session.get("user_id")

    return role in ("Admin", "Superviseur") or (
        user_id is not None and avance.enregistre_par_id == user_id
    )


def calculer_situation_avance_equipe(avance):
    from decimal import Decimal

    from django.db.models import Sum

    ZERO = Decimal("0.00")

    equipe = avance.equipe_execution or avance.miniers_execution

    if not equipe or not equipe.personnel_execution_id:
        return {
            "montant_contrat": ZERO,
            "montant_avance": avance.montant or ZERO,
            "total_avances": ZERO,
            "reste_a_payer": ZERO,
        }

    execution = equipe.personnel_execution

    inscriptions = PersonnelExecutionProjet.objects.filter(
        projet_id=equipe.projet_id,
        type_class=execution.type_class,
        nom__iexact=execution.nom.strip(),
    )

    if execution.type_class == "CHEF_EQUIPE":
        inscriptions = inscriptions.filter(
            point_projet_id=execution.point_projet_id,
        )
    elif execution.type_class == "MINIER":
        inscriptions = inscriptions.filter(
            materiau_projet_id=execution.materiau_projet_id,
        )

    total_contrat = ZERO

    for inscription in inscriptions:
        if inscription.type_class == "MINIER":
            total_contrat += inscription.montant_total_production or ZERO
        else:
            total_contrat += inscription.montant or ZERO

    equipes = EquipeProjet.objects.filter(
        projet_id=equipe.projet_id,
        personnel_execution__in=inscriptions,
    )

    if execution.type_class == "MINIER":
        avances_beneficiaire = AvanceEquipeProjet.objects.filter(
            miniers_execution__in=equipes,
        )
    else:
        avances_beneficiaire = AvanceEquipeProjet.objects.filter(
            equipe_execution__in=equipes,
        )

    total_avances = (
        avances_beneficiaire.aggregate(total=Sum("montant"))["total"] or ZERO
    )

    return {
        "montant_contrat": total_contrat,
        "montant_avance": avance.montant or ZERO,
        "total_avances": total_avances,
        "reste_a_payer": total_contrat - total_avances,
    }


@project_access_required
def avance_equipe_projet_list(request, projet_id):
    from datetime import datetime
    from decimal import Decimal

    from django.contrib import messages
    from django.db.models import Q

    projet = get_object_or_404(Projet, pk=projet_id)

    synchroniser_affectations_equipe(projet)

    avances = _avances_du_projet(projet)

    # --------------------------------------------------------
    # FILTRE PAR NOM
    # --------------------------------------------------------
    filtre_nom = request.GET.get("nom", "").strip()

    if filtre_nom:
        avances = avances.filter(
            Q(equipe_execution__personnel_execution__nom__icontains=filtre_nom)
            | Q(miniers_execution__personnel_execution__nom__icontains=filtre_nom)
            | Q(equipe_execution__personnel__nom__icontains=filtre_nom)
            | Q(miniers_execution__personnel__nom__icontains=filtre_nom)
        )

    # --------------------------------------------------------
    # FILTRE PAR DATE
    # date_avance est un DateTimeField.
    # --------------------------------------------------------
    filtre_date_debut = request.GET.get("date_debut", "").strip()
    filtre_date_fin = request.GET.get("date_fin", "").strip()

    if filtre_date_debut:
        try:
            date_debut = datetime.strptime(filtre_date_debut, "%Y-%m-%d").date()

            avances = avances.filter(date_avance__date__gte=date_debut)
        except ValueError:
            filtre_date_debut = ""

    if filtre_date_fin:
        try:
            date_fin = datetime.strptime(filtre_date_fin, "%Y-%m-%d").date()

            avances = avances.filter(date_avance__date__lte=date_fin)
        except ValueError:
            filtre_date_fin = ""

    # --------------------------------------------------------
    # TRI
    # --------------------------------------------------------
    avances = avances.select_related(
        "equipe_execution",
        "equipe_execution__personnel_execution",
        "equipe_execution__personnel",
        "miniers_execution",
        "miniers_execution__personnel_execution",
        "miniers_execution__personnel",
        "enregistre_par",
    ).order_by("-date_avance", "-id")

    # --------------------------------------------------------
    # CALCUL DE CHAQUE LIGNE
    # --------------------------------------------------------
    avances_liste = list(avances)

    for avance in avances_liste:
        avance.situation = calculer_situation_avance_equipe(avance)

        equipe = avance.equipe_execution or avance.miniers_execution

        if equipe and equipe.personnel_execution_id:
            execution = equipe.personnel_execution
            avance.beneficiaire_nom = execution.nom

            if execution.type_class == "MINIER":
                avance.beneficiaire_type = "Minier"
            elif execution.type_class == "CHEF_EQUIPE":
                avance.beneficiaire_type = "Chef d'Ã©quipe"
            else:
                avance.beneficiaire_type = execution.get_type_class_display()
        elif equipe and equipe.personnel_id:
            avance.beneficiaire_nom = str(equipe.personnel)
            avance.beneficiaire_type = equipe.get_fonction_display()
        else:
            avance.beneficiaire_nom = "BÃ©nÃ©ficiaire non dÃ©fini"
            avance.beneficiaire_type = ""

    # --------------------------------------------------------
    # TOTAL DE LA PAGE : AVANCES AFFICHÃ‰ES UNIQUEMENT
    # --------------------------------------------------------
    total_montant = sum(
        (avance.montant or Decimal("0.00") for avance in avances_liste),
        Decimal("0.00"),
    )

    role = request.session.get("role")
    peut_gerer = role in ("Admin", "Superviseur")

    return render(
        request,
        "projet/avance/list.html",
        {
            "projet": projet,
            "avances": avances_liste,
            "filtre_nom": filtre_nom,
            "filtre_date_debut": filtre_date_debut,
            "filtre_date_fin": filtre_date_fin,
            "total_montant": total_montant,
            "peut_gerer": peut_gerer,
        },
    )


@project_access_required
def avance_equipe_projet_create(request, projet_id):
    projet = get_object_or_404(Projet, pk=projet_id)

    # Actualiser automatiquement les bÃ©nÃ©ficiaires disponibles.
    synchroniser_affectations_equipe(projet)

    if request.method == "POST":
        form = AvanceEquipeProjetForm(
            request.POST,
            projet=projet,
        )

        if form.is_valid():
            avance = form.save(commit=False)

            user_id = request.session.get("user_id")
            avance.enregistre_par_id = user_id
            avance.save()

            messages.success(
                request,
                "L'avance d'Ã©quipe a Ã©tÃ© enregistrÃ©e avec succÃ¨s.",
            )

            return redirect(
                "projet:avance_equipe_projet_list",
                projet_id=projet.pk,
            )
    else:
        form = AvanceEquipeProjetForm(projet=projet)

    return render(
        request,
        "projet/avance/form.html",
        {
            "projet": projet,
            "form": form,
            "titre": "Nouvelle avance d'Ã©quipe",
            "bouton": "Enregistrer",
        },
    )


# ============================================================
# AVANCE Ã‰QUIPE PROJET - MODIFICATION
# ============================================================


@project_access_required
def avance_equipe_projet_update(request, projet_id, avance_id):
    projet = get_object_or_404(Projet, pk=projet_id)

    # Synchronisation des affectations du projet
    synchroniser_affectations_equipe(projet)

    avance = get_object_or_404(
        _avances_du_projet(projet),
        pk=avance_id,
    )

    if not _peut_gerer_avance(request, avance):
        messages.error(
            request,
            "Vous n'Ãªtes pas autorisÃ© Ã  modifier cette avance.",
        )
        return redirect(
            "projet:avance_equipe_projet_list",
            projet_id=projet.pk,
        )

    if request.method == "POST":
        form = AvanceEquipeProjetForm(
            request.POST,
            instance=avance,
            projet=projet,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "L'avance d'Ã©quipe a Ã©tÃ© modifiÃ©e avec succÃ¨s.",
            )

            # Retour Ã  la liste : aucune page de dÃ©tail
            return redirect(
                "projet:avance_equipe_projet_list",
                projet_id=projet.pk,
            )
    else:
        form = AvanceEquipeProjetForm(
            instance=avance,
            projet=projet,
        )

    return render(
        request,
        "projet/avance/form.html",
        {
            "projet": projet,
            "avance": avance,
            "form": form,
            "titre": "Modifier l'avance d'Ã©quipe",
            "bouton": "Enregistrer les modifications",
        },
    )


# ============================================================
# AVANCE Ã‰QUIPE PROJET - SUPPRESSION
# ============================================================
@project_access_required
def avance_equipe_projet_delete(request, projet_id, avance_id):
    projet = get_object_or_404(Projet, pk=projet_id)

    avance = get_object_or_404(
        _avances_du_projet(projet),
        pk=avance_id,
    )

    if not _peut_gerer_avance(request, avance):
        messages.error(
            request,
            "Vous n'Ãªtes pas autorisÃ© Ã  supprimer cette avance.",
        )
        return redirect(
            "projet:avance_equipe_projet_list",
            projet_id=projet.pk,
        )

    if request.method == "POST":
        avance.delete()

        messages.success(
            request,
            "L'avance d'Ã©quipe a Ã©tÃ© supprimÃ©e avec succÃ¨s.",
        )

        return redirect(
            "projet:avance_equipe_projet_list",
            projet_id=projet.pk,
        )

    return render(
        request,
        "projet/avance_equipe_projet_delete.html",
        {
            "projet": projet,
            "avance": avance,
        },
    )




# ============================================================
# TABLEAU DE BORD DES MATÉRIAUX DU PROJET
# ============================================================
@project_access_required
def dashboard_materiaux(request, projet_id):
    from decimal import Decimal

    from django.db.models import Q
    from django.shortcuts import render

    projet = request.projet
    ZERO = Decimal("0.00")

    # ==========================================================
    # 1. MATÉRIAUX ET MOUVEMENTS UNIFIÉS
    # ==========================================================
    materiaux = list(
        MateriauProjet.objects.filter(projet=projet).order_by(
            "materiau",
            "id",
        )
    )

    mouvements = (
        MouvementMateriauProjet.objects.filter(
            materiau_projet__projet=projet,
        )
        .select_related(
            "materiau_projet",
            "point_depart",
            "point_arrivee",
            "enregistre_par",
        )
        .order_by("-date_mouvement", "-id")
    )

    mouvements_par_materiau = {}

    for mouvement in mouvements:
        mouvements_par_materiau.setdefault(
            mouvement.materiau_projet_id,
            [],
        ).append(mouvement)

    materiaux_stats = []
    stocks_par_point_dict = {}

    # ==========================================================
    # 2. TOTAUX GÉNÉRAUX
    # ==========================================================
    total_prevu = ZERO
    total_recu = ZERO
    total_sorti_depot = ZERO
    total_utilise = ZERO
    total_retourne = ZERO
    total_solde_global = ZERO

    total_montant_prevu = ZERO
    total_montant_entrees = ZERO
    total_montant_sorties = ZERO
    total_montant_utilise = ZERO
    total_montant_retourne = ZERO
    total_valeur_stock = ZERO

    # ==========================================================
    # 3. CALCUL PAR MATÉRIAU
    # ==========================================================
    for materiau in materiaux:
        mouvements_materiau = mouvements_par_materiau.get(
            materiau.pk,
            [],
        )

        quantite_prevue = materiau.quantite_prevue or ZERO

        entrees = [
            mouvement
            for mouvement in mouvements_materiau
            if mouvement.type_mouvement == "ENTREE"
        ]

        sorties = [
            mouvement
            for mouvement in mouvements_materiau
            if mouvement.type_mouvement == "SORTIE"
        ]

        retours = [
            mouvement
            for mouvement in mouvements_materiau
            if mouvement.type_mouvement == "RETOUR"
        ]

        # ------------------------------------------------------
        # ENTRÉES ET PRIX MOYEN PONDÉRÉ
        # ------------------------------------------------------
        quantite_recue = sum(
            (m.quantite or ZERO for m in entrees),
            ZERO,
        )

        montant_entrees = sum(
            (
                (m.quantite or ZERO)
                * (m.prix_unitaire or ZERO)
                for m in entrees
            ),
            ZERO,
        )

        prix_moyen = (
            montant_entrees / quantite_recue
            if quantite_recue > ZERO
            else ZERO
        )

        # ------------------------------------------------------
        # SORTIES ET RETOURS
        # ------------------------------------------------------
        quantite_sortie = sum(
            (m.quantite or ZERO for m in sorties),
            ZERO,
        )

        quantite_retournee = sum(
            (m.quantite or ZERO for m in retours),
            ZERO,
        )

        # IMPORTANT :
        # SORTIE et RETOUR sont des mouvements entre points.
        # Sans type CONSOMMATION, on ne peut pas affirmer
        # qu'une sortie correspond à une consommation réelle.
        quantite_utilisee = ZERO

        montant_sorties = quantite_sortie * prix_moyen
        montant_utilise = ZERO
        montant_retourne = quantite_retournee * prix_moyen

        # ------------------------------------------------------
        # STOCK PHYSIQUE PAR POINT
        # Stock = entrées au point - sorties du point.
        # Les transferts entre points s'annulent au niveau global.
        # ------------------------------------------------------
        points_concernes = {}

        for mouvement in mouvements_materiau:
            if mouvement.point_depart_id:
                points_concernes[mouvement.point_depart_id] = (
                    mouvement.point_depart
                )

            if mouvement.point_arrivee_id:
                points_concernes[mouvement.point_arrivee_id] = (
                    mouvement.point_arrivee
                )

        stock_materiau_total = ZERO

        for point_id, point in points_concernes.items():
            quantite_entree_point = sum(
                (
                    (m.quantite or ZERO)
                    for m in mouvements_materiau
                    if m.point_arrivee_id == point_id
                ),
                ZERO,
            )

            quantite_sortie_point = sum(
                (
                    (m.quantite or ZERO)
                    for m in mouvements_materiau
                    if m.point_depart_id == point_id
                ),
                ZERO,
            )

            stock_point = (
                quantite_entree_point - quantite_sortie_point
            )

            stock_materiau_total += stock_point

            if stock_point != ZERO:
                stocks_par_point_dict[
                    (materiau.pk, point_id)
                ] = {
                    "materiau": materiau.materiau,
                    "materiau_projet": materiau,
                    "point": point,
                    "unite": materiau.unite,
                    "stock": stock_point,
                    "quantite": stock_point,
                    "prix_unitaire_moyen": prix_moyen,
                    "montant_stock": stock_point * prix_moyen,
                }

        # ------------------------------------------------------
        # VALORISATION FINANCIÈRE
        # Le stock restant suit le stock physique global.
        # ------------------------------------------------------
        montant_prevu = quantite_prevue * prix_moyen

        quantite_stock_valorisee = stock_materiau_total

        montant_restant = (
            quantite_stock_valorisee * prix_moyen
        )

        # ------------------------------------------------------
        # MONTANT DES MOUVEMENTS POUR L'HISTORIQUE
        # ------------------------------------------------------
        for mouvement in mouvements_materiau:
            if mouvement.type_mouvement == "ENTREE":
                mouvement.montant_mouvement = (
                    (mouvement.quantite or ZERO)
                    * (mouvement.prix_unitaire or ZERO)
                )
            else:
                mouvement.montant_mouvement = (
                    (mouvement.quantite or ZERO) * prix_moyen
                )

            mouvement.prix_moyen_materiau = prix_moyen

        # ------------------------------------------------------
        # LIGNE DU TABLEAU DES MATÉRIAUX
        # Conserve les clés attendues par le template existant.
        # ------------------------------------------------------
        ligne = {
            "materiau": materiau.materiau,
            "materiau_projet": materiau,
            "unite": materiau.unite,
            "quantite_prevue": quantite_prevue,
            "quantite_recue": quantite_recue,
            "quantite_sortie_depot": quantite_sortie,
            "quantite_utilisee": quantite_utilisee,
            "quantite_retournee": quantite_retournee,
            "quantite_restante": quantite_stock_valorisee,
            "stock_materiau_total": stock_materiau_total,
            "solde_global": stock_materiau_total,
            "prix_unitaire_moyen": prix_moyen,
            "montant_prevu": montant_prevu,
            "montant_recu": montant_entrees,
            "montant_sortie": montant_sorties,
            "montant_utilise": montant_utilise,
            "montant_retourne": montant_retourne,
            "montant_restant": montant_restant,

            # Compatibilité avec les anciens champs du template.
            "quantite_entree_depot": quantite_recue,
            "quantite_livree_directement": ZERO,
            "stock_depot": ZERO,
            "restant_equipes": stock_materiau_total,
        }

        materiaux_stats.append(ligne)

        # ------------------------------------------------------
        # CUMUL DES QUANTITÉS ET MONTANTS
        # ------------------------------------------------------
        total_prevu += quantite_prevue
        total_recu += quantite_recue
        total_sorti_depot += quantite_sortie
        total_utilise += quantite_utilisee
        total_retourne += quantite_retournee
        total_solde_global += stock_materiau_total

        total_montant_prevu += montant_prevu
        total_montant_entrees += montant_entrees
        total_montant_sorties += montant_sorties
        total_montant_utilise += montant_utilise
        total_montant_retourne += montant_retourne
        total_valeur_stock += montant_restant

    # ==========================================================
    # 4. STOCK PAR POINT
    # ==========================================================
    stocks_par_point = sorted(
        stocks_par_point_dict.values(),
        key=lambda ligne: (
            str(ligne["materiau"]).casefold(),
            str(ligne["point"]).casefold(),
        ),
    )

    # ==========================================================
    # 5. DERNIERS MOUVEMENTS UNIFIÉS
    # ==========================================================
    derniers_mouvements = list(mouvements[:10])

    # ==========================================================
    # 6. HISTORIQUES DES ANCIENNES TABLES
    # Conservés pour ne pas perdre l'accès aux données existantes.
    # ==========================================================
    dernieres_receptions = (
        ReceptionMateriauProjet.objects.filter(
            materiau_projet__projet=projet,
        )
        .select_related(
            "materiau_projet",
            "point",
            "enregistre_par",
        )
        .order_by("-date_reception", "-id")[:10]
    )

    dernieres_distributions = (
        DistributionMateriauProjet.objects.filter(
            materiau_projet__projet=projet,
        )
        .select_related(
            "materiau_projet",
            "chef_equipe",
            "point",
            "enregistre_par",
        )
        .order_by("-date_distribution", "-id")[:10]
    )

    dernieres_utilisations = (
        ConsommationMateriauProjet.objects.filter(
            Q(distribution__materiau_projet__projet=projet)
            | Q(
                reception_directe__materiau_projet__projet=projet
            )
        )
        .select_related(
            "distribution__materiau_projet",
            "distribution__point",
            "reception_directe__materiau_projet",
            "reception_directe__point",
            "enregistre_par",
        )
        .order_by("-date_consommation", "-id")[:10]
    )

    derniers_retours = (
        RetourMateriauProjet.objects.filter(
            Q(distribution__materiau_projet__projet=projet)
            | Q(
                reception_directe__materiau_projet__projet=projet
            )
        )
        .select_related(
            "distribution__materiau_projet",
            "distribution__point",
            "reception_directe__materiau_projet",
            "reception_directe__point",
            "enregistre_par",
        )
        .order_by("-date_retour", "-id")[:10]
    )

    # ==========================================================
    # 7. COMPTEURS ET INDICATEURS
    # ==========================================================
    nombre_materiaux = len(materiaux)

    nombre_receptions = mouvements.filter(
        type_mouvement="ENTREE",
    ).count()

    nombre_distributions = mouvements.filter(
        type_mouvement="SORTIE",
    ).count()

    nombre_retours = mouvements.filter(
        type_mouvement="RETOUR",
    ).count()

    # Aucune consommation n'est déduite des sorties.
    taux_utilisation = (
        total_utilise / total_recu * Decimal("100")
        if total_recu > ZERO
        else ZERO
    )

    taux_progression = min(
        taux_utilisation,
        Decimal("100"),
    )

    # ==========================================================
    # 8. CONTEXTE DU TEMPLATE
    # ==========================================================
    context = {
        "projet": projet,

        "materiaux_stats": materiaux_stats,
        "materiaux_projet": materiaux_stats,

        "stocks_par_point": stocks_par_point,
        "stocks": stocks_par_point,

        "derniers_mouvements": derniers_mouvements,

        "total_prevu": total_prevu,
        "total_recu": total_recu,
        "total_entree_depot": total_recu,
        "total_livraison_directe": ZERO,
        "total_sorti_depot": total_sorti_depot,
        "total_utilise": total_utilise,
        "total_retourne": total_retourne,

        "total_stock_depot": ZERO,
        "total_restant_equipes": total_solde_global,
        "total_solde_global": total_solde_global,

        "total_restant": sum(
            (
                ligne["quantite_restante"]
                for ligne in materiaux_stats
            ),
            ZERO,
        ),

        "total_montant_prevu": total_montant_prevu,
        "total_montant_entrees": total_montant_entrees,
        "total_montant_sorties": total_montant_sorties,
        "total_montant_utilise": total_montant_utilise,
        "total_montant_retourne": total_montant_retourne,
        "total_valeur_stock": total_valeur_stock,

        "nombre_materiaux": nombre_materiaux,
        "nombre_receptions": nombre_receptions,
        "nombre_distributions": nombre_distributions,
        "nombre_retours": nombre_retours,

        "taux_utilisation": taux_utilisation,
        "taux_progression": taux_progression,

        "dernieres_receptions": dernieres_receptions,
        "dernieres_distributions": dernieres_distributions,
        "dernieres_utilisations": dernieres_utilisations,
        "derniers_retours": derniers_retours,
    }

    return render(
        request,
        "projet/materiaux/dashbord.html",
        context,
    )

# ============================================================
# CRUD MATERIAUX DU PROJET 
# ============================================================
MATERIAUX_PROJET_CRUD = {
    "achat": {
        "model": AchatMateriauProjet,
        "form": AchatMateriauProjetForm,
        "titre": "Achats de matÃ©riaux",
        "titre_create": "Nouvel achat de matériaux",
        "titre_update": "Modifier un achat de matériaux",
        "list_url": "projet:achat_materiau_projet_list",
        "create_url": "projet:achat_materiau_projet_create",
        "update_url": "projet:achat_materiau_projet_update",
        "delete_url": "projet:achat_materiau_projet_delete",
        "relation": "materiau_projet__projet",
        "date_field": "date_achat",
    },
    "reception": {
        "model": ReceptionMateriauProjet,
        "form": ReceptionMateriauProjetForm,
        "titre": "Réceptions de matériaux",
        "titre_create": "Nouvelle réception de matériaux",
        "titre_update": "Modifier une réception",
        "list_url": "projet:reception_materiau_projet_list",
        "create_url": "projet:reception_materiau_projet_create",
        "update_url": "projet:reception_materiau_projet_update",
        "delete_url": "projet:reception_materiau_projet_delete",
        "relation": "materiau_projet__projet",
        "date_field": "date_reception",
    },
    "distribution": {
        "model": DistributionMateriauProjet,
        "form": DistributionMateriauProjetForm,
        "titre": "Distributions de matériaux",
        "titre_create": "Nouvelle distribution de matériaux",
        "titre_update": "Modifier une distribution",
        "list_url": "projet:distribution_materiau_projet_list",
        "create_url": "projet:distribution_materiau_projet_create",
        "update_url": "projet:distribution_materiau_projet_update",
        "delete_url": "projet:distribution_materiau_projet_delete",
        "relation": "materiau_projet__projet",
        "date_field": "date_distribution",
    },
    "consommation": {
        "model": ConsommationMateriauProjet,
        "form": ConsommationMateriauProjetForm,
        "titre": "Consommations de matériaux",
        "titre_create": "Nouvelle consommation de matériaux",
        "titre_update": "Modifier une consommation",
        "list_url": "projet:consommation_materiau_projet_list",
        "create_url": "projet:consommation_materiau_projet_create",
        "update_url": "projet:consommation_materiau_projet_update",
        "delete_url": "projet:consommation_materiau_projet_delete",
        "date_field": "date_consommation",
    },
    "retour": {
        "model": RetourMateriauProjet,
        "form": RetourMateriauProjetForm,
        "titre": "Retours de matériaux",
        "titre_create": "Nouveau retour de matériaux",
        "titre_update": "Modifier un retour",
        "list_url": "projet:retour_materiau_projet_list",
        "create_url": "projet:retour_materiau_projet_create",
        "update_url": "projet:retour_materiau_projet_update",
        "delete_url": "projet:retour_materiau_projet_delete",
        "date_field": "date_retour",
    },
}


def _materiaux_projet_queryset(config, projet):
    """
    Retourne les opérations de matériaux appartenant au projet.

    - Réception : mouvements unifiés de type ENTREE.
    - Distribution : mouvements unifiés de type SORTIE.
    - Achat : conserve le modèle AchatMateriauProjet.
    - Consommation et retour : conserve les modèles historiques.
    """

    type_objet = next(
        (
            nom
            for nom, parametres in MATERIAUX_PROJET_CRUD.items()
            if parametres is config
        ),
        None,
    )

    # ------------------------------------------------------
    # RÉCEPTIONS : MOUVEMENTS UNIFIÉS ENTRANTS
    # ------------------------------------------------------
    if type_objet == "reception":
        return (
            MouvementMateriauProjet.objects.filter(
                materiau_projet__projet=projet,
                type_mouvement="ENTREE",
            )
            .select_related(
                "materiau_projet",
                "point_depart",
                "point_arrivee",
                "enregistre_par",
            )
            .order_by("-date_mouvement", "-id")
        )

    # ------------------------------------------------------
    # DISTRIBUTIONS : MOUVEMENTS UNIFIÉS SORTANTS
    # ------------------------------------------------------
    if type_objet == "distribution":
        return (
            MouvementMateriauProjet.objects.filter(
                materiau_projet__projet=projet,
                type_mouvement="SORTIE",
            )
            .select_related(
                "materiau_projet",
                "point_depart",
                "point_arrivee",
                "enregistre_par",
            )
            .order_by("-date_mouvement", "-id")
        )

    # ------------------------------------------------------
    # AUTRES OPÉRATIONS : MODÈLES EXISTANTS
    # ------------------------------------------------------
    model = config["model"]

    if "relation" in config:
        return model.objects.filter(
            **{config["relation"]: projet}
        )

    if model is ConsommationMateriauProjet:
        return (
            model.objects.filter(
                Q(
                    distribution__materiau_projet__projet=projet
                )
                | Q(
                    reception_directe__materiau_projet__projet=projet
                )
            )
            .distinct()
        )

    if model is RetourMateriauProjet:
        return (
            model.objects.filter(
                Q(
                    distribution__materiau_projet__projet=projet
                )
                | Q(
                    reception_directe__materiau_projet__projet=projet
                )
            )
            .distinct()
        )

    return model.objects.none()



def _materiaux_projet_list(request, projet, type_objet):
    config = MATERIAUX_PROJET_CRUD[type_objet]

    objets = _materiaux_projet_queryset(
        config,
        projet,
    ).order_by(
        "-date_mouvement" if type_objet in ("reception", "distribution")
        else f"-{config['date_field']}",
        "-pk",
    )

    lignes = []

    utilisateur = getattr(request, "current_user", None)
    aujourd_hui = timezone.localdate()

    date_debut = getattr(projet, "date_debut", None)
    date_fin = getattr(projet, "date_fin", None)

    periode_autorisee = (
        (date_debut is None or aujourd_hui >= date_debut)
        and (date_fin is None or aujourd_hui <= date_fin)
    )

    for numero, objet in enumerate(objets, start=1):
        mouvement_unifie = type_objet in ("reception", "distribution")

        if mouvement_unifie:
            materiau_projet = objet.materiau_projet
            materiau = materiau_projet.materiau
            unite = materiau_projet.unite
            quantite = objet.quantite
            point = (
                objet.point_arrivee
                if objet.point_arrivee_id
                else objet.point_depart
            )
            date_operation = objet.date_mouvement
        else:
            materiau_projet = getattr(objet, "materiau_projet", None)

            if materiau_projet is None:
                distribution = getattr(objet, "distribution", None)
                reception_directe = getattr(objet, "reception_directe", None)

                if distribution:
                    materiau_projet = getattr(
                        distribution, "materiau_projet", None
                    )
                elif reception_directe:
                    materiau_projet = getattr(
                        reception_directe, "materiau_projet", None
                    )

            materiau = (
                getattr(materiau_projet, "materiau", None)
                if materiau_projet else None
            )
            unite = (
                getattr(materiau_projet, "unite", "")
                if materiau_projet else ""
            )

            quantite = None
            for champ_quantite in (
                "quantite_recue",
                "quantite",
                "quantite_utilisee",
                "quantite_retournee",
            ):
                valeur = getattr(objet, champ_quantite, None)
                if valeur is not None:
                    quantite = valeur
                    break

            point = getattr(objet, "point", None)
            if point is None:
                distribution = getattr(objet, "distribution", None)
                reception_directe = getattr(objet, "reception_directe", None)

                if distribution:
                    point = getattr(distribution, "point", None)
                elif reception_directe:
                    point = getattr(reception_directe, "point", None)

            date_operation = getattr(objet, config["date_field"], None)

        enregistreur_id = getattr(objet, "enregistre_par_id", None)

        est_enregistreur = (
            utilisateur is not None
            and enregistreur_id is not None
            and enregistreur_id == utilisateur.pk
        )

        peut_modifier = est_enregistreur and periode_autorisee

        enregistre_le = getattr(objet, "created_at", None)
        if enregistre_le is None:
            enregistre_le = getattr(objet, "date_creation", None)

        lignes.append({
            "numero": numero,
            "objet": objet,
            "materiau": materiau,
            "quantite": quantite,
            "unite": unite,
            "point": point,
            "observation": getattr(objet, "observation", ""),
            "date_operation": date_operation,
            "enregistre_le": enregistre_le,
            "est_enregistreur": est_enregistreur,
            "peut_modifier": peut_modifier,
            "modifier_url": (
                reverse(
                    config["update_url"],
                    kwargs={"projet_id": projet.pk, "pk": objet.pk},
                )
                if peut_modifier else None
            ),
            "supprimer_url": reverse(
                config["delete_url"],
                kwargs={"projet_id": projet.pk, "pk": objet.pk},
            ),
        })

    context = {
        "projet": projet,
        "type_objet": type_objet,
        "titre_page": config["titre"],
        "lignes": lignes,
        "url_ajout": reverse(
            config["create_url"],
            kwargs={"projet_id": projet.pk},
        ),
    }

    template_name = config.get(
        "template_list",
        "projet/materiaux_projet/crud_list.html",
    )

    return render(request, template_name, context)

# ============================================================
# CREATION GENERIQUE
# ============================================================
def _materiaux_projet_create(request, projet, type_objet):
    from django.contrib import messages
    from django.core.exceptions import ValidationError
    from django.shortcuts import redirect, render
    from django.urls import reverse

    config = MATERIAUX_PROJET_CRUD.get(type_objet)

    if config is None:
        messages.error(request, "Type d'opÃ©ration de matÃ©riaux inconnu.")
        return redirect("projet:projet_list")

    FormClass = config["form"]

    url_retour = reverse(
        config["list_url"],
        kwargs={"projet_id": projet.pk},
    )

    contexte = {
        "projet": projet,
        "titre_page": config["titre_create"],
        "mode": "create",
        "type_objet": type_objet,
        "url_retour": url_retour,
    }

    if request.method == "POST":
        form = FormClass(
            request.POST,
            request.FILES,
            projet=projet,
        )

        if form.is_valid():

            # =====================================================
            # CAS PARTICULIER : RETOUR DE MATÃ‰RIAUX
            # Le formulaire rÃ©partit automatiquement le retour
            # entre les distributions concernÃ©es.
            # =====================================================
            if type_objet == "retour":
                utilisateur = getattr(
                    request,
                    "current_user",
                    None,
                )

                from users.models import AppUser

                if utilisateur is None or not isinstance(utilisateur, AppUser):
                    messages.error(
                        request,
                        "Utilisateur non identifié. " "Veuillez vous reconnecter.",
                    )
                    contexte["form"] = form

                    return render(
                        request,
                        "projet/materiaux_projet/crud_form.html",
                        contexte,
                    )

                try:
                    retours_crees = form.enregistrer_retour(enregistre_par=utilisateur)

                    if not retours_crees:
                        form.add_error(
                            None, "Aucun retour de matÃ©riau n'a été enregistré."
                        )

                        messages.error(
                            request, "Aucun retour de matÃ©riau n'a été enregistré."
                        )

                        contexte["form"] = form

                        return render(
                            request,
                            "projet/materiaux_projet/crud_form.html",
                            contexte,
                        )

                except ValidationError as exc:
                    # Ne pas ajouter les erreurs aux champs du modÃ¨le
                    # distribution/reception_directe : ces champs ne
                    # figurent pas dans le formulaire de retour.
                    if hasattr(exc, "message_dict"):
                        for erreurs in exc.message_dict.values():
                            for erreur in erreurs:
                                form.add_error(None, erreur)
                    else:
                        for erreur in exc.messages:
                            form.add_error(None, erreur)

                    messages.error(
                        request,
                        "Le retour n'a pas pu être enregistré. Vérifiez les informations saisies.",
                    )

                    contexte["form"] = form

                    return render(
                        request,
                        "projet/materiaux_projet/crud_form.html",
                        contexte,
                    )

                messages.success(
                    request, f"{config['titre']} : enregistrement réussi."
                )

                return redirect(
                    config["list_url"],
                    projet_id=projet.pk,
                )

            # =====================================================
            # AUTRES OPÃ‰RATIONS : COMPORTEMENT HABITUEL
            # =====================================================
            objet = form.save(commit=False)

            # Affecter l'utilisateur uniquement si le modÃ¨le
            # possÃ¨de le champ enregistre_par.
            if hasattr(objet, "enregistre_par_id"):
                from users.models import AppUser

                utilisateur = getattr(
                    request,
                    "current_user",
                    None,
                )

                if utilisateur is None or not isinstance(utilisateur, AppUser):
                    messages.error(
                        request,
                        "Utilisateur non identifiÃ©. " "Veuillez vous reconnecter.",
                    )

                    contexte["form"] = form

                    return render(
                        request,
                        "projet/materiaux_projet/crud_form.html",
                        contexte,
                    )

                objet.enregistre_par = utilisateur

            objet.save()
            form.save_m2m()

            messages.success(request, f"{config['titre']} : enregistrement réussi.")

            return redirect(
                config["list_url"],
                projet_id=projet.pk,
            )

        messages.error(request, "Veuillez corriger les erreurs du formulaire.")

    else:
        form = FormClass(projet=projet)

    contexte["form"] = form

    return render(
        request,
        "projet/materiaux_projet/crud_form.html",
        contexte,
    )


# ============================================================
# MODIFICATION GENERIQUE
# ============================================================
def _materiaux_projet_update(request, projet, type_objet, pk):
    config = MATERIAUX_PROJET_CRUD[type_objet]
    form_class = config["form"]

    objet = get_object_or_404(
        _materiaux_projet_queryset(config, projet),
        pk=pk,
    )

    # ContrÃ´le des droits avant d'afficher ou de traiter le formulaire.
    if not _peut_modifier_mouvement_materiau(
        request,
        projet,
        objet,
    ):
        messages.error(
            request,
            (
                "Modification refusÃ©e : seul l'enregistreur initial "
                "peut modifier cette opération pendant la période du projet."
            ),
        )
        return redirect(
            config["list_url"],
            projet_id=projet.pk,
        )

    if request.method == "POST":
        form = form_class(
            request.POST,
            request.FILES,
            instance=objet,
            projet=projet,
        )

        if form.is_valid():
            objet_modifie = form.save(commit=False)

            # Protection : l'enregistreur initial ne peut pas Ãªtre remplacÃ©.
            objet_modifie.enregistre_par_id = objet.enregistre_par_id

            objet_modifie.save()
            form.save_m2m()

            messages.success(
                request,
                "Modification enregistrée avec succées.",
            )

            return redirect(
                config["list_url"],
                projet_id=projet.pk,
            )
    else:
        form = form_class(
            instance=objet,
            projet=projet,
        )

    return render(
        request,
        "projet/materiaux_projet/crud_form.html",
        {
            "projet": projet,
            "form": form,
            "objet": objet,
            "titre_page": config["titre_update"],
            "mode": "update",
            "type_objet": type_objet,
            "url_retour": reverse(
                config["list_url"],
                kwargs={"projet_id": projet.pk},
            ),
        },
    )


# ============================================================
# SUPPRESSION GENERIQUE
# ============================================================
def _materiaux_projet_delete(request, projet, type_objet, pk):
    config = MATERIAUX_PROJET_CRUD[type_objet]

    objet = get_object_or_404(
        _materiaux_projet_queryset(config, projet),
        pk=pk,
    )

    if request.method == "POST":
        try:
            objet.delete()

            messages.success(
                request,
                "Enregistrement supprimÃ© avec succÃ¨s.",
            )

        except ProtectedError:
            messages.error(
                request,
                (
                    "Suppression impossible : cet enregistrement "
                    "est utilisé par d'autres opérations. "
                    "Vérifiez les mouvements liés avant de continuer."
                ),
            )

        return redirect(
            config["list_url"],
            projet_id=projet.pk,
        )

    return render(
        request,
        "projet/materiaux_projet/crud_confirm_delete.html",
        {
            "projet": projet,
            "objet": objet,
            "titre_page": "Confirmer la suppression",
            "type_objet": type_objet,
            "url_retour": reverse(
                config["list_url"],
                kwargs={"projet_id": projet.pk},
            ),
        },
    )


# ============================================================
# VUES PUBLIQUES ACHATS
# ============================================================
@project_access_required
def achat_materiau_projet_list(request, projet_id):
    projet = get_object_or_404(Projet, pk=projet_id)
    return _materiaux_projet_list(request, projet, "achat")


@project_access_required
def achat_materiau_projet_create(request, projet_id):
    projet = get_object_or_404(Projet, pk=projet_id)
    return _materiaux_projet_create(request, projet, "achat")


@project_access_required
def achat_materiau_projet_update(request, projet_id, pk):
    projet = get_object_or_404(Projet, pk=projet_id)
    return _materiaux_projet_update(request, projet, "achat", pk)


@project_access_required
def achat_materiau_projet_delete(request, projet_id, pk):
    projet = get_object_or_404(Projet, pk=projet_id)
    return _materiaux_projet_delete(request, projet, "achat", pk)


# ============================================================
# VUES PUBLIQUES RECEPTIONS
# ============================================================
@login_required_projet
@project_access_required
def reception_materiau_projet_list(request, projet_id):
    projet = get_object_or_404(Projet, pk=projet_id)
    return _materiaux_projet_list(request, projet, "reception")


@project_access_required
def reception_materiau_projet_create(request, projet_id):
    projet = get_object_or_404(Projet, pk=projet_id)
    return _materiaux_projet_create(request, projet, "reception")


@project_access_required
def reception_materiau_projet_update(request, projet_id, pk):
    projet = get_object_or_404(Projet, pk=projet_id)
    return _materiaux_projet_update(request, projet, "reception", pk)


@project_access_required
def reception_materiau_projet_delete(request, projet_id, pk):
    projet = get_object_or_404(Projet, pk=projet_id)
    return _materiaux_projet_delete(request, projet, "reception", pk)


# ============================================================
# VUES PUBLIQUE DISTRIBUTIONS
# ============================================================
@login_required_projet
@project_access_required
def distribution_materiau_projet_list(request, projet_id):
    projet = get_object_or_404(Projet, pk=projet_id)
    return _materiaux_projet_list(request, projet, "distribution")


@project_access_required
def distribution_materiau_projet_create(request, projet_id):
    projet = get_object_or_404(Projet, pk=projet_id)
    return _materiaux_projet_create(request, projet, "distribution")


@project_access_required
def distribution_materiau_projet_update(request, projet_id, pk):
    projet = get_object_or_404(Projet, pk=projet_id)
    return _materiaux_projet_update(request, projet, "distribution", pk)


@project_access_required
def distribution_materiau_projet_delete(request, projet_id, pk):
    projet = get_object_or_404(Projet, pk=projet_id)
    return _materiaux_projet_delete(request, projet, "distribution", pk)


# ============================================================
# VUES PUBLIQUES  CONSOMMATIONS
# ============================================================
@project_access_required
def consommation_materiau_projet_list(request, projet_id):
    projet = get_object_or_404(Projet, pk=projet_id)
    return _materiaux_projet_list(request, projet, "consommation")


@project_access_required
def consommation_materiau_projet_create(request, projet_id):
    projet = get_object_or_404(Projet, pk=projet_id)
    return _materiaux_projet_create(request, projet, "consommation")


@project_access_required
def consommation_materiau_projet_update(request, projet_id, pk):
    projet = get_object_or_404(Projet, pk=projet_id)
    return _materiaux_projet_update(request, projet, "consommation", pk)


@project_access_required
def consommation_materiau_projet_delete(request, projet_id, pk):
    projet = get_object_or_404(Projet, pk=projet_id)
    return _materiaux_projet_delete(request, projet, "consommation", pk)


# ============================================================
# VUES PUBLIQUES RETOURS
# ============================================================
@project_access_required
def retour_materiau_projet_list(request, projet_id):
    projet = get_object_or_404(Projet, pk=projet_id)
    return _materiaux_projet_list(request, projet, "retour")


@project_access_required
def retour_materiau_projet_create(request, projet_id):
    projet = get_object_or_404(Projet, pk=projet_id)
    return _materiaux_projet_create(request, projet, "retour")


@project_access_required
def retour_materiau_projet_update(request, projet_id, pk):
    projet = get_object_or_404(Projet, pk=projet_id)
    return _materiaux_projet_update(request, projet, "retour", pk)


@project_access_required
def retour_materiau_projet_delete(request, projet_id, pk):
    projet = get_object_or_404(Projet, pk=projet_id)
    return _materiaux_projet_delete(request, projet, "retour", pk)


# ============================================================
# MOUVEMENTS UNIFIÃ‰S DES MATÃ‰RIAUX DU PROJET
# ============================================================
def calculer_stock_point(projet, materiau, point):
    mouvements = MouvementMateriauProjet.objects.filter(
        materiau_projet__projet=projet,
        materiau_projet=materiau,
    )

    entrees = mouvements.filter(point_arrivee=point).aggregate(total=Sum("quantite"))[
        "total"
    ] or Decimal("0.00")

    sorties = mouvements.filter(point_depart=point).aggregate(total=Sum("quantite"))[
        "total"
    ] or Decimal("0.00")

    return entrees - sorties


@project_access_required
def mouvements_materiaux_projet(request, projet_id):
    from decimal import Decimal

    from django.shortcuts import render

    projet = request.projet
    ZERO = Decimal("0")

    # ======================================================
    # 1. RÃ‰CUPÃ‰RER LES MOUVEMENTS DU PROJET
    # ======================================================

    mouvements = (
        MouvementMateriauProjet.objects.filter(materiau_projet__projet=projet)
        .select_related(
            "materiau_projet",
            "point_depart",
            "point_arrivee",
            "enregistre_par",
        )
        .order_by("-date_mouvement", "-id")
    )

    # ======================================================
    # 2. VÃ‰RIFIER SI LA PÃ‰RIODE DU PROJET EST ACTIVE
    # ======================================================

    periode_projet_active = projet.est_actif and not projet.periode_terminee

    # ======================================================
    # 3. IDENTIFIER L'UTILISATEUR CONNECTÃ‰
    # ======================================================

    utilisateur_courant = getattr(
        request,
        "current_user",
        None,
    )

    if utilisateur_courant is None:
        utilisateur_id = request.session.get("user_id")

        if utilisateur_id:
            utilisateur_courant = AppUser.objects.filter(pk=utilisateur_id).first()

    # ======================================================
    # 4. DROITS DE MODIFICATION ET DE SUPPRESSION
    # ======================================================

    for mouvement in mouvements:
        mouvement.peut_modifier = (
            periode_projet_active
            and utilisateur_courant is not None
            and mouvement.enregistre_par_id is not None
            and mouvement.enregistre_par_id == utilisateur_courant.pk
        )

    # ======================================================
    # 5. RÃ‰CUPÃ‰RER LES MATÃ‰RIAUX DU PROJET
    # ======================================================

    materiaux = MateriauProjet.objects.filter(projet=projet).order_by("materiau", "id")

    # ======================================================
    # 6. CALCULER LES STOCKS PAR MATÃ‰RIAU ET PAR POINT
    # ======================================================

    stocks = []

    points_utilises = {}

    # Ne retenir que les points rÃ©ellement associÃ©s
    # aux mouvements du projet.
    for mouvement in mouvements:
        if mouvement.point_depart_id:
            points_utilises[mouvement.point_depart_id] = mouvement.point_depart

        if mouvement.point_arrivee_id:
            points_utilises[mouvement.point_arrivee_id] = mouvement.point_arrivee

    # Trier les points par identifiant.
    points = sorted(
        points_utilises.values(),
        key=lambda point: point.pk,
    )

    for materiau in materiaux:
        for point in points:

            stock = calculer_stock_point(
                projet,
                materiau,
                point,
            )

            # Ne pas afficher les stocks nuls.
            # Les stocks négatifs restent visibles pour
            # permettre de repérer une anomalie.
            if stock is None or stock == ZERO:
                continue

            stocks.append(
                {
                    "materiau": materiau.materiau,
                    "materiau_projet": materiau,
                    "unite": materiau.unite,
                    "point": point,
                    "stock": stock,
                }
            )

    # ======================================================
    # 7. ENVOYER LES DONNÃ‰ES AU TEMPLATE
    # ======================================================

    return render(
        request,
        "projet/materiaux/mouvements.html",
        {
            "projet": projet,
            "mouvements": mouvements,
            "stocks": stocks,
            "periode_projet_active": periode_projet_active,
        },
    )


@project_access_required
def mouvement_materiau_projet_create(request, projet_id):
    projet = request.projet

    if request.method == "POST":
        form = MouvementMateriauProjetForm(
            request.POST,
            projet=projet,
        )

        if form.is_valid():
            mouvement = form.save(commit=False)

            utilisateur = getattr(request, "current_user", None)

            if utilisateur is None:
                utilisateur_id = request.session.get("user_id")
                if utilisateur_id:
                    from users.models import AppUser

                    utilisateur = AppUser.objects.filter(pk=utilisateur_id).first()

            mouvement.enregistre_par = utilisateur

            try:
                with transaction.atomic():
                    if mouvement.point_depart_id:
                        stock = calculer_stock_point(
                            projet,
                            mouvement.materiau_projet,
                            mouvement.point_depart,
                        )

                        if mouvement.quantite > stock:
                            form.add_error(
                                "quantite",
                                (
                                    f"Stock insuffisant au point "
                                    f"{mouvement.point_depart}. "
                                    f"Disponible : {stock} "
                                    f"{mouvement.materiau_projet.unite}."
                                ),
                            )
                            raise ValidationError("Stock insuffisant.")

                    mouvement.full_clean()
                    mouvement.save()

                messages.success(
                    request,
                    "Mouvement de matériau enregistré avec succés.",
                )
                return redirect(
                    "projet:mouvements_materiaux_projet",
                    projet_id=projet.pk,
                )

            except ValidationError as exc:
                if not form.errors:
                    if hasattr(exc, "message_dict"):
                        for field, errors in exc.message_dict.items():
                            for error in errors:
                                form.add_error(field, error)
                    else:
                        form.add_error(None, exc)

    else:
        form = MouvementMateriauProjetForm(projet=projet)

    return render(
        request,
        "projet/materiaux/mouvement_form.html",
        {
            "projet": projet,
            "form": form,
            "titre": "Nouveau mouvement de matériau",
            "bouton": "Enregistrer le mouvement",
        },
    )


def _utilisateur_mouvement_courant(request):
    utilisateur = getattr(request, "current_user", None)

    if utilisateur is not None:
        return utilisateur

    utilisateur_id = request.session.get("user_id")
    if not utilisateur_id:
        return None

    return AppUser.objects.filter(pk=utilisateur_id).first()


def _mouvement_modifiable(request, projet, mouvement):
    utilisateur = _utilisateur_mouvement_courant(request)

    return bool(
        projet.est_actif
        and not projet.periode_terminee
        and utilisateur is not None
        and mouvement.enregistre_par_id is not None
        and mouvement.enregistre_par_id == utilisateur.pk
    )


@project_access_required
@require_http_methods(["GET", "POST"])
def mouvement_materiau_projet_update(request, projet_id, mouvement_id):
    projet = request.projet

    mouvement = get_object_or_404(
        MouvementMateriauProjet,
        pk=mouvement_id,
        materiau_projet__projet=projet,
    )

    if not _mouvement_modifiable(request, projet, mouvement):
        messages.error(
            request,
            "Modification interdite : seul l'enregistreur peut "
            "modifier ce mouvement pendant la période active du projet.",
        )
        return redirect(
            "projet:mouvements_materiaux_projet",
            projet_id=projet.pk,
        )

    if request.method == "POST":
        form = MouvementMateriauProjetForm(
            request.POST,
            instance=mouvement,
        )

        if form.is_valid():
            form.save()
            messages.success(request, "Le mouvement de matériau a été modifié.")
            return redirect(
                "projet:mouvements_materiaux_projet",
                projet_id=projet.pk,
            )
    else:
        form = MouvementMateriauProjetForm(instance=mouvement)

    return render(
        request,
        "projet/materiaux/mouvement_form.html",
        {
            "projet": projet,
            "mouvement": mouvement,
            "form": form,
            "titre_page": "Modifier le mouvement",
        },
    )


@project_access_required
@require_http_methods(["GET", "POST"])
def mouvement_materiau_projet_delete(request, projet_id, mouvement_id):
    projet = request.projet

    mouvement = get_object_or_404(
        MouvementMateriauProjet,
        pk=mouvement_id,
        materiau_projet__projet=projet,
    )

    if not _mouvement_modifiable(request, projet, mouvement):
        messages.error(
            request,
            "Suppression interdite : seul l'enregistreur peut "
            "supprimer ce mouvement pendant la période active du projet.",
        )
        return redirect(
            "projet:mouvements_materiaux_projet",
            projet_id=projet.pk,
        )

    if request.method == "POST":
        mouvement.delete()
        messages.success(request, "Le mouvement de matÃ©riau a été supprimé.")
        return redirect(
            "projet:mouvements_materiaux_projet",
            projet_id=projet.pk,
        )

    return render(
        request,
        "projet/materiaux/mouvement_confirm_delete.html",
        {
            "projet": projet,
            "mouvement": mouvement,
        },
    )
