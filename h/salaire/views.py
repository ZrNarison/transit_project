from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from users.models import AppUser

from .forms import h_SalaireForm
from .models import (
    h_Salaire,
    recalculer_situation_personnel,
)


# =============================================================
# UTILISATEUR CONNECTÉ
# =============================================================

def get_current_user(request):

    user_id = request.session.get(
        "user_id"
    )

    if not user_id:
        return None

    return (
        AppUser.objects
        .filter(
            pk=user_id
        )
        .first()
    )


# =============================================================
# VÉRIFICATION SESSION
# =============================================================

def check_session(request):

    user = get_current_user(
        request
    )

    if not user:
        return None

    return user


# =============================================================
# LISTE DES SALAIRES
# =============================================================

def h_salaire_list(request):

    utilisateur = check_session(
        request
    )

    if not utilisateur:

        return redirect(
            "users:login"
        )

    role = request.session.get(
        "role"
    )

    # =========================================================
    # SALAIRES
    # =========================================================

    salaires = (
        h_Salaire.objects
        .select_related(
            "personnel",
            "enregistreur",
        )
        .all()
    )

    # =========================================================
    # FILTRE ROLE
    # =========================================================

    if role == "UserMica":

        salaires = salaires.filter(
            personnel__typeTravail="Mica"
        )

    elif role == "UserEntreprise":

        salaires = salaires.filter(
            personnel__typeTravail="Construction"
        )

    # =========================================================
    # FILTRE PERSONNEL
    # =========================================================

    personnel_recherche = (
        request.GET.get(
            "personnel",
            ""
        ).strip()
    )

    if personnel_recherche:

        salaires = salaires.filter(
            Q(
                personnel__nom__icontains=(
                    personnel_recherche
                )
            )
            |
            Q(
                personnel__prenom__icontains=(
                    personnel_recherche
                )
            )
        )

    # =========================================================
    # FILTRE MONTANT
    # =========================================================

    montant = (
        request.GET.get(
            "montant",
            ""
        ).strip()
    )

    if montant:

        try:

            salaires = salaires.filter(
                montant=montant
            )

        except (
            ValueError,
            TypeError
        ):

            pass

    # =========================================================
    # FILTRE DATE
    # =========================================================

    date = (
        request.GET.get(
            "date",
            ""
        ).strip()
    )

    if date:

        salaires = salaires.filter(
            date_paiement=date
        )

    # =========================================================
    # TOTAL SALAIRES
    # =========================================================

    total_salaires = (
        salaires.aggregate(
            total=Sum("montant")
        )["total"]
        or 0
    )

    # =========================================================
    # TOTAL RESTE
    # =========================================================

    total_reste = (
        salaires.aggregate(
            total=Sum("reste")
        )["total"]
        or 0
    )

    # =========================================================
    # TOTAL TROP-PERÇU
    # =========================================================

    total_trop_percu = (
        salaires.aggregate(
            total=Sum("trop_percu")
        )["total"]
        or 0
    )

    # =========================================================
    # PAGINATION
    # =========================================================

    paginator = Paginator(
        salaires,
        10
    )

    page_number = (
        request.GET.get(
            "page"
        )
    )

    page_obj = paginator.get_page(
        page_number
    )

    # =========================================================
    # PERSONNELS POUR FILTRE
    # =========================================================

    from personnel.models import Personnel

    personnels = (
        Personnel.objects
        .all()
        .order_by(
            "nom",
            "prenom",
        )
    )

    if role == "UserMica":

        personnels = personnels.filter(
            typeTravail="Mica"
        )

    elif role == "UserEntreprise":

        personnels = personnels.filter(
            typeTravail="Construction"
        )

    # =========================================================
    # PARAMÈTRES POUR PAGINATION
    # =========================================================

    query_params = (
        request.GET.copy()
    )

    if "page" in query_params:
        query_params.pop(
            "page"
        )

    query_params = (
        query_params.urlencode()
    )

    # =========================================================
    # RENDU
    # =========================================================

    return render(
        request,
        "h/salaire/list.html",
        {
            "salaires": page_obj,
            "page_obj": page_obj,
            "personnels": personnels,

            "total_salaires": (
                total_salaires
            ),

            "total_reste": (
                total_reste
            ),

            "total_trop_percu": (
                total_trop_percu
            ),

            "role": role,
            "utilisateur": utilisateur,

            "personnel": (
                personnel_recherche
            ),

            "montant": montant,
            "date": date,

            "query_params": (
                query_params
            ),
        }
    )


# =============================================================
# AJOUT SALAIRE
# =============================================================

def h_salaire_add(request):

    utilisateur = check_session(
        request
    )

    if not utilisateur:

        return redirect(
            "users:login"
        )

    role = request.session.get(
        "role"
    )

    # =========================================================
    # POST
    # =========================================================

    if request.method == "POST":

        form = h_SalaireForm(
            request.POST,
            role=role,
        )

        if form.is_valid():

            with transaction.atomic():

                salaire = form.save(
                    commit=False
                )

                # ---------------------------------------------
                # Enregistreur
                # ---------------------------------------------

                salaire.enregistreur = (
                    utilisateur
                )

                salaire.save()

                # ---------------------------------------------
                # Recalcul complet
                # ---------------------------------------------

                if salaire.personnel:

                    recalculer_situation_personnel(
                        salaire.personnel
                    )

            messages.success(
                request,
                "Le salaire a été enregistré avec succès."
            )

            return redirect(
                "salaire:h_salaire_list"
            )

    # =========================================================
    # GET
    # =========================================================

    else:

        form = h_SalaireForm(
            role=role
        )

    # =========================================================
    # RENDU
    # =========================================================

    return render(
        request,
        "h/salaire/form.html",
        {
            "form": form,
            "action": "Ajouter",
            "role": role,
        }
    )


# =============================================================
# MODIFICATION SALAIRE
#
# Compatible avec :
#
#     path(..., salaire_edit, ...)
#     <int:id>
#
# ET :
#
#     <int:pk>
#
# =============================================================

def h_salaire_edit(
    request,
    id=None,
    pk=None,
):

    utilisateur = check_session(
        request
    )

    if not utilisateur:

        return redirect(
            "users:login"
        )

    role = request.session.get(
        "role"
    )

    # =========================================================
    # IDENTIFIANT
    # =========================================================

    salaire_id = (
        id
        if id is not None
        else pk
    )

    if salaire_id is None:

        messages.error(
            request,
            "Identifiant du salaire manquant."
        )

        return redirect(
            "salaire:h_salaire_list"
        )

    # =========================================================
    # SALAIRE
    # =========================================================

    salaire = get_object_or_404(
        h_Salaire.objects.select_related(
            "personnel",
            "enregistreur",
        ),
        pk=salaire_id,
    )

    # =========================================================
    # AUTORISATION
    #
    # Seul l'enregistreur peut modifier.
    # =========================================================

    if (
        salaire.enregistreur_id
        != utilisateur.id
    ):

        messages.error(
            request,
            "Vous n'êtes pas autorisé à modifier ce salaire."
        )

        return redirect(
            "salaire:h_salaire_list"
        )

    # =========================================================
    # ANCIEN PERSONNEL
    # =========================================================

    ancien_personnel = (
        salaire.personnel
    )

    # =========================================================
    # POST
    # =========================================================

    if request.method == "POST":

        form = h_SalaireForm(
            request.POST,
            instance=salaire,
            role=role,
        )

        if form.is_valid():

            with transaction.atomic():

                salaire_modifie = (
                    form.save(
                        commit=False
                    )
                )

                # ---------------------------------------------
                # L'enregistreur ne change pas
                # ---------------------------------------------

                salaire_modifie.enregistreur = (
                    utilisateur
                )

                salaire_modifie.save()

                # ---------------------------------------------
                # Nouveau personnel
                # ---------------------------------------------

                nouveau_personnel = (
                    salaire_modifie.personnel
                )

                # ---------------------------------------------
                # Personnel inchangé
                # ---------------------------------------------

                if (
                    ancien_personnel
                    and nouveau_personnel
                    and ancien_personnel.id
                    == nouveau_personnel.id
                ):

                    recalculer_situation_personnel(
                        nouveau_personnel
                    )

                # ---------------------------------------------
                # Personnel changé
                # ---------------------------------------------

                else:

                    if ancien_personnel:

                        recalculer_situation_personnel(
                            ancien_personnel
                        )

                    if nouveau_personnel:

                        recalculer_situation_personnel(
                            nouveau_personnel
                        )

            messages.success(
                request,
                "Le salaire a été modifié avec succès."
            )

            return redirect(
                "salaire:salaire_list"
            )

    # =========================================================
    # GET
    # =========================================================

    else:

        form = h_SalaireForm(
            instance=salaire,
            role=role,
        )

    # =========================================================
    # RENDU
    # =========================================================

    return render(
        request,
        "h/salaire/form.html",
        {
            "form": form,
            "action": "Modifier",
            "salaire": salaire,
            "role": role,
        }
    )


# =============================================================
# SUPPRESSION SALAIRE
#
# Compatible avec id ET pk.
# =============================================================

def h_salaire_delete(
    request,
    id=None,
    pk=None,
):

    utilisateur = check_session(
        request
    )

    if not utilisateur:

        return redirect(
            "users:login"
        )

    # =========================================================
    # IDENTIFIANT
    # =========================================================

    salaire_id = (
        id
        if id is not None
        else pk
    )

    if salaire_id is None:

        messages.error(
            request,
            "Identifiant du salaire manquant."
        )

        return redirect(
            "salaire:h_salaire_list"
        )

    # =========================================================
    # SALAIRE
    # =========================================================

    salaire = get_object_or_404(
        h_Salaire.objects.select_related(
            "personnel",
            "enregistreur",
        ),
        pk=salaire_id,
    )

    # =========================================================
    # AUTORISATION
    # =========================================================

    if (
        salaire.enregistreur_id
        != utilisateur.id
    ):

        messages.error(
            request,
            "Vous n'êtes pas autorisé à supprimer ce salaire."
        )

        return redirect(
            "salaire:h_salaire_list"
        )

    # =========================================================
    # PERSONNEL
    # =========================================================

    personnel = (
        salaire.personnel
    )

    # =========================================================
    # SUPPRESSION
    # =========================================================

    if request.method == "POST":

        with transaction.atomic():

            salaire.delete()

            # ---------------------------------------------
            # Recalcul après suppression
            # ---------------------------------------------

            if personnel:

                recalculer_situation_personnel(
                    personnel
                )

        messages.success(
            request,
            "Le salaire a été supprimé avec succès."
        )

        return redirect(
            "salaire:h_salaire_list"
        )

    # =========================================================
    # CONFIRMATION
    # =========================================================

    return render(
        request,
        "h/salaire/confirm_delete.html",
        {
            "salaire": salaire,
        }
    )