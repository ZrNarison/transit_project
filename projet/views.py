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

from .forms import (ProjetForm,EquipeProjetForm,PointProjetForm,RapportProjetForm,RapportTravailForm,RapportMateriauForm,VehiculeProjetForm,RapportVehiculeForm,ActiviteTransportProjetForm)
from .models import (Projet,EquipeProjet,PointProjet,RapportProjet,RapportTravail,RapportMateriau,RapportVehicule,)
from .models import (
    Projet,
    EquipeProjet,
    VehiculeProjet,ActiviteTransportProjet,
    PointProjet,
    RapportProjet,
    RapportTravail,
    RapportMateriau,
    RapportVehicule,
)
# ============================================================

# FONCTIONS DU PERSONNEL DE PROJET

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

def prepare_equipe_form(form, projet=None, affectation=None):

    if "personnel" in form.fields:

        form.fields["personnel"].label = "Personnel de l'entreprise"

        queryset = (
            Personnel.objects
            .filter(typeTravail="Construction")
            .order_by("nom", "prenom")
        )

        if projet:

            deja_affectes = (
                EquipeProjet.objects
                .filter(projet=projet)
                .values_list("personnel_id", flat=True)
            )

            if affectation:
                deja_affectes = deja_affectes.exclude(
                    personnel_id=affectation.personnel_id
                )

            queryset = queryset.exclude(
                id__in=deja_affectes
            )

        form.fields["personnel"].queryset = queryset

    return form

# ============================================================

# UTILISATEUR CONNECTÉ

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

# AUTHENTIFICATION

# ============================================================

def login_required_projet(view_func):
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
    if not user:
        return False

    return user.role in {
        "Admin",
        "Superviseur",
        "UserEntreprise",
    }


def project_manager_required(view_func):
    @wraps(view_func)
    @login_required_projet
    def wrapper(request, *args, **kwargs):

        if not user_can_manage_projects(request.current_user):
            messages.error(
                request,
                "Vous n'avez pas l'autorisation de gérer les projets."
            )
            return redirect("projet:projet_list")

        return view_func(request, *args, **kwargs)

    return wrapper


# ============================================================

# PERSONNEL DE L'UTILISATEUR

# ============================================================

def get_current_personnel(request):
    user = getattr(request,"current_user",None,)

    if not user:
        return None

    return getattr(
        user,
        "personnel",
        None,
    )


# ============================================================

# VÉRIFICATION D'ACCÈS À UN PROJET

# ============================================================

def user_has_project_access(user, projet):

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

    return EquipeProjet.objects.filter(
        projet=projet,
        personnel=personnel,
        actif=True,
        date_debut__lte=aujourd_hui,
        date_fin__gte=aujourd_hui,
    ).exists()


# ============================================================

# PROJECT ACCESS REQUIRED

# ============================================================

def project_access_required(view_func):
    @wraps(view_func)
    @login_required_projet
    def wrapper(request, *args, **kwargs):

        projet_id = kwargs.get("projet_id")

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
                "Votre accès à ce projet n'est pas actif."
            )

            return redirect(
                "projet:projet_list"
            )

        request.projet = projet

        return view_func(request, *args, **kwargs)

    return wrapper

# ============================================================
# CREER UN COMPTE UTILISATEUR POUR UN MEMBRE DU PROJET
# ============================================================

