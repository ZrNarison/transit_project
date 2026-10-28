from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.dateparse import parse_date
from users.decorators import session_login_required
from audit.utils import enregistrer_action
from users.models import AppUser, H_AppUser

from .forms import DepotSocForm, H_DepotSocForm
from .models import DepotSoc, H_DepotSoc


# ============================================================
# UTILISATEUR CONNECTÉ GALAXY
# ============================================================
def get_current_user(request):
    user_id = request.session.get("user_id")

    if not user_id:
        return None

    try:
        return AppUser.objects.filter(pk=int(user_id)).first()
    except (ValueError, TypeError):
        return None


# ============================================================
# VÉRIFICATION SESSION GALAXY
# ============================================================
def check_session(request):
    user = get_current_user(request)

    if not user:
        messages.error(
            request,
            "Votre session a expiré. Veuillez vous reconnecter.",
        )

    return user


# ============================================================
# UTILISATEUR CONNECTÉ MCCR
# ============================================================
def _h_depot_soc_user(request):
    h_user_id = request.session.get("h_user_id")
    h_role = request.session.get("h_role")

    if not h_user_id or not h_role:
        return None

    try:
        return H_AppUser.objects.filter(pk=int(h_user_id)).first()
    except (ValueError, TypeError):
        return None


# ============================================================
# VALEURS POUR AUDIT GALAXY
# ============================================================
def depot_soc_values(depot):
    return {
        "id": depot.pk,
        "montant": str(depot.montant),
        "date": depot.date.isoformat() if depot.date else None,
        "enregistreur": (
            str(depot.enregistreur)
            if depot.enregistreur_id
            else None
        ),
    }


# ============================================================
# VALEURS POUR AUDIT MCCR
# ============================================================
def h_depot_soc_values(depot):
    return {
        "id": depot.pk,
        "montant": str(depot.montant),
        "date": depot.date.isoformat() if depot.date else None,
        "enregistreur": (
            str(depot.enregistreur)
            if depot.enregistreur_id
            else None
        ),
    }


# ============================================================
# OUTIL : FILTRER LES DÉPÔTS PAR MONTANT ET PAR DATE
# ============================================================
def _filtrer_depots(request, queryset):
    montant = request.GET.get("montant", "").strip()
    date = request.GET.get("date", "").strip()

    if montant:
        try:
            montant_decimal = Decimal(montant.replace(",", "."))

            if not montant_decimal.is_finite():
                raise InvalidOperation

            queryset = queryset.filter(montant=montant_decimal)

        except (InvalidOperation, ValueError):
            messages.warning(
                request,
                "Le montant saisi dans le filtre est invalide.",
            )

    if date:
        date_valide = parse_date(date)

        if date_valide:
            queryset = queryset.filter(date=date_valide)
        else:
            messages.warning(
                request,
                "La date saisie dans le filtre est invalide.",
            )

    return queryset, montant, date


# ============================================================
# OUTIL : PAGINATION ET PARAMÈTRES DE FILTRE
# ============================================================
def _paginer_depots(request, queryset, nombre_par_page=12):
    paginator = Paginator(queryset, nombre_par_page)
    page_obj = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)

    return page_obj, query_params.urlencode()


# ============================================================
# GALAXY : LISTE DES DÉPÔTS
# ============================================================
@session_login_required
def depot_soc_list(request):
    user = check_session(request)

    if not user:
        return redirect("users:login")

    depots = (
        DepotSoc.objects
        .select_related("enregistreur")
        .order_by("-date", "-pk")
    )

    depots, montant, date = _filtrer_depots(request, depots)

    total_depots = (
        depots.aggregate(total=Sum("montant"))["total"]
        or Decimal("0.00")
    )

    page_obj, query_params = _paginer_depots(request, depots)

    context = {
        "depots": page_obj,
        "page_obj": page_obj,
        "montant": montant,
        "date": date,
        "total_depots": total_depots,
        "user": user,
        "role": request.session.get("role"),
        "query_params": query_params,
    }

    return render(
        request,
        "depot/list.html",
        context,
    )


