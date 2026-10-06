from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib import messages
from salaire.views import recalculer_situation_personnel
from .forms import AvanceForm
from .models import Avance

from personnel.models import Personnel
from users.models import AppUser

from audit.utils import enregistrer_action


# =========================================================
# OUTIL : QUERYSET PERSONNEL SELON LE RÔLE
# =========================================================

def get_personnel_queryset_for_role(role):

    queryset = (
        Personnel.objects
        .select_related("categorie")
        .all()
        .order_by("nom", "prenom")
    )

    # -----------------------------------------------------
    # USER MICA
    # -----------------------------------------------------

    if role == "UserMica":

        return queryset.filter(
            typeTravail="Mica"
        )

    # -----------------------------------------------------
    # USER ENTREPRISE
    # -----------------------------------------------------

    elif role == "UserEntreprise":

        return queryset.filter(
            typeTravail="Construction"
        )

    # -----------------------------------------------------
    # ADMIN / SUPERADMIN / SUPERVISEUR
    # -----------------------------------------------------

    elif role in [
        "Admin",
        "SuperAdmin",
        "Superviseur"
    ]:

        return queryset

    # -----------------------------------------------------
    # AUTRE / RÔLE INVALIDE
    # -----------------------------------------------------

    return Personnel.objects.none()


# =========================================================
# OUTIL : QUERYSET AVANCE SELON LE RÔLE
# =========================================================

def get_avance_queryset_for_role(role):

    queryset = (
        Avance.objects
        .select_related(
            "personnel",
            "distribution",
            "enregistre_par"
        )
        .all()
        .order_by("-dateAv")
    )

    # -----------------------------------------------------
    # USER MICA
    # -----------------------------------------------------

    if role == "UserMica":

        return queryset.filter(
            personnel__typeTravail="Mica"
        )

    # -----------------------------------------------------
    # USER ENTREPRISE
    # -----------------------------------------------------

    elif role == "UserEntreprise":

        return queryset.filter(
            personnel__typeTravail="Construction"
        )

    # -----------------------------------------------------
    # ADMIN / SUPERADMIN / SUPERVISEUR
    # -----------------------------------------------------

    elif role in [
        "Admin",
        "SuperAdmin",
        "Superviseur"
    ]:

        return queryset

    # -----------------------------------------------------
    # AUTRE / RÔLE INVALIDE
    # -----------------------------------------------------

    return Avance.objects.none()


# =========================================================
# AJOUT
# =========================================================

def avance_add(request):

    # -----------------------------------------------------
    # RÔLE DE L'UTILISATEUR
    # -----------------------------------------------------

    role = request.session.get("role")

    # -----------------------------------------------------
    # VÉRIFICATION SESSION
    # -----------------------------------------------------

    if not request.session.get("user_id"):

        messages.error(
            request,
            "Votre session a expiré. Veuillez vous reconnecter."
        )

        return redirect("users:login")

    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    if request.method == "POST":

        form = AvanceForm(
            request.POST,
            role=role
        )

        if form.is_valid():

            avance = form.save(
                commit=False
            )

            # -------------------------------------------------
            # SÉCURITÉ : VÉRIFIER LE PERSONNEL
            # -------------------------------------------------

            personnel = avance.personnel

            personnel_queryset = (
                get_personnel_queryset_for_role(role)
            )

            if not personnel_queryset.filter(
                id=personnel.id
            ).exists():

                messages.error(
                    request,
                    "Vous n'êtes pas autorisé à enregistrer "
                    "une avance pour ce personnel."
                )

                return redirect(
                    "avances:avance_list"
                )

            # -------------------------------------------------
            # UTILISATEUR CONNECTÉ
            # -------------------------------------------------

            user_id = request.session.get(
                "user_id"
            )

            if user_id:

                try:

                    avance.enregistre_par = (
                        AppUser.objects.get(
                            id=user_id
                        )
                    )

                except AppUser.DoesNotExist:

                    avance.enregistre_par = None

            # -------------------------------------------------
            # ENREGISTREMENT
            # -------------------------------------------------

            avance.save()

            if avance.personnel:
                recalculer_situation_personnel(
                    avance.personnel
    )

            # -------------------------------------------------
            # AUDIT
            # -------------------------------------------------

            enregistrer_action(
                request,
                "CREATE",
                "Avance",
                avance.id,
                nouvelle={
                    "personnel": str(
                        avance.personnel
                    ),
                    "montant": str(
                        avance.montantAv
                    ),
                    "motif": avance.motifAv,
                    "type": avance.typeAv
                },
                description=(
                    "Création d'une avance personnel"
                )
            )

            # -------------------------------------------------
            # MESSAGE
            # -------------------------------------------------

            messages.success(
                request,
                "Avance enregistrée avec succès."
            )

            return redirect(
                "avances:avance_list"
            )

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    else:

        form = AvanceForm(
            role=role
        )

    # -----------------------------------------------------
    # AFFICHAGE
    # -----------------------------------------------------

    return render(
        request,
        "avances/form.html",
        {
            "form": form,
            "role": role
        }
    )


# =========================================================
# LISTE
# =========================================================

def avance_list(request):

    # -----------------------------------------------------
    # RÔLE
    # -----------------------------------------------------

    role = request.session.get("role")

    # -----------------------------------------------------
    # AVANCES AUTORISÉES
    # -----------------------------------------------------

    avances = get_avance_queryset_for_role(
        role
    )

    # -----------------------------------------------------
    # RECHERCHE PERSONNEL
    # -----------------------------------------------------

    recherche = request.GET.get(
        "personnel",
        ""
    ).strip()

    # -----------------------------------------------------
    # FILTRE DATE
    # -----------------------------------------------------

    date = request.GET.get(
        "date",
        ""
    ).strip()

    # -----------------------------------------------------
    # RECHERCHE
    # -----------------------------------------------------

    if recherche:

        avances = avances.filter(
            Q(
                personnel__nom__icontains=recherche
            )
            |
            Q(
                personnel__prenom__icontains=recherche
            )
        )

    # -----------------------------------------------------
    # DATE
    # -----------------------------------------------------

    if date:

        avances = avances.filter(
            dateAv__date=date
        )

    # -----------------------------------------------------
    # PAGINATION
    # -----------------------------------------------------

    paginator = Paginator(
        avances,
        12
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )

    # -----------------------------------------------------
    # PARAMÈTRES POUR PAGINATION
    # -----------------------------------------------------

    query_params = request.GET.copy()

    query_params.pop(
        "page",
        None
    )

    # -----------------------------------------------------
    # AFFICHAGE
    # -----------------------------------------------------

    return render(
        request,
        "avances/list.html",
        {
            "avances": page_obj,
            "page_obj": page_obj,
            "personnel": recherche,
            "date": date,
            "role": role,
            "query_params": query_params.urlencode()
        }
    )


# =========================================================
# DETAIL
# =========================================================

def avance_detail(request, id):

    # -----------------------------------------------------
    # RÔLE
    # -----------------------------------------------------

    role = request.session.get(
        "role"
    )

    # -----------------------------------------------------
    # SÉCURITÉ
    # -----------------------------------------------------

    avance = get_object_or_404(
        get_avance_queryset_for_role(role),
        id=id
    )

    # -----------------------------------------------------
    # AUDIT
    # -----------------------------------------------------

    enregistrer_action(
        request,
        "VIEW",
        "Avance",
        id,
        description=(
            "Consultation détail avance personnel"
        )
    )

    # -----------------------------------------------------
    # AFFICHAGE
    # -----------------------------------------------------

    return render(
        request,
        "avances/detail.html",
        {
            "avance": avance,
            "role": role
        }
    )


# =========================================================
# MODIFICATION
# =========================================================

def avance_edit(request, id):

    # -----------------------------------------------------
    # RÔLE
    # -----------------------------------------------------

    role = request.session.get(
        "role"
    )

    # -----------------------------------------------------
    # AVANCE AUTORISÉE POUR CE RÔLE
    # -----------------------------------------------------

    avance = get_object_or_404(
        get_avance_queryset_for_role(role),
        id=id
    )

    # -----------------------------------------------------
    # UTILISATEUR CONNECTÉ
    # -----------------------------------------------------

    user_id = request.session.get(
        "user_id"
    )

    # -----------------------------------------------------
    # VÉRIFICATION PROPRIÉTAIRE
    # -----------------------------------------------------

    if (
        not user_id
        or avance.enregistre_par_id != int(user_id)
    ):

        messages.error(
            request,
            "Vous ne pouvez pas modifier cette avance."
        )

        return redirect(
            "avances:avance_list"
        )

    # -----------------------------------------------------
    # ANCIENNES VALEURS
    # -----------------------------------------------------

    ancienne = {
        "personnel": str(
            avance.personnel
        ),
        "montant": str(
            avance.montantAv
        ),
        "motif": avance.motifAv,
        "type": avance.typeAv
    }

    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    if request.method == "POST":

        form = AvanceForm(
            request.POST,
            instance=avance,
            role=role
        )

        if form.is_valid():

            # ---------------------------------------------
            # VÉRIFICATION PERSONNEL
            # ---------------------------------------------

            personnel = form.cleaned_data.get(
                "personnel"
            )

            personnel_queryset = (
                get_personnel_queryset_for_role(role)
            )

            if not personnel_queryset.filter(
                id=personnel.id
            ).exists():

                messages.error(
                    request,
                    "Vous n'êtes pas autorisé à sélectionner "
                    "ce personnel."
                )

                return redirect(
                    "avances:avance_list"
                )

            # ---------------------------------------------
            # ENREGISTRER
            # ---------------------------------------------

            avance_modifiee = form.save()

            # ---------------------------------------------
            # NOUVELLES VALEURS
            # ---------------------------------------------

            nouvelle = {
                "personnel": str(
                    avance_modifiee.personnel
                ),
                "montant": str(
                    avance_modifiee.montantAv
                ),
                "motif": avance_modifiee.motifAv,
                "type": avance_modifiee.typeAv
            }

            # ---------------------------------------------
            # AUDIT
            # ---------------------------------------------

            enregistrer_action(
                request,
                "UPDATE",
                "Avance",
                id,
                ancienne=ancienne,
                nouvelle=nouvelle,
                description=(
                    "Modification d'une avance personnel"
                )
            )

            # ---------------------------------------------
            # MESSAGE
            # ---------------------------------------------

            messages.success(
                request,
                "Avance modifiée avec succès."
            )

            return redirect(
                "avances:avance_list"
            )

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    else:

        form = AvanceForm(
            instance=avance,
            role=role
        )

    # -----------------------------------------------------
    # AFFICHAGE
    # -----------------------------------------------------

    return render(
        request,
        "avances/form.html",
        {
            "form": form,
            "role": role,
            "avance": avance
        }
    )


# =========================================================
# SUPPRESSION
# =========================================================

def avance_delete(request, id):

    # -----------------------------------------------------
    # RÔLE
    # -----------------------------------------------------

    role = request.session.get(
        "role"
    )

    # -----------------------------------------------------
    # AVANCE AUTORISÉE POUR CE RÔLE
    # -----------------------------------------------------

    avance = get_object_or_404(
        get_avance_queryset_for_role(role),
        id=id
    )

    # -----------------------------------------------------
    # UTILISATEUR CONNECTÉ
    # -----------------------------------------------------

    user_id = request.session.get(
        "user_id"
    )

    # -----------------------------------------------------
    # VÉRIFICATION PROPRIÉTAIRE
    # -----------------------------------------------------

    if (
        not user_id
        or avance.enregistre_par_id != int(user_id)
    ):

        messages.error(
            request,
            "Vous ne pouvez pas supprimer cette avance."
        )

        return redirect(
            "avances:avance_list"
        )

    # -----------------------------------------------------
    # ANCIENNES VALEURS
    # -----------------------------------------------------

    ancienne = {
        "personnel": str(
            avance.personnel
        ),
        "montant": str(
            avance.montantAv
        ),
        "motif": avance.motifAv,
        "type": avance.typeAv
    }

    # -----------------------------------------------------
    # SUPPRESSION
    # -----------------------------------------------------

    if request.method == "POST":

        enregistrer_action(
            request,
            "DELETE",
            "Avance",
            id,
            ancienne=ancienne,
            description=(
                "Suppression d'une avance personnel"
            )
        )

        avance.delete()

        messages.success(
            request,
            "Avance supprimée avec succès."
        )

    # -----------------------------------------------------
    # RETOUR
    # -----------------------------------------------------

    return redirect(
        "avances:avance_list"
    )