@project_manager_required
def utilisateur_projet_create(request, projet_id, equipe_id):

    projet = get_object_or_404(
        Projet,
        pk=projet_id
    )

    affectation = get_object_or_404(
        EquipeProjet.objects.select_related("personnel"),
        pk=equipe_id,
        projet=projet
    )

    personnel = affectation.personnel

    # ========================================================
    # VERIFIER SI LE PERSONNEL A DEJA UN COMPTE
    # ========================================================

    compte_existant = AppUser.objects.filter(
        personnel=personnel
    ).first()

    if compte_existant:

        messages.warning(
            request,
            (
                f"{personnel} possède déjà un compte "
                f"utilisateur « {compte_existant.username} »."
            )
        )

        return redirect(
            "projet:equipe_list",
            projet_id=projet.pk
        )

    # ========================================================
    # POST
    # ========================================================

    if request.method == "POST":

        username = request.POST.get(
            "username",
            ""
        ).strip()

        password = request.POST.get(
            "password",
            ""
        )

        password_confirmation = request.POST.get(
            "password_confirmation",
            ""
        )

        # ----------------------------------------------------
        # VALIDATIONS
        # ----------------------------------------------------

        if not username:

            messages.error(
                request,
                "Le nom d'utilisateur est obligatoire."
            )

        elif not password:

            messages.error(
                request,
                "Le mot de passe est obligatoire."
            )

        elif password != password_confirmation:

            messages.error(
                request,
                "Les deux mots de passe ne correspondent pas."
            )

        elif AppUser.objects.filter(
            username=username
        ).exists():

            messages.error(
                request,
                f"Le nom d'utilisateur « {username} » existe déjà."
            )

        else:

            # ------------------------------------------------
            # CREATION DU COMPTE
            # ------------------------------------------------

            utilisateur = AppUser.objects.create(
                personnel=personnel,
                username=username,
                password=make_password(password),
                role="UserProjet",
            )

            # ------------------------------------------------
            # MESSAGE
            # ------------------------------------------------

            messages.success(
                request,
                (
                    f"Le compte « {utilisateur.username} » "
                    f"a été créé pour {personnel}."
                )
            )

            return redirect(
                "projet:equipe_list",
                projet_id=projet.pk
            )

    # ========================================================
    # AFFICHAGE
    # ========================================================

    return render(
        request,
        "projet/utilisateur_projet_form.html",
        {
            "projet": projet,
            "affectation": affectation,
            "personnel": personnel,
            "user": request.current_user,
        }
    )


# ============================================================

# CONTRÔLE DES FONCTIONS

# ============================================================

def user_has_project_function(user,projet,fonctions,):
    if not user or not getattr(user, "personnel", None):
        return False

    if user_can_manage_projects(user):
        return True

    aujourd_hui = timezone.localdate()

    return EquipeProjet.objects.filter(
        projet=projet,
        personnel=user.personnel,
        actif=True,
        date_debut__lte=aujourd_hui,
        date_fin__gte=aujourd_hui,
        fonction__in=fonctions,
    ).exists()

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

    context = {
        "projets": projets,
        "user": user,
        "aujourd_hui": timezone.localdate(),
    }
    return render(
        request,
        "projet/projet_list.html",
        context,
    )


# ============================================================

# CRÉER UN PROJET

# ============================================================

@project_manager_required
def projet_create(request):

    if request.method == "POST":

        form = ProjetForm(request.POST)

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
                "Le projet a été créé avec succès."
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
# MODIFICATION D'UN PROJET
# ============================================================

@project_manager_required
def projet_update(request, projet_id):

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    # ========================================================
    # POST
    # ========================================================

    if request.method == "POST":

        form = ProjetForm(
            request.POST,
            instance=projet,
        )

        if form.is_valid():

            projet_modifie = form.save(
                commit=False
            )

            # On conserve l'utilisateur qui avait créé
            # initialement le projet.
            #
            # Si tu veux au contraire enregistrer le dernier
            # utilisateur ayant modifié le projet, il faudrait
            # un champ spécifique pour cela.
            projet_modifie.save()

            messages.success(
                request,
                "Le projet a été modifié avec succès."
            )

            return redirect(
                "projet:projet_detail",
                projet_id=projet.pk,
            )

    # ========================================================
    # GET
    # ========================================================

    else:

        form = ProjetForm(
            instance=projet,
        )

    # ========================================================
    # AFFICHAGE DU FORMULAIRE
    #
    # Ce return est exécuté :
    # - après un GET ;
    # - après un POST invalide.
    # ========================================================

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
def projet_delete(request,projet_id,):
    projet = get_object_or_404(Projet,pk=projet_id,)

    # Seul l'utilisateur ayant enregistré le projet
    # peut le supprimer.
    if projet.enregistre_par_id != request.current_user.id:

        messages.error(
            request,
            "Vous n'êtes pas autorisé à supprimer ce projet."
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
            "Le projet a été supprimé."
        )

    except ProtectedError:

        messages.error(
            request,
            (
                "Impossible de supprimer ce projet car "
                "il possède des données liées."
            )
        )

    return redirect(
        "projet:projet_list"
    )

# ============================================================
# RAPPORT GLOBAL DU PROJET
# ============================================================

@project_access_required
def rapport_projet_global(request, projet_id):

    projet = request.projet

    rapports_projet = (
        RapportProjet.objects
        .filter(projet=projet)
        .select_related("auteur")
    )

    rapports_travaux = (
        RapportTravail.objects
        .filter(projet=projet)
        .select_related(
            "point",
            "auteur",
        )
    )

    rapports_materiaux = (
        RapportMateriau.objects
        .filter(projet=projet)
        .select_related(
            "point",
            "materiau",
            "auteur",
        )
    )

    rapports_vehicules = (
        RapportVehicule.objects
        .filter(projet=projet)
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
# DETAIL D'UN PROJET
# ============================================================

@login_required_projet
def projet_detail(request, projet_id):

    projet = get_object_or_404(
        Projet.objects
        .select_related(
            "enregistre_par",
        )
        .prefetch_related(
            "equipe__personnel",
            # "points__nom",
            "rapports_projet__auteur",
            "rapports_travaux__auteur",
            "rapports_materiaux__materiau",
            "rapports_materiaux__auteur",
            "rapports_vehicules__vehicule",
            "rapports_vehicules__chauffeur",
        ),
        pk=projet_id,
    )

    # ========================================================
    # VERIFICATION DE L'ACCES AU PROJET
    # ========================================================

    if not user_has_project_access(
        request.current_user,
        projet,
    ):

        messages.error(
            request,
            "Votre accès à ce projet n'est pas actif."
        )

        return redirect(
            "projet:projet_list"
        )

    # ========================================================
    # EQUIPE
    # ========================================================

    equipe = (
        projet.equipe
        .all()
        .select_related("personnel")
        .order_by(
            "fonction",
            "personnel__nom",
            "personnel__prenom",
        )
    )

    # ========================================================
    # POINTS DE CHANTIER
    # ========================================================

    points = (
        projet.points
        .all()
        .select_related("nom")
    )

    # ========================================================
    # RAPPORTS
    # ========================================================

    rapports_projet = (
        projet.rapports_projet
        .all()
        .select_related("auteur")
    )

    rapports_travaux = (
        projet.rapports_travaux
        .all()
        .select_related("auteur")
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
    # DONNEES MATERIAUX / TRANSPORT / DEPENSES
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
    # ACTIVITES DE TRANSPORT
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
    # DEPENSES GENERALES
    # ========================================================

    depenses = (
        Depense.objects
        .filter(
            projet=projet
        )
    )

    # ========================================================
    # DEPENSES GASOIL
    # ========================================================

    depenses_gasoil = (
        DepenseGasoil.objects
        .filter(
            projet=projet
        )
    )

    # ========================================================
    # REPARATIONS VEHICULES
    # ========================================================

    reparations = (
        ReparationVehicule.objects
        .filter(
            projet=projet
        )
    )

    # ========================================================
    # PAIEMENTS DOCKERS
    # ========================================================

    paiements_dockers = (
        PaiementDocker.objects
        .filter(
            projet=projet
        )
    )

    # ========================================================
    # TOTAUX MATERIAUX
    # ========================================================

    total_sorties = (
        sorties_materiaux
        .aggregate(
            total=Sum("quantite")
        )["total"]
        or 0
    )

    # ========================================================
    # TOTAL TRANSPORT
    # ========================================================

    total_transport = (
        transports
        .aggregate(
            total=Sum("quantite")
        )["total"]
        or 0
    )

    # ========================================================
    # TOTAL RECEPTIONS
    # ========================================================

    total_reception = (
        receptions
        .aggregate(
            total=Sum("quantite_recue")
        )["total"]
        or 0
    )

    # ========================================================
    # TOTAL UTILISATIONS
    # ========================================================

    total_utilisation = (
        utilisations
        .aggregate(
            total=Sum("quantite_utilisee")
        )["total"]
        or 0
    )

    # ========================================================
    # TOTAL RETOURS
    # ========================================================

    total_retour = (
        retours
        .aggregate(
            total=Sum("quantite")
        )["total"]
        or 0
    )

    # ========================================================
    # TOTAL DEPENSES GENERALES
    # ========================================================

    total_depenses = (
        depenses
        .aggregate(
            total=Sum("montant")
        )["total"]
        or 0
    )

    # ========================================================
    # TOTAL GASOIL
    #
    # DepenseGasoil possède le champ "total".
    # ========================================================

    total_gasoil = (
        depenses_gasoil
        .aggregate(
            total=Sum("total")
        )["total"]
        or 0
    )

    # ========================================================
    # TOTAL REPARATIONS
    #
    # IMPORTANT :
    # ReparationVehicule possède "total".
    # Il n'existe PAS de champ "montant_total".
    # ========================================================

    total_reparations = (
        reparations
        .aggregate(
            total=Sum("total")
        )["total"]
        or 0
    )

    # ========================================================
    # TOTAL PAIEMENTS DOCKERS
    # ========================================================

    total_dockers = (
        paiements_dockers
        .aggregate(
            total=Sum("montant")
        )["total"]
        or 0
    )

    # ========================================================
    # TOTAL GENERAL DES DEPENSES DU PROJET
    # ========================================================

    total_depenses_projet = (
        total_depenses
        + total_gasoil
        + total_reparations
        + total_dockers
    )

    # ========================================================
    # CONTEXTE
    # ========================================================

    context = {

        # ----------------------------------------------------
        # PROJET
        # ----------------------------------------------------

        "projet": projet,

        # ----------------------------------------------------
        # EQUIPE / POINTS
        # ----------------------------------------------------

        "equipe": equipe,
        "points": points,

        # ----------------------------------------------------
        # RAPPORTS
        # ----------------------------------------------------

        "rapports_projet": rapports_projet,
        "rapports_travaux": rapports_travaux,
        "rapports_materiaux": rapports_materiaux,
        "rapports_vehicules": rapports_vehicules,

        "total_rapports": total_rapports,

        # ----------------------------------------------------
        # MATERIAUX / TRANSPORT
        # ----------------------------------------------------

        "sorties_materiaux": sorties_materiaux,
        "transports": transports,
        "receptions": receptions,
        "utilisations": utilisations,
        "retours": retours,

        # ----------------------------------------------------
        # TOTAUX MATERIAUX / TRANSPORT
        # ----------------------------------------------------

        "total_sorties": total_sorties,
        "total_transport": total_transport,
        "total_reception": total_reception,
        "total_utilisation": total_utilisation,
        "total_retour": total_retour,

        # ----------------------------------------------------
        # DEPENSES
        # ----------------------------------------------------

        "depenses": depenses,
        "depenses_gasoil": depenses_gasoil,
        "reparations": reparations,
        "paiements_dockers": paiements_dockers,

        # ----------------------------------------------------
        # TOTAUX FINANCIERS
        # ----------------------------------------------------

        "total_depenses": total_depenses,
        "total_gasoil": total_gasoil,
        "total_reparations": total_reparations,
        "total_dockers": total_dockers,
        "total_depenses_projet": total_depenses_projet,

        # ----------------------------------------------------
        # UTILISATEUR
        # ----------------------------------------------------

        "user": request.current_user,

        # ----------------------------------------------------
        # PERMISSIONS
        # ----------------------------------------------------

        "peut_gerer": user_can_manage_projects(
            request.current_user
        ),

        "acces_actuel": user_has_project_access(
            request.current_user,
            projet,
        ),

        # ----------------------------------------------------
        # DATE
        # ----------------------------------------------------

        "aujourd_hui": timezone.localdate(),
    }

    # ========================================================
    # AFFICHAGE
    # ========================================================

    return render(
        request,
        "projet/projet_detail.html",
        context,
    )

# ============================================================
# ÉQUIPE - LISTE
# ============================================================

@project_manager_required
def equipe_list(request, projet_id):

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    equipe = (
        EquipeProjet.objects
        .filter(projet=projet)
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
# CREATION D'UNE AFFECTATION D'EQUIPE
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

        # IMPORTANT :
        # Le modèle EquipeProjet utilise self.projet dans clean().
        # Il faut donc affecter le projet AVANT form.is_valid().
        form.instance.projet = projet

        form = prepare_equipe_form(
            form,
            projet=projet,
        )

        if form.is_valid():

            affectation = form.save()

            messages.success(
                request,
                (
                    f"{affectation.personnel} a été affecté au projet "
                    f"« {projet.titre} » comme "
                    f"{affectation.get_fonction_display()}."
                )
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
            form.fields["date_debut"].initial = projet.date_debut

        if "date_fin" in form.fields:
            form.fields["date_fin"].initial = projet.date_fin

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
def equipe_update(request, projet_id, equipe_id):

    projet = get_object_or_404(
        Projet,
        pk=projet_id
    )

    affectation = get_object_or_404(
        EquipeProjet,
        pk=equipe_id,
        projet=projet
    )

    # ========================================================
    # POST
    # ========================================================

    if request.method == "POST":

        form = EquipeProjetForm(
            request.POST,
            instance=affectation,
            projet=projet
        )

        form = prepare_equipe_form(
            form,
            projet=projet,
            affectation=affectation
        )

        if form.is_valid():

            affectation_modifiee = form.save()

            messages.success(
                request,
                (
                    f"L'affectation de "
                    f"{affectation_modifiee.personnel} "
                    f"a été modifiée avec succès."
                )
            )

            return redirect(
                "projet:equipe_list",
                projet_id=projet.pk
            )

    # ========================================================
    # GET
    # ========================================================

    else:

        form = EquipeProjetForm(
            instance=affectation,
            projet=projet
        )

        form = prepare_equipe_form(
            form,
            projet=projet,
            affectation=affectation
        )

    # ========================================================
    # AFFICHAGE DU FORMULAIRE
    # ========================================================

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
def equipe_delete(request, projet_id, equipe_id):

    # --------------------------------------------------------
    # Récupérer l'affectation appartenant bien au projet
    # --------------------------------------------------------

    affectation = get_object_or_404(
        EquipeProjet,
        pk=equipe_id,
        projet_id=projet_id,
    )

    # --------------------------------------------------------
    # La suppression doit obligatoirement être faite en POST
    # --------------------------------------------------------

    if request.method != "POST":

        messages.error(
            request,
            "La suppression d'une affectation doit être effectuée par POST."
        )

        return redirect(
            "projet:equipe_list",
            projet_id=projet_id,
        )

    # --------------------------------------------------------
    # Suppression
    # --------------------------------------------------------

    try:

        personnel = affectation.personnel

        affectation.delete()

        messages.success(
            request,
            (
                f"L'affectation de {personnel} "
                f"a été supprimée du projet."
            )
        )

    except ProtectedError:

        messages.error(
            request,
            (
                "Cette affectation est utilisée "
                "par des données historiques "
                "et ne peut pas être supprimée."
            )
        )

    # --------------------------------------------------------
    # Retour dans tous les cas
    # --------------------------------------------------------

    return redirect(
        "projet:equipe_list",
        projet_id=projet_id,
    )



# ============================================================

# POINTS - LISTE

# ============================================================

# @project_manager_required
def point_list(request,projet_id,):
    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    points = (
        PointProjet.objects
        .filter(projet=projet)
        .select_related("nom")
        .order_by("code")
    )

    return render(
        request,
        "projet/point_list.html",
        {
            "projet": projet,
            "points": points,
        },
    )

# ============================================================

# AJOUTER UN POINT

# ============================================================

# @project_manager_required
def point_create(request,projet_id,):
    projet = get_object_or_404(Projet,pk=projet_id,)

    if request.method == "POST":

        form = PointProjetForm(request.POST,projet=projet,)

        if form.is_valid():
            point = form.save(
                commit=False
            )

            point.projet = projet

            point.save()

            messages.success(
                request,
                "Le point de chantier a été créé."
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
        },
    )

# ============================================================

# MODIFIER UN POINT

# ============================================================

@project_manager_required
def point_update(request,projet_id,point_id,):
    projet = get_object_or_404(Projet,pk=projet_id,)

    point = get_object_or_404(PointProjet,pk=point_id,projet=projet,)

    if request.method == "POST":
        form = PointProjetForm(
            request.POST,
            instance=point,
            projet=projet,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Le point de chantier a été modifié."
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
        },
    )

# ============================================================

# SUPPRIMER UN POINT

# ============================================================

@project_manager_required
def point_delete(request,projet_id,point_id,):
    point = get_object_or_404(PointProjet,pk=point_id,projet_id=projet_id,    )
    if request.method == "POST":
        try:
            point.delete()

            messages.success(
                request,
                "Le point de chantier a été supprimé."
                )

        except ProtectedError:
            messages.error(
                request,
                (
                    "Impossible de supprimer ce point car "
                    "il est utilisé par des données du projet."
                )
            )
            return redirect(
                "projet:point_list",
                projet_id=projet_id,
            )

# ============================================================

# RAPPORT PROJET - LISTE

# ============================================================

@project_access_required
def rapport_projet_list(request,projet_id,):
    rapports = (
        RapportProjet.objects
        .filter(projet=request.projet)
        .select_related("auteur")
    )

    return render(
        request,
        "projet/rapport_projet_list.html",
        {
            "projet": request.projet,
            "rapports": rapports,
        },
    )

@login_required_projet
def rapport_projet_selection(request):

    projets = (
        Projet.objects
        .all()
        .order_by("-date_debut", "-id")
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

# CRÉER RAPPORT PROJET

# ============================================================

@project_access_required
def rapport_projet_create(request,projet_id,):
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
            )
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
                "Le rapport de projet a été enregistré."
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
        },
    )


# ============================================================

# MODIFIER RAPPORT PROJET

# ============================================================

@project_access_required
def rapport_projet_update(request,projet_id,rapport_id,):
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

            form.save()

            messages.success(
                request,
                "Le rapport a été modifié."
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
        },
    )


# ============================================================

# RAPPORT TRAVAIL - LISTE

# ============================================================

@project_access_required
def rapport_travail_list(request,projet_id,):
    rapports = (
        RapportTravail.objects
        .filter(projet=request.projet)
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
        },
    )

# ============================================================

# RAPPORT TRAVAIL - CRÉER

# ============================================================

@project_access_required
def rapport_travail_create(request,projet_id,):
    projet = request.projet
    user = request.current_user

    if not user_has_project_function(user,projet,["CHEF_CHANTIER"],):
        messages.error(
            request,
            (
                "Seul le Chef de Chantier peut enregistrer "
                "un rapport de travail."
            )
        )

        return redirect(
            "projet:projet_detail",
            projet_id=projet.pk,
        )

    if request.method == "POST":

        form = RapportTravailForm(request.POST,request.FILES,projet=projet,)
        if form.is_valid():
            rapport = form.save(
                commit=False
                )
            
            rapport.projet = projet
            rapport.auteur = user.personnel

            rapport.save()

            messages.success(request,"Le rapport de travail a été enregistré.")
            return redirect("projet:rapport_travail_list",projet_id=projet.pk,)

        else:
            form = RapportTravailForm(projet=projet,)
            return render(request,"projet/rapport_travail_form.html",{"form": form,"projet": projet,"titre_page": "Nouveau rapport de travail",},)


# ============================================================

# RAPPORT MATÉRIAUX - LISTE

# ============================================================

@project_access_required
def rapport_materiau_list(request,projet_id,):
    rapports = (
            RapportMateriau.objects
            .filter(projet=request.projet)
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
        },
    )


# ============================================================

# RAPPORT MATÉRIAU - CRÉER

# ============================================================

@project_access_required
def rapport_materiau_create(request,projet_id,):
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
            )
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
                "Le rapport matériau a été enregistré."
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
        },
    )

# ============================================================
# VEHICULES AFFECTES AUX PROJETS
# ============================================================

# @project_manager_required
def vehicule_projet_list(request, projet_id):
    """
    Liste des véhicules affectés à un projet.
    """

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    affectations = (
        VehiculeProjet.objects
        .filter(projet=projet)
        .select_related(
            "chauffeur",
            "projet",
        )
        .order_by(
            "-date_debut",
            "-id",
        )
    )

    user = get_current_user(request)

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

    return render(
        request,
        "projet/vehicule_projet_list.html",
        {
            "projet": projet,
            "affectations": affectations,
            "user": user,
            "total_km": total_km,
            "total_carburant": total_carburant,
            "total_actifs": total_actifs,
        },
    )


@project_manager_required
def vehicule_projet_create(request, projet_id):
    """
    Affecter un véhicule à un projet.
    """
    projet = get_object_or_404(Projet, pk=projet_id)

    if request.method == "POST":
        form = VehiculeProjetForm(
            request.POST,
            projet=projet,
        )

        # Très important : rattacher le formulaire au projet
        form.instance.projet = projet

        if form.is_valid():
            affectation = form.save(commit=False)
            affectation.projet = projet
            affectation.save()

            messages.success(
                request,
                f"Le véhicule {affectation.vehicule} "
                f"a été affecté au projet « {projet.titre} »."
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
        },
    )

@project_manager_required
def vehicule_projet_update(
    request,
    projet_id,
    vehicule_projet_id,
):
    """
    Modifier l'affectation d'un véhicule à un projet.
    """

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

            affectation = form.save(
                commit=False
            )

            affectation.projet = projet

            affectation.save()

            messages.success(
                request,
                "L'affectation du véhicule "
                "a été modifiée avec succès.",
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
        },
    )


@project_manager_required
def vehicule_projet_delete(
    request,
    projet_id,
    vehicule_projet_id,
):
    """
    Supprimer une affectation de véhicule.
    """

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

            vehicule = str(affectation.vehicule)

            affectation.delete()

            messages.success(
                request,
                f"L'affectation du véhicule "
                f"« {vehicule} » a été supprimée avec succès."
            )

        except ProtectedError:

            messages.error(
                request,
                "Impossible de supprimer cette affectation "
                "car elle est utilisée par d'autres données."
            )

        return redirect(
            "projet:vehicule_projet_list",
            projet_id=projet.pk,
        )

    # Toute requête GET retourne simplement à la liste
    return redirect(
        "projet:vehicule_projet_list",
        projet_id=projet.pk,
    )

# ============================================================

# RAPPORT VÉHICULE - LISTE

# ============================================================

@project_access_required
def rapport_vehicule_list(request,projet_id,):
    rapports = (
            RapportVehicule.objects
            .filter(projet=request.projet)
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
        },
    )

# ============================================================
# RAPPORT VÉHICULE - CRÉER
# ============================================================

@project_access_required
def rapport_vehicule_create(request, projet_id):

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    if request.method == "POST":

        form = RapportVehiculeForm(
            request.POST,
            request.FILES,
            projet=projet,
        )

        if form.is_valid():

            # =================================================
            # DONNÉES VALIDÉES
            # =================================================

            vehicule = form.cleaned_data.get("vehicule")
            chauffeur = form.cleaned_data.get("chauffeur")

            # =================================================
            # VÉRIFICATION OBLIGATOIRE
            # =================================================

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

            # =================================================
            # SAUVEGARDE
            # =================================================

            if not form.errors:

                rapport = form.save(commit=False)

                # -------------------------------------------------
                # FK par ID : aucune ambiguïté
                # -------------------------------------------------

                rapport.projet_id = projet.pk
                rapport.vehicule_id = vehicule.pk
                rapport.chauffeur_id = chauffeur.pk

                # -------------------------------------------------
                # Sauvegarde
                # -------------------------------------------------

                rapport.save()

                # =================================================
                # AUDIT ÉVENTUEL
                # =================================================

                # Si tu as un audit ici, utilise les IDs ou les
                # valeurs déjà connues, pas rapport.chauffeur
                # avant sauvegarde.

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
        },
    )


@login_required_projet
def equipe_projet_selection(request):
    projets = Projet.objects.all().order_by("-date_debut", "-id")

    if not user_can_manage_projects(request.current_user):
        messages.error(
            request,
            "Vous n'avez pas l'autorisation de gérer les équipes."
        )
        return redirect("projet:projet_list")

    return render(
        request,
        "projet/equipe_projet_selection.html",
        {
            "projets": projets,
            "user": request.current_user,
        },
    )

# ============================================================
# CRUD ACTIVITÉS TRANSPORT DU PROJET
# ============================================================


# ============================================================
# LISTE
# ============================================================

@project_manager_required
def activite_transport_projet_list(request, projet_id):
    """
    Liste des activités de transport d'un projet.
    """

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    activites = (
        ActiviteTransportProjet.objects
        .filter(
            projet=projet,
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
        },
    )


# ============================================================
# AJOUT
# ============================================================

@project_manager_required
def activite_transport_projet_create(request, projet_id):
    """
    Ajouter une activité de transport à un projet.
    """

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    user = get_current_user(request)

    if not user:
        return redirect("users:login")

    if request.method == "POST":

        form = ActiviteTransportProjetForm(
            request.POST,
            projet=projet,
        )

        if form.is_valid():

            activite = form.save(
                commit=False
            )

            # Projet imposé par l'URL
            activite.projet = projet

            # Utilisateur connecté
            activite.enregistre_par = user

            activite.save()

            messages.success(
                request,
                "L'activité de transport a été enregistrée avec succès.",
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
        },
    )


# ============================================================
# MODIFICATION
# ============================================================

@project_manager_required
def activite_transport_projet_update(
    request,
    projet_id,
    activite_id,
):
    """
    Modifier une activité de transport.

    Seul l'utilisateur ayant enregistré l'activité
    peut la modifier.
    """

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

    user = get_current_user(request)

    if not user:

        return redirect(
            "users:login"
        )

    # --------------------------------------------------------
    # AUTORISATION
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == "POST":

        form = ActiviteTransportProjetForm(
            request.POST,
            instance=activite,
            projet=projet,
        )

        if form.is_valid():

            activite = form.save(
                commit=False
            )

            # Empêcher le changement de projet
            activite.projet = projet

            activite.save()

            messages.success(
                request,
                "L'activité de transport a été modifiée avec succès.",
            )

            return redirect(
                "projet:activite_transport_projet_list",
                projet_id=projet.pk,
            )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

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
            "titre_page": "Modifier l'activité de transport",
            "mode": "update",
        },
    )


# ============================================================
# SUPPRESSION
# ============================================================

@project_manager_required
def activite_transport_projet_delete(
    request,
    projet_id,
    activite_id,
):
    """
    Supprimer une activité de transport.

    Seul l'utilisateur ayant enregistré l'activité
    peut la supprimer.
    """

    projet = get_object_or_404(
        Projet,
        pk=projet_id,
    )

    activite = get_object_or_404(
        ActiviteTransportProjet,
        pk=activite_id,
        projet=projet,
    )

    user = get_current_user(request)

    if not user:

        return redirect(
            "users:login"
        )

    # --------------------------------------------------------
    # AUTORISATION
    # --------------------------------------------------------

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

    # --------------------------------------------------------
    # POST = SUPPRESSION
    # --------------------------------------------------------

    if request.method == "POST":

        try:

            activite.delete()

            messages.success(
                request,
                "L'activité de transport a été supprimée avec succès.",
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

    # --------------------------------------------------------
    # GET = PAGE CONFIRMATION
    # --------------------------------------------------------

    return render(
        request,
        "projet/activite_transport_projet_confirm_delete.html",
        {
            "projet": projet,
            "activite": activite,
        },
    )
