from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from .models import DepotSoc
from .forms import DepotSocForm

from users.models import AppUser
from audit.utils import enregistrer_action


# ============================================================
# UTILISATEUR CONNECTÉ
# ============================================================

def get_current_user(request):

    user_id = request.session.get("user_id")

    if not user_id:
        return None

    try:

        return AppUser.objects.get(
            id=int(user_id)
        )

    except (
        AppUser.DoesNotExist,
        ValueError,
        TypeError,
    ):

        return None


# ============================================================
# VÉRIFICATION SESSION
# ============================================================

def check_session(request):

    user = get_current_user(request)

    if not user:

        messages.error(
            request,
            "Votre session a expiré. Veuillez vous reconnecter."
        )

        return None

    return user


# ============================================================
# VALEURS POUR AUDIT
# ============================================================

def depot_soc_values(depot):

    return {
        "montant": str(depot.montant),
        "date": str(depot.date),
        "enregistreur": (
            depot.enregistreur.username
            if depot.enregistreur
            else None
        ),
    }


# ============================================================
# LISTE DES DÉPÔTS SOCIÉTÉ
# ============================================================

def depot_soc_list(request):

    user = check_session(request)

    if not user:
        return redirect("users:login")

    depots = (
        DepotSoc.objects
        .select_related("enregistreur")
        .all()
        .order_by("-date", "-id")
    )

    # --------------------------------------------------------
    # FILTRES
    # --------------------------------------------------------

    montant = request.GET.get(
        "montant",
        ""
    ).strip()

    date = request.GET.get(
        "date",
        ""
    ).strip()

    if montant:

        depots = depots.filter(
            montant__icontains=montant
        )

    if date:

        depots = depots.filter(
            date=date
        )

    # --------------------------------------------------------
    # TOTAL
    # --------------------------------------------------------

    total_depots = (
        depots.aggregate(
            total=Sum("montant")
        )["total"]
        or Decimal("0")
    )

    # --------------------------------------------------------
    # PAGINATION
    # --------------------------------------------------------

    paginator = Paginator(
        depots,
        12
    )

    page_number = request.GET.get(
        "page"
    )

    page_obj = paginator.get_page(
        page_number
    )

    # --------------------------------------------------------
    # PARAMÈTRES POUR PAGINATION
    # --------------------------------------------------------

    query_params = request.GET.copy()

    if "page" in query_params:

        query_params.pop("page")

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    context = {

        "depots": page_obj,

        "page_obj": page_obj,

        "montant": montant,

        "date": date,

        "total_depots": total_depots,

        "user": user,

        "role": request.session.get(
            "role"
        ),

        "query_params": query_params.urlencode(),
    }

    return render(
        request,
        "depotEntreprise/list.html",
        context
    )


# ============================================================
# AJOUT
# ============================================================

def depot_soc_add(request):

    user = check_session(request)

    if not user:
        return redirect("users:login")

    if request.method == "POST":

        form = DepotSocForm(
            request.POST
        )

        if form.is_valid():

            depot = form.save(
                commit=False
            )

            # Utilisateur connecté
            depot.enregistreur = user

            depot.save()

            # ------------------------------------------------
            # AUDIT
            # ------------------------------------------------

            nouvelle_valeur = depot_soc_values(
                depot
            )

            enregistrer_action(
                request,
                "CREATE",
                "DepotSoc",
                depot.id,
                None,
                nouvelle_valeur,
                "Ajout d'un dépôt société"
            )

            messages.success(
                request,
                "Dépôt société ajouté avec succès."
            )

            return redirect(
                "depotSoc:depot_soc_list"
            )

    else:

        form = DepotSocForm()

    return render(
        request,
        "depotEntreprise/form.html",
        {
            "form": form,
            "action": "Ajouter",
            "user": user,
            "role": request.session.get(
                "role"
            ),
        }
    )


# ============================================================
# DÉTAIL
# ============================================================

def depot_soc_detail(request, id):

    user = check_session(request)

    if not user:
        return redirect("users:login")

    depot = get_object_or_404(
        DepotSoc.objects.select_related(
            "enregistreur"
        ),
        id=id
    )

    return render(
        request,
        "depotEntreprise/detail.html",
        {
            "depot": depot,
            "user": user,
            "role": request.session.get(
                "role"
            ),
        }
    )


# ============================================================
# MODIFICATION
# ============================================================

def depot_soc_edit(request, id):

    user = check_session(request)

    if not user:
        return redirect("users:login")

    depot = get_object_or_404(
        DepotSoc,
        id=id
    )

    # Anciennes valeurs
    ancienne_valeur = depot_soc_values(
        depot
    )

    if request.method == "POST":

        form = DepotSocForm(
            request.POST,
            instance=depot
        )

        if form.is_valid():

            depot = form.save(
                commit=False
            )

            # L'utilisateur qui modifie
            depot.enregistreur = user

            depot.save()

            # ------------------------------------------------
            # NOUVELLES VALEURS
            # ------------------------------------------------

            nouvelle_valeur = depot_soc_values(
                depot
            )

            # ------------------------------------------------
            # AUDIT
            # ------------------------------------------------

            enregistrer_action(
                request,
                "UPDATE",
                "DepotSoc",
                depot.id,
                ancienne_valeur,
                nouvelle_valeur,
                "Modification d'un dépôt société"
            )

            messages.success(
                request,
                "Dépôt société modifié avec succès."
            )

            return redirect(
                "depotSoc:depot_soc_list"
            )

    else:

        form = DepotSocForm(
            instance=depot
        )

    return render(
        request,
        "depotEntreprise/form.html",
        {
            "form": form,
            "depot": depot,
            "action": "Modifier",
            "user": user,
            "role": request.session.get(
                "role"
            ),
        }
    )


# ============================================================
# SUPPRESSION
# ============================================================

def depot_soc_delete(request, id):

    user = check_session(request)

    if not user:
        return redirect("users:login")

    depot = get_object_or_404(
        DepotSoc,
        id=id
    )

    if request.method == "POST":

        # ----------------------------------------------------
        # ANCIENNES VALEURS POUR AUDIT
        # ----------------------------------------------------

        ancienne_valeur = depot_soc_values(
            depot
        )

        depot_id = depot.id

        # ----------------------------------------------------
        # AUDIT
        # ----------------------------------------------------

        enregistrer_action(
            request,
            "DELETE",
            "DepotSoc",
            depot_id,
            ancienne_valeur,
            None,
            "Suppression d'un dépôt société"
        )

        # ----------------------------------------------------
        # SUPPRESSION
        # ----------------------------------------------------

        depot.delete()

        messages.success(
            request,
            "Dépôt société supprimé avec succès."
        )

        return redirect(
            "depotSoc:depot_soc_list"
        )

    return render(
        request,
        "depotEntreprise/delete.html",
        {
            "depot": depot,
            "user": user,
            "role": request.session.get(
                "role"
            ),
        }
    )