# ============================================================
# GALAXY : AJOUT D'UN DÉPÔT
# ============================================================
@session_login_required
def depot_soc_add(request):
    user = check_session(request)

    if not user:
        return redirect("users:login")

    if request.method == "POST":
        form = DepotSocForm(request.POST)

        if form.is_valid():
            depot = form.save(commit=False)
            depot.enregistreur = user
            depot.save()

            enregistrer_action(
                request,
                "CREATE",
                "DepotSoc",
                depot.pk,
                None,
                depot_soc_values(depot),
                "Ajout d'un dépôt Banque Construction GALAXY",
            )

            messages.success(
                request,
                "Dépôt GALAXY ajouté avec succès.",
            )

            return redirect("depotSoc:depot_soc_list")

    else:
        form = DepotSocForm()

    return render(
        request,
        "depot/form.html",
        {
            "form": form,
            "action": "Ajouter",
            "user": user,
            "role": request.session.get("role"),
        },
    )


# ============================================================
# GALAXY : DÉTAIL D'UN DÉPÔT
# ============================================================
@session_login_required
def depot_soc_detail(request, id):
    user = check_session(request)

    if not user:
        return redirect("users:login")

    depot = get_object_or_404(
        DepotSoc.objects.select_related("enregistreur"),
        pk=id,
    )

    return render(
        request,
        "depot/detail.html",
        {
            "depot": depot,
            "user": user,
            "role": request.session.get("role"),
        },
    )


# ============================================================
# GALAXY : MODIFICATION D'UN DÉPÔT
# ============================================================
@session_login_required
def depot_soc_edit(request, id):
    user = check_session(request)

    if not user:
        return redirect("users:login")

    depot = get_object_or_404(DepotSoc, pk=id)
    ancienne_valeur = depot_soc_values(depot)

    if request.method == "POST":
        form = DepotSocForm(request.POST, instance=depot)

        if form.is_valid():
            depot = form.save(commit=False)
            depot.save()

            enregistrer_action(
                request,
                "UPDATE",
                "DepotSoc",
                depot.pk,
                ancienne_valeur,
                depot_soc_values(depot),
                "Modification d'un dépôt Banque Construction GALAXY",
            )

            messages.success(
                request,
                "Dépôt GALAXY modifié avec succès.",
            )

            return redirect("depotSoc:depot_soc_list")

    else:
        form = DepotSocForm(instance=depot)

    return render(
        request,
        "depot/form.html",
        {
            "form": form,
            "depot": depot,
            "action": "Modifier",
            "user": user,
            "role": request.session.get("role"),
        },
    )


# ============================================================
# GALAXY : SUPPRESSION D'UN DÉPÔT
# ============================================================
@session_login_required
def depot_soc_delete(request, id):
    user = check_session(request)

    if not user:
        return redirect("users:login")

    depot = get_object_or_404(DepotSoc, pk=id)

    if request.method == "POST":
        ancienne_valeur = depot_soc_values(depot)
        depot_id = depot.pk

        enregistrer_action(
            request,
            "DELETE",
            "DepotSoc",
            depot_id,
            ancienne_valeur,
            None,
            "Suppression d'un dépôt Banque Construction GALAXY",
        )

        depot.delete()

        messages.success(
            request,
            "Dépôt GALAXY supprimé avec succès.",
        )

        return redirect("depotSoc:depot_soc_list")

    return render(
        request,
        "depot/delete.html",
        {
            "depot": depot,
            "user": user,
            "role": request.session.get("role"),
        },
    )


# ============================================================
# MCCR : LISTE DES DÉPÔTS BANQUE CONSTRUCTION
# ============================================================
@session_login_required
def h_depot_soc_list(request):
    user = _h_depot_soc_user(request)

    if not user:
        messages.warning(
            request,
            "Votre session MCCR a expiré. Veuillez vous reconnecter.",
        )
        return redirect("users:login")

    h_depots = (
        H_DepotSoc.objects
        .select_related("enregistreur")
        .order_by("-date", "-pk")
    )

    h_depots, montant, date = _filtrer_depots(
        request,
        h_depots,
    )

    total_montant = (
        h_depots.aggregate(total=Sum("montant"))["total"]
        or Decimal("0.00")
    )

    page_obj, query_params = _paginer_depots(
        request,
        h_depots,
    )

    context = {
        "h_depots": page_obj,
        "depots": page_obj,
        "page_obj": page_obj,
        "montant": montant,
        "date": date,
        "total_montant": total_montant,
        "total_depots": total_montant,
        "query_params": query_params,
        "user": user,
        "role": request.session.get("h_role"),
    }

    return render(
        request,
        "depot/h_list.html",
        context,
    )


# ============================================================
# MCCR : AJOUT D'UN DÉPÔT
# ============================================================
@session_login_required
def h_depot_soc_add(request):
    user = _h_depot_soc_user(request)

    if not user:
        messages.warning(
            request,
            "Votre session MCCR a expiré. Veuillez vous reconnecter.",
        )
        return redirect("users:login")

    if request.method == "POST":
        form = H_DepotSocForm(request.POST)

        if form.is_valid():
            h_depot = form.save(commit=False)
            h_depot.enregistreur = user
            h_depot.save()

            enregistrer_action(
                request,
                "CREATE",
                "H_DepotSoc",
                h_depot.pk,
                None,
                h_depot_soc_values(h_depot),
                "Ajout d'un dépôt Banque Construction MCCR",
            )

            messages.success(
                request,
                "Dépôt MCCR ajouté avec succès.",
            )

            return redirect("depotSoc:h_depot_soc_list")

    else:
        form = H_DepotSocForm()

    return render(
        request,
        "depot/h_form.html",
        {
            "form": form,
            "action": "Ajouter",
            "user": user,
            "role": request.session.get("h_role"),
        },
    )


# ============================================================
# MCCR : DÉTAIL D'UN DÉPÔT
# ============================================================
@session_login_required
def h_depot_soc_detail(request, id):
    user = _h_depot_soc_user(request)

    if not user:
        messages.warning(
            request,
            "Votre session MCCR a expiré. Veuillez vous reconnecter.",
        )
        return redirect("users:login")

    h_depot = get_object_or_404(
        H_DepotSoc.objects.select_related("enregistreur"),
        pk=id,
    )

    return render(
        request,
        "depot/detail.html",
        {
            "depot": h_depot,
            "user": user,
            "role": request.session.get("h_role"),
        },
    )


# ============================================================
# MCCR : MODIFICATION D'UN DÉPÔT
# ============================================================
@session_login_required
def h_depot_soc_edit(request, id):
    user = _h_depot_soc_user(request)

    if not user:
        messages.warning(
            request,
            "Votre session MCCR a expiré. Veuillez vous reconnecter.",
        )
        return redirect("users:login")

    h_depot = get_object_or_404(H_DepotSoc, pk=id)
    ancienne_valeur = h_depot_soc_values(h_depot)

    if request.method == "POST":
        form = H_DepotSocForm(
            request.POST,
            instance=h_depot,
        )

        if form.is_valid():
            h_depot = form.save(commit=False)

            # Conserver l'enregistreur initial du dépôt.
            # La modification ne remplace pas son créateur.
            h_depot.save()

            enregistrer_action(
                request,
                "UPDATE",
                "H_DepotSoc",
                h_depot.pk,
                ancienne_valeur,
                h_depot_soc_values(h_depot),
                "Modification d'un dépôt Banque Construction MCCR",
            )

            messages.success(
                request,
                "Dépôt MCCR modifié avec succès.",
            )

            return redirect("depotSoc:h_depot_soc_list")

    else:
        form = H_DepotSocForm(instance=h_depot)

    return render(
        request,
        "depot/h_form.html",
        {
            "form": form,
            "depot": h_depot,
            "action": "Modifier",
            "user": user,
            "role": request.session.get("h_role"),
        },
    )


# ============================================================
# MCCR : SUPPRESSION D'UN DÉPÔT
# ============================================================
@session_login_required
def h_depot_soc_delete(request, id):
    user = _h_depot_soc_user(request)

    if not user:
        messages.warning(
            request,
            "Votre session MCCR a expiré. Veuillez vous reconnecter.",
        )
        return redirect("users:login")

    h_depot = get_object_or_404(H_DepotSoc, pk=id)

    if request.method == "POST":
        ancienne_valeur = h_depot_soc_values(h_depot)
        h_depot_id = h_depot.pk

        enregistrer_action(
            request,
            "DELETE",
            "H_DepotSoc",
            h_depot_id,
            ancienne_valeur,
            None,
            "Suppression d'un dépôt Banque Construction MCCR",
        )

        h_depot.delete()

        messages.success(
            request,
            "Dépôt MCCR supprimé avec succès.",
        )

        return redirect("depotSoc:h_depot_soc_list")

    return render(
        request,
        "depot/delete.html",
        {
            "depot": h_depot,
            "user": user,
            "role": request.session.get("h_role"),
        },
    )