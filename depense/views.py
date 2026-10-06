from decimal import Decimal
from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)

from django.db.models import Sum
from django.contrib import messages
from django.core.paginator import Paginator

from .models import Depense
from .forms import DepenseForm

from depot.models import Distribution
from personnel.models import Personnel
from users.models import AppUser

from audit.utils import enregistrer_action


# ============================================================
# LISTE DES DÉPENSES
# ============================================================

def depense_list(request):

    queryset = Depense.objects.select_related(
        "distribution",
        "enregistre_par",
    ).all()

    # --------------------------------------------------------
    # FILTRE TITRE
    # --------------------------------------------------------

    titre = request.GET.get(
        "titre",
        ""
    ).strip()

    # --------------------------------------------------------
    # FILTRE MONTANT
    # --------------------------------------------------------

    montant = request.GET.get(
        "montant",
        ""
    ).strip()

    # --------------------------------------------------------
    # Recherche par titre
    # --------------------------------------------------------

    if titre:
        queryset = queryset.filter(
            titre__icontains=titre
        )

    # --------------------------------------------------------
    # Recherche par montant
    # --------------------------------------------------------

    if montant:
        queryset = queryset.filter(
            montant__icontains=montant
        )

    # --------------------------------------------------------
    # Pagination
    # --------------------------------------------------------

    paginator = Paginator(
        queryset,
        10
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    return render(
        request,
        "depense/list.html",
        {
            "depenses": page_obj,
            "page_obj": page_obj,
            "titre": titre,
            "montant": montant,
        }
    )


# ============================================================
# AJOUT D'UNE DÉPENSE
# ============================================================

def depense_add(request):

    if request.method == "POST":

        form = DepenseForm(
            request.POST
        )

        if form.is_valid():

            # ------------------------------------------------
            # Création sans sauvegarde immédiate
            # ------------------------------------------------

            depense = form.save(
                commit=False
            )

            # =================================================
            # UTILISATEUR CONNECTÉ
            # =================================================

            user_id = request.session.get(
                "user_id"
            )

            if user_id:

                try:

                    depense.enregistre_par = (
                        AppUser.objects.get(
                            id=user_id
                        )
                    )

                except AppUser.DoesNotExist:

                    depense.enregistre_par = None

            # =================================================
            # PERSONNEL DE RÉFÉRENCE : GEGE
            # =================================================

            try:

                gege = Personnel.objects.get(
                    id=1
                )

            except Personnel.DoesNotExist:

                messages.error(
                    request,
                    "Le personnel de référence (Gege) est introuvable."
                )

                return render(
                    request,
                    "depense/form.html",
                    {
                        "form": form,
                        "action": "Ajouter",
                    }
                )

            # =================================================
            # DATE SAISIE PAR L'UTILISATEUR
            # =================================================

            date_depense = depense.date

            # =================================================
            # RECHERCHE DES DISTRIBUTIONS
            # =================================================
            #
            # On prend uniquement les distributions :
            #
            # distribution.date <= depense.date
            #
            # La plus ancienne est prioritaire.
            #
            # =================================================

            distributions = Distribution.objects.filter(
                distributeur=gege,
                depot__date__lte=date_depense,
            ).order_by(
                "depot__date",
                "id",
            )

            # =================================================
            # RECHERCHE D'UNE DISTRIBUTION SUFFISANTE
            # =================================================

            distribution_trouvee = None

            for distribution in distributions:

                # ------------------------------------------------
                # Total déjà dépensé sur cette distribution
                # ------------------------------------------------

                deja_depense = (
                    distribution.depenses.aggregate(
                        total=Sum("montant")
                    )["total"]
                    or Decimal("0")
                )

                # ------------------------------------------------
                # Montant encore disponible
                # ------------------------------------------------

                disponible = (
                    distribution.montant
                    - deja_depense
                )

                if disponible <= 0:
                    continue

                # ------------------------------------------------
                # Cette distribution peut payer toute la dépense
                # ------------------------------------------------

                if depense.montant <= disponible:

                    distribution_trouvee = distribution
                    break

            # =================================================
            # AUCUNE DISTRIBUTION SUFFISANTE
            # =================================================

            if distribution_trouvee is None:

                messages.error(
                    request,
                    "Montant disponible insuffisant pour la date de la dépense."
                )

                return render(
                    request,
                    "depense/form.html",
                    {
                        "form": form,
                        "action": "Ajouter",
                    }
                )

            # =================================================
            # AFFECTATION DE LA DISTRIBUTION
            # =================================================

            depense.distribution = distribution_trouvee

            depense.save()

            # =================================================
            # AUDIT CREATE
            # =================================================

            enregistrer_action(
                request,
                action="CREATE",
                table="Depense",
                objet_id=depense.id,
                nouvelle={
                    "titre": depense.titre,
                    "montant": str(depense.montant),
                    "date": str(depense.date),
                    "description": depense.description,
                    "distribution": (
                        depense.distribution_id
                        if depense.distribution
                        else None
                    ),
                },
                description="Création d'une dépense",
            )

            messages.success(
                request,
                "Dépense enregistrée avec succès."
            )

            return redirect(
                "depense:depense_list"
            )

    else:

        form = DepenseForm()

    # =========================================================
    # AFFICHAGE DU FORMULAIRE
    # =========================================================

    return render(
        request,
        "depense/form.html",
        {
            "form": form,
            "action": "Ajouter",
        }
    )


# ============================================================
# MODIFICATION D'UNE DÉPENSE
# ============================================================

def depense_edit(request, id):

    depense = get_object_or_404(
        Depense,
        id=id
    )

    # ========================================================
    # VÉRIFICATION DU PROPRIÉTAIRE
    # ========================================================

    user_id = request.session.get(
        "user_id"
    )

    if (
        not user_id
        or depense.enregistre_par_id != int(user_id)
    ):

        messages.error(
            request,
            "Vous ne pouvez pas modifier cette dépense."
        )

        return redirect(
            "depense:depense_list"
        )

    # ========================================================
    # ANCIENNES VALEURS
    # ========================================================

    ancienne = {
        "titre": depense.titre,
        "montant": str(depense.montant),
        "date": str(depense.date),
        "description": depense.description,
        "distribution": (
            depense.distribution_id
            if depense.distribution
            else None
        ),
    }

    # ========================================================
    # POST
    # ========================================================

    if request.method == "POST":

        form = DepenseForm(
            request.POST,
            instance=depense
        )

        if form.is_valid():

            # ------------------------------------------------
            # Récupérer les nouvelles valeurs
            # sans sauvegarder immédiatement
            # ------------------------------------------------

            depense_modifiee = form.save(
                commit=False
            )

            # =================================================
            # PERSONNEL DE RÉFÉRENCE
            # =================================================

            try:

                gege = Personnel.objects.get(
                    id=1
                )

            except Personnel.DoesNotExist:

                messages.error(
                    request,
                    "Le personnel de référence (Gege) est introuvable."
                )

                return render(
                    request,
                    "depense/form.html",
                    {
                        "form": form,
                        "action": "Modifier",
                    }
                )

            # =================================================
            # NOUVELLE DATE SAISIE
            # =================================================

            date_depense = depense_modifiee.date

            # =================================================
            # RECHERCHE DES DISTRIBUTIONS
            # =================================================

            distributions = Distribution.objects.filter(
                distributeur=gege,
                depot__date__lte=date_depense,
            ).order_by(
                "depot__date",
                "id",
            )

            distribution_trouvee = None

            # =================================================
            # RECHERCHE D'UNE DISTRIBUTION SUFFISANTE
            # =================================================

            for distribution in distributions:

                # ------------------------------------------------
                # IMPORTANT :
                # On exclut la dépense actuelle.
                # ------------------------------------------------

                deja_depense = (
                    distribution.depenses
                    .exclude(
                        id=depense.id
                    )
                    .aggregate(
                        total=Sum("montant")
                    )["total"]
                    or Decimal("0")
                )

                disponible = (
                    distribution.montant
                    - deja_depense
                )

                if disponible <= 0:
                    continue

                # ------------------------------------------------
                # Distribution suffisante
                # ------------------------------------------------

                if depense_modifiee.montant <= disponible:

                    distribution_trouvee = distribution
                    break

            # =================================================
            # AUCUNE DISTRIBUTION SUFFISANTE
            # =================================================

            if distribution_trouvee is None:

                messages.error(
                    request,
                    "Montant disponible insuffisant pour la nouvelle date ou le nouveau montant."
                )

                return render(
                    request,
                    "depense/form.html",
                    {
                        "form": form,
                        "action": "Modifier",
                    }
                )

            # =================================================
            # NOUVELLE DISTRIBUTION
            # =================================================

            depense_modifiee.distribution = (
                distribution_trouvee
            )

            # =================================================
            # SAUVEGARDE
            # =================================================

            depense_modifiee.save()

            # =================================================
            # NOUVELLES VALEURS
            # =================================================

            nouvelle = {
                "titre": depense_modifiee.titre,
                "montant": str(depense_modifiee.montant),
                "date": str(depense_modifiee.date),
                "description": depense_modifiee.description,
                "distribution": (
                    depense_modifiee.distribution_id
                    if depense_modifiee.distribution
                    else None
                ),
            }

            # =================================================
            # AUDIT UPDATE
            # =================================================

            enregistrer_action(
                request,
                action="UPDATE",
                table="Depense",
                objet_id=depense_modifiee.id,
                ancienne=ancienne,
                nouvelle=nouvelle,
                description="Modification d'une dépense",
            )

            messages.success(
                request,
                "Dépense modifiée avec succès."
            )

            return redirect(
                "depense:depense_list"
            )

    else:

        form = DepenseForm(
            instance=depense
        )

    # =========================================================
    # AFFICHAGE DU FORMULAIRE
    # =========================================================

    return render(
        request,
        "depense/form.html",
        {
            "form": form,
            "action": "Modifier",
        }
    )


# ============================================================
# SUPPRESSION D'UNE DÉPENSE
# ============================================================

def depense_delete(request, id):

    depense = get_object_or_404(
        Depense,
        id=id
    )

    # ========================================================
    # VÉRIFICATION DU PROPRIÉTAIRE
    # ========================================================

    user_id = request.session.get(
        "user_id"
    )

    if (
        not user_id
        or depense.enregistre_par_id != int(user_id)
    ):

        messages.error(
            request,
            "Vous ne pouvez pas supprimer cette dépense."
        )

        return redirect(
            "depense:depense_list"
        )

    # ========================================================
    # POST UNIQUEMENT
    # ========================================================

    if request.method != "POST":

        messages.error(
            request,
            "Méthode de suppression invalide."
        )

        return redirect(
            "depense:depense_list"
        )

    # ========================================================
    # ANCIENNES INFORMATIONS
    # ========================================================

    ancienne = {
        "titre": depense.titre,
        "montant": str(depense.montant),
        "date": str(depense.date),
        "description": depense.description,
        "distribution": (
            depense.distribution_id
            if depense.distribution
            else None
        ),
    }

    objet_id = depense.id

    # ========================================================
    # SUPPRESSION
    # ========================================================

    depense.delete()

    # ========================================================
    # AUDIT DELETE
    # ========================================================

    enregistrer_action(
        request,
        action="DELETE",
        table="Depense",
        objet_id=objet_id,
        ancienne=ancienne,
        nouvelle=None,
        description="Suppression d'une dépense",
    )

    messages.success(
        request,
        "Dépense supprimée avec succès."
    )

    return redirect(
        "depense:depense_list"
    )

