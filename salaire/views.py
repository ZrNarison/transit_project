from django.contrib import messages
from django.core.paginator import Paginator
from decimal import Decimal
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from users.models import AppUser, H_AppUser
from personnel.models import Personnel, H_Personnel
from .forms import SalaireForm, H_SalaireForm
from .models import Salaire, H_Salaire, recalculer_situation_personnel,h_recalculer_situation_personnel
from django.views.decorators.http import require_http_methods
from users.decorators import session_login_required
# =============================================================
# UTILISATEUR CONNECTÉ
# =============================================================
def get_current_user(request):

    user_id = request.session.get("user_id")

    if not user_id:
        return None

    return AppUser.objects.filter(pk=user_id).first()


# =============================================================
# VÉRIFICATION SESSION
# =============================================================
def check_session(request):

    user = get_current_user(request)

    if not user:
        return None

    return user


# =============================================================
# LISTE DES SALAIRES
# =============================================================
@session_login_required
def salaire_list(request):

    utilisateur = check_session(request)

    if not utilisateur:

        return redirect("users:login")

    role = request.session.get("role")

    # =========================================================
    # SALAIRES
    # =========================================================

    salaires = Salaire.objects.select_related(
        "personnel",
        "enregistreur",
    ).all()

    # =========================================================
    # FILTRE ROLE
    # =========================================================

    if role == "UserMica":

        salaires = salaires.filter(personnel__typeTravail="Mica")

    elif role == "UserEntreprise":

        salaires = salaires.filter(personnel__typeTravail="Construction")

    # =========================================================
    # FILTRE PERSONNEL
    # =========================================================

    personnel_recherche = request.GET.get("personnel", "").strip()

    if personnel_recherche:

        salaires = salaires.filter(
            Q(personnel__nom__icontains=(personnel_recherche))
            | Q(personnel__prenom__icontains=(personnel_recherche))
        )

    # =========================================================
    # FILTRE MONTANT
    # =========================================================

    montant = request.GET.get("montant", "").strip()

    if montant:

        try:

            salaires = salaires.filter(montant=montant)

        except (ValueError, TypeError):

            pass

    # =========================================================
    # FILTRE DATE
    # =========================================================

    date = request.GET.get("date", "").strip()

    if date:

        salaires = salaires.filter(date_paiement=date)

    # =========================================================
    # TOTAL SALAIRES
    # =========================================================

    total_salaires = salaires.aggregate(total=Sum("montant"))["total"] or 0

    # =========================================================
    # TOTAL RESTE
    # =========================================================

    total_reste = salaires.aggregate(total=Sum("reste"))["total"] or 0

    # =========================================================
    # TOTAL TROP-PERÇU
    # =========================================================

    total_trop_percu = salaires.aggregate(total=Sum("trop_percu"))["total"] or 0

    # =========================================================
    # PAGINATION
    # =========================================================

    paginator = Paginator(salaires, 10)

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(page_number)

    # =========================================================
    # PERSONNELS POUR FILTRE
    # =========================================================

    from personnel.models import Personnel

    personnels = Personnel.objects.all().order_by(
        "nom",
        "prenom",
    )

    if role == "UserMica":

        personnels = personnels.filter(typeTravail="Mica")

    elif role == "UserEntreprise":

        personnels = personnels.filter(typeTravail="Construction")

    # =========================================================
    # PARAMÈTRES POUR PAGINATION
    # =========================================================

    query_params = request.GET.copy()

    if "page" in query_params:
        query_params.pop("page")

    query_params = query_params.urlencode()

    # =========================================================
    # RENDU
    # =========================================================

    return render(
        request,
        "salaire/list.html",
        {
            "salaires": page_obj,
            "page_obj": page_obj,
            "personnels": personnels,
            "total_salaires": (total_salaires),
            "total_reste": (total_reste),
            "total_trop_percu": (total_trop_percu),
            "role": role,
            "utilisateur": utilisateur,
            "personnel": (personnel_recherche),
            "montant": montant,
            "date": date,
            "query_params": (query_params),
        },
    )


# =============================================================
# AJOUT SALAIRE
# =============================================================
@session_login_required
def salaire_add(request):

    utilisateur = check_session(request)

    if not utilisateur:

        return redirect("users:login")

    role = request.session.get("role")

    # =========================================================
    # POST
    # =========================================================

    if request.method == "POST":

        form = SalaireForm(
            request.POST,
            role=role,
        )

        if form.is_valid():

            with transaction.atomic():

                salaire = form.save(commit=False)

                # ---------------------------------------------
                # Enregistreur
                # ---------------------------------------------

                salaire.enregistreur = utilisateur

                salaire.save()

                # ---------------------------------------------
                # Recalcul complet
                # ---------------------------------------------

                if salaire.personnel:

                    recalculer_situation_personnel(salaire.personnel)

            messages.success(request, "Le salaire a été enregistré avec succès.")

            return redirect("salaire:salaire_list")

    # =========================================================
    # GET
    # =========================================================

    else:

        form = SalaireForm(role=role)

    # =========================================================
    # RENDU
    # =========================================================

    return render(
        request,
        "salaire/form.html",
        {
            "form": form,
            "action": "Ajouter",
            "role": role,
        },
    )


# =============================================================
# MODIFICATION SALAIRE
# Compatible avec :
# =============================================================
@session_login_required
def salaire_edit(request,id=None,pk=None,):

    utilisateur = check_session(request)

    if not utilisateur:

        return redirect("users:login")

    role = request.session.get("role")

    # =========================================================
    # IDENTIFIANT
    # =========================================================

    salaire_id = id if id is not None else pk

    if salaire_id is None:

        messages.error(request, "Identifiant du salaire manquant.")

        return redirect("salaire:salaire_list")

    # =========================================================
    # SALAIRE
    # =========================================================

    salaire = get_object_or_404(
        Salaire.objects.select_related(
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

    if salaire.enregistreur_id != utilisateur.id:

        messages.error(request, "Vous n'êtes pas autorisé à modifier ce salaire.")

        return redirect("salaire:salaire_list")

    # =========================================================
    # ANCIEN PERSONNEL
    # =========================================================

    ancien_personnel = salaire.personnel

    # =========================================================
    # POST
    # =========================================================

    if request.method == "POST":

        form = SalaireForm(
            request.POST,
            instance=salaire,
            role=role,
        )

        if form.is_valid():

            with transaction.atomic():

                salaire_modifie = form.save(commit=False)

                # ---------------------------------------------
                # L'enregistreur ne change pas
                # ---------------------------------------------

                salaire_modifie.enregistreur = utilisateur

                salaire_modifie.save()

                # ---------------------------------------------
                # Nouveau personnel
                # ---------------------------------------------

                nouveau_personnel = salaire_modifie.personnel

                # ---------------------------------------------
                # Personnel inchangé
                # ---------------------------------------------

                if (
                    ancien_personnel
                    and nouveau_personnel
                    and ancien_personnel.id == nouveau_personnel.id
                ):

                    recalculer_situation_personnel(nouveau_personnel)

                # ---------------------------------------------
                # Personnel changé
                # ---------------------------------------------

                else:

                    if ancien_personnel:

                        recalculer_situation_personnel(ancien_personnel)

                    if nouveau_personnel:

                        recalculer_situation_personnel(nouveau_personnel)

            messages.success(request, "Le salaire a été modifié avec succès.")

            return redirect("salaire:salaire_list")

    # =========================================================
    # GET
    # =========================================================

    else:

        form = SalaireForm(
            instance=salaire,
            role=role,
        )

    # =========================================================
    # RENDU
    # =========================================================

    return render(
        request,
        "salaire/form.html",
        {
            "form": form,
            "action": "Modifier",
            "salaire": salaire,
            "role": role,
        },
    )


# =============================================================
# SUPPRESSION SALAIRE
# Compatible avec id ET pk.
# =============================================================
@session_login_required
def salaire_delete(request,id=None,pk=None,):
    utilisateur = check_session(request)

    if not utilisateur:

        return redirect("users:login")

    # =========================================================
    # IDENTIFIANT
    # =========================================================

    salaire_id = id if id is not None else pk

    if salaire_id is None:

        messages.error(request, "Identifiant du salaire manquant.")

        return redirect("salaire:salaire_list")

    # =========================================================
    # SALAIRE
    # =========================================================

    salaire = get_object_or_404(
        Salaire.objects.select_related(
            "personnel",
            "enregistreur",
        ),
        pk=salaire_id,
    )

    # =========================================================
    # AUTORISATION
    # =========================================================

    if salaire.enregistreur_id != utilisateur.id:

        messages.error(request, "Vous n'êtes pas autorisé à supprimer ce salaire.")

        return redirect("salaire:salaire_list")

    # =========================================================
    # PERSONNEL
    # =========================================================

    personnel = salaire.personnel

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

                recalculer_situation_personnel(personnel)

        messages.success(request, "Le salaire a été supprimé avec succès.")

        return redirect("salaire:salaire_list")

    # =========================================================
    # CONFIRMATION
    # =========================================================

    return render(
        request,
        "salaire/confirm_delete.html",
        {
            "salaire": salaire,
        },
    )


# ===========================================================
#  SALAIRE ENTREPRISE H
# ===========================================================
@session_login_required
def _get_h_salaire_user(request):
    """Récupère exclusivement l'utilisateur MCCR connecté."""
    h_user_id = request.session.get("h_user_id")

    if not h_user_id:
        return None

    return H_AppUser.objects.filter(pk=h_user_id).first()


# ===========================================================
# LISTE DES SALAIRES MCCR
# ===========================================================
@session_login_required
def h_salaire_list(request):
    utilisateur = _get_h_salaire_user(request)

    if not utilisateur:
        messages.warning(
            request,
            "Votre session MCCR a expiré. Veuillez vous reconnecter.",
        )
        return redirect("users:login")

    role = request.session.get("h_role", "")

    salaires = H_Salaire.objects.select_related(
        "personnel",
        "enregistreur",
    ).all()

    # -------------------------------------------------------
    # FILTRE PERSONNEL
    # -------------------------------------------------------

    personnel_recherche = request.GET.get("personnel", "").strip()

    if personnel_recherche:
        salaires = salaires.filter(
            Q(personnel__nom__icontains=personnel_recherche)
            | Q(personnel__prenom__icontains=personnel_recherche)
        )

    # -------------------------------------------------------
    # FILTRE MONTANT
    # -------------------------------------------------------

    montant = request.GET.get("montant", "").strip()

    if montant:
        try:
            montant_decimal = Decimal(montant.replace(",", "."))
            salaires = salaires.filter(montant=montant_decimal)
        except (InvalidOperation, ValueError, TypeError):
            messages.warning(request, "Le montant du filtre est invalide.")

    # -------------------------------------------------------
    # FILTRE DATE DE PAIEMENT
    # -------------------------------------------------------

    date = request.GET.get("date", "").strip()

    if date:
        date_valide = parse_date(date)

        if date_valide:
            salaires = salaires.filter(date_paiement=date_valide)
        else:
            messages.warning(request, "La date du filtre est invalide.")

    # -------------------------------------------------------
    # TOTAUX SUR LES RÉSULTATS FILTRÉS
    # -------------------------------------------------------

    totaux = salaires.aggregate(
        total_salaires=Sum("montant"),
        total_reste=Sum("reste"),
        total_trop_percu=Sum("trop_percu"),
    )

    total_salaires = totaux["total_salaires"] or Decimal("0")
    total_reste = totaux["total_reste"] or Decimal("0")
    total_trop_percu = totaux["total_trop_percu"] or Decimal("0")

    # -------------------------------------------------------
    # PAGINATION
    # -------------------------------------------------------

    paginator = Paginator(salaires, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    # -------------------------------------------------------
    # PERSONNELS MCCR UNIQUEMENT
    # -------------------------------------------------------

    personnels = H_Personnel.objects.all().order_by("nom", "prenom")

    # -------------------------------------------------------
    # PARAMÈTRES DE PAGINATION
    # -------------------------------------------------------

    query_params = request.GET.copy()
    query_params.pop("page", None)
    query_params = query_params.urlencode()

    return render(
        request,
        "salaire/h_list.html",
        {
            "h_salaires": page_obj,
            "salaires": page_obj,
            "page_obj": page_obj,
            "personnels": personnels,
            "total_salaires": total_salaires,
            "total_reste": total_reste,
            "total_trop_percu": total_trop_percu,
            "role": role,
            "utilisateur": utilisateur,
            "personnel": personnel_recherche,
            "personnel_recherche": personnel_recherche,
            "montant": montant,
            "date": date,
            "query_params": query_params,
        },
    )


# ===========================================================
# AJOUT SALAIRE MCCR
# ===========================================================
@session_login_required
def h_salaire_add(request):
    utilisateur = _get_h_salaire_user(request)

    if not utilisateur:
        messages.warning(
            request,
            "Votre session MCCR a expiré. Veuillez vous reconnecter.",
        )
        return redirect("users:login")

    role = request.session.get("h_role", "")

    if request.method == "POST":
        form = H_SalaireForm(request.POST, role=role)

        if form.is_valid():
            with transaction.atomic():
                salaire = form.save(commit=False)

                # Utilisateur MCCR, jamais AppUser GALAXY.
                salaire.enregistreur = utilisateur
                salaire.save()

                if salaire.personnel_id:
                    h_recalculer_situation_personnel(salaire.personnel)

            messages.success(
                request,
                "Le salaire MCCR a été enregistré avec succès.",
            )
            return redirect("salaire:h_salaire_list")
    else:
        form = H_SalaireForm(role=role)

    return render(
        request,
        "salaire/h_form.html",
        {
            "form": form,
            "action": "Ajouter",
            "role": role,
            "utilisateur": utilisateur,
        },
    )


# ===========================================================
# MODIFICATION SALAIRE MCCR
# ===========================================================
@session_login_required
def h_salaire_edit(request, id=None, pk=None):
    utilisateur = _get_h_salaire_user(request)

    if not utilisateur:
        messages.warning(
            request,
            "Votre session MCCR a expiré. Veuillez vous reconnecter.",
        )
        return redirect("users:login")

    salaire_id = id if id is not None else pk

    if salaire_id is None:
        messages.error(request, "Identifiant du salaire manquant.")
        return redirect("salaire:h_salaire_list")

    salaire = get_object_or_404(
        H_Salaire.objects.select_related("personnel", "enregistreur"),
        pk=salaire_id,
    )

    # Seul l'enregistreur MCCR peut modifier ce salaire.
    if salaire.enregistreur_id != utilisateur.pk:
        messages.error(
            request,
            "Vous n'êtes pas autorisé à modifier ce salaire MCCR.",
        )
        return redirect("salaire:h_salaire_list")

    ancien_personnel = salaire.personnel

    if request.method == "POST":
        form = H_SalaireForm(
            request.POST,
            instance=salaire,
            role=request.session.get("h_role", ""),
        )

        if form.is_valid():
            with transaction.atomic():
                salaire_modifie = form.save(commit=False)

                # L'enregistreur d'origine ne change pas.
                salaire_modifie.enregistreur = utilisateur
                salaire_modifie.save()

                nouveau_personnel = salaire_modifie.personnel

                if (
                    ancien_personnel
                    and nouveau_personnel
                    and ancien_personnel.pk == nouveau_personnel.pk
                ):
                    h_recalculer_situation_personnel(nouveau_personnel)
                else:
                    if ancien_personnel:
                        h_recalculer_situation_personnel(ancien_personnel)

                    if nouveau_personnel:
                        h_recalculer_situation_personnel(nouveau_personnel)

            messages.success(
                request,
                "Le salaire MCCR a été modifié avec succès.",
            )
            return redirect("salaire:h_salaire_list")
    else:
        form = H_SalaireForm(
            instance=salaire,
            role=request.session.get("h_role", ""),
        )

    return render(
        request,
        "salaire/h_form.html",
        {
            "form": form,
            "action": "Modifier",
            "salaire": salaire,
            "role": request.session.get("h_role", ""),
            "utilisateur": utilisateur,
        },
    )


# ===========================================================
# SUPPRESSION SALAIRE MCCR
# Compatible avec id et pk
# ===========================================================
@session_login_required
@require_http_methods(["GET", "POST"])
def h_salaire_delete(request, id=None, pk=None):
    # -------------------------------------------------------
    # SESSION MCCR UNIQUEMENT
    # -------------------------------------------------------
    utilisateur = _get_h_salaire_user(request)

    if not utilisateur:
        messages.warning(
            request,
            "Votre session MCCR a expiré. Veuillez vous reconnecter.",
        )
        return redirect("users:login")

    # -------------------------------------------------------
    # IDENTIFIANT
    # -------------------------------------------------------
    salaire_id = id if id is not None else pk

    if salaire_id is None:
        messages.error(request, "Identifiant du salaire manquant.")
        return redirect("salaire:h_salaire_list")

    # -------------------------------------------------------
    # RÉCUPÉRATION DU SALAIRE MCCR
    # Le champ correct est « personnel ».
    # -------------------------------------------------------
    h_salaire = get_object_or_404(
        H_Salaire.objects.select_related(
            "personnel",
            "enregistreur",
        ),
        pk=salaire_id,
    )

    # -------------------------------------------------------
    # AUTORISATION
    # Seul l'enregistreur de ce salaire peut le supprimer.
    # -------------------------------------------------------
    if h_salaire.enregistreur_id != utilisateur.pk:
        messages.error(
            request,
            "Vous n'êtes pas autorisé à supprimer ce salaire MCCR.",
        )
        return redirect("salaire:h_salaire_list")

    # -------------------------------------------------------
    # PERSONNEL ASSOCIÉ
    # -------------------------------------------------------
    personnel = h_salaire.personnel

    # -------------------------------------------------------
    # SUPPRESSION ET RECALCUL
    # -------------------------------------------------------
    if request.method == "POST":
        with transaction.atomic():
            h_salaire.delete()

            if personnel:
                h_recalculer_situation_personnel(personnel)

        messages.success(
            request,
            "Le salaire MCCR a été supprimé avec succès.",
        )

        return redirect("salaire:h_salaire_list")

    # -------------------------------------------------------
    # CONFIRMATION
    # -------------------------------------------------------
    return render(
        request,
        "salaire/confirm_delete.html",
        {
            "salaire": h_salaire,
            "retour_url": "salaire:h_salaire_list",
        },
    )