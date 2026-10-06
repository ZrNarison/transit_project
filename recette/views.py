from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from .models import Recette
from .forms import RecetteForm

from users.models import AppUser

from audit.utils import enregistrer_action


# ============================================================
# UTILISATEUR CONNECTÉ
# ============================================================

def get_current_user(request):
    """
    Récupère l'utilisateur connecté à partir de la session.
    """

    user_id = request.session.get("user_id")

    if not user_id:
        return None

    try:
        return AppUser.objects.get(id=int(user_id))

    except (AppUser.DoesNotExist, ValueError, TypeError):
        return None


# ============================================================
# VÉRIFICATION DE SESSION
# ============================================================

def check_session(request):
    """
    Vérifie que l'utilisateur possède une session valide.
    """

    user = get_current_user(request)

    if not user:
        messages.error(
            request,
            "Votre session a expiré. Veuillez vous reconnecter."
        )
        return None

    return user


# ============================================================
# VÉRIFICATION DE PROPRIÉTÉ
# ============================================================

def is_recette_owner(recette, user):
    """
    Vérifie si l'utilisateur connecté est l'enregistreur
    de la recette.
    """

    if not recette.enregistreur:
        return False

    return recette.enregistreur.id == user.id


# ============================================================
# LISTE DES RECETTES
# ============================================================

def recette_list(request):

    user = check_session(request)

    if not user:
        return redirect("users:login")

    # --------------------------------------------------------
    # RÉCUPÉRATION DES RECETTES
    # --------------------------------------------------------

    queryset = (
        Recette.objects
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

    type_virement = request.GET.get(
        "type_virement",
        ""
    ).strip()

    date = request.GET.get(
        "date",
        ""
    ).strip()

    source = request.GET.get(
        "source",
        ""
    ).strip()

    if montant:
        queryset = queryset.filter(
            montant__icontains=montant
        )

    if type_virement:
        queryset = queryset.filter(
            type_virement__icontains=type_virement
        )

    if date:
        queryset = queryset.filter(
            date__icontains=date
        )

    if source:
        queryset = queryset.filter(
            source__icontains=source
        )

    # --------------------------------------------------------
    # TOTAL DES RECETTES
    # --------------------------------------------------------

    total_recettes = (
        queryset.aggregate(
            total=Sum("montant")
        )["total"]
        or Decimal("0")
    )

    # --------------------------------------------------------
    # PAGINATION
    # --------------------------------------------------------

    paginator = Paginator(
        queryset,
        12
    )

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(
        page_number
    )

    # --------------------------------------------------------
    # CONSERVATION DES FILTRES
    # --------------------------------------------------------

    query_params = request.GET.copy()

    if "page" in query_params:
        query_params.pop("page")

    # --------------------------------------------------------
    # CONTEXT
    # --------------------------------------------------------

    context = {
        "recettes": page_obj,
        "page_obj": page_obj,

        "montant": montant,
        "type_virement": type_virement,
        "date": date,
        "source": source,

        "total_recettes": total_recettes,

        "user": user,
        "role": request.session.get("role"),

        "query_params": query_params.urlencode(),
    }

    return render(
        request,
        "recette/list.html",
        context
    )


# ============================================================
# AJOUT D'UNE RECETTE
# ============================================================

def recette_add(request):

    user = check_session(request)

    if not user:
        return redirect("users:login")

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == "POST":

        form = RecetteForm(
            request.POST
        )

        if form.is_valid():

            recette = form.save(
                commit=False
            )

            # ------------------------------------------------
            # ENREGISTREUR
            # ------------------------------------------------

            recette.enregistreur = user

            recette.save()

            # ------------------------------------------------
            # NOUVELLES VALEURS
            # ------------------------------------------------

            nouvelle_valeur = {

                "montant": str(
                    recette.montant
                ),

                "type_virement": (
                    recette.type_virement
                ),

                "date": str(
                    recette.date
                ),

                "source": (
                    recette.source
                ),

                "enregistreur": (
                    recette.enregistreur.username
                    if recette.enregistreur
                    else None
                ),
            }

            # ------------------------------------------------
            # AUDIT
            # ------------------------------------------------

            enregistrer_action(
                request,
                "CREATE",
                "Recette",
                recette.id,
                None,
                nouvelle_valeur,
                "Ajout d'une recette"
            )

            messages.success(
                request,
                "Recette ajoutée avec succès."
            )

            return redirect(
                "recette:recette_list"
            )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    else:

        form = RecetteForm()

    return render(
        request,
        "recette/form.html",
        {
            "form": form,
            "action": "Ajouter",
            "user": user,
            "role": request.session.get("role"),
        }
    )


# ============================================================
# DÉTAIL D'UNE RECETTE
# ============================================================

def recette_detail(request, id):

    user = check_session(request)

    if not user:
        return redirect("users:login")

    recette = get_object_or_404(
        Recette.objects.select_related(
            "enregistreur"
        ),
        id=id
    )

    return render(
        request,
        "recette/detail.html",
        {
            "recette": recette,
            "user": user,
            "role": request.session.get("role"),
        }
    )


# ============================================================
# MODIFICATION D'UNE RECETTE
# SEUL L'ENREGISTREUR PEUT MODIFIER
# ============================================================

def recette_edit(request, id):

    user = check_session(request)

    if not user:
        return redirect("users:login")

    recette = get_object_or_404(
        Recette.objects.select_related(
            "enregistreur"
        ),
        id=id
    )

    # --------------------------------------------------------
    # VÉRIFICATION DU PROPRIÉTAIRE
    # --------------------------------------------------------

    if not is_recette_owner(recette, user):

        messages.error(
            request,
            "Vous n'êtes pas autorisé à modifier cette recette. "
            "Seul son enregistreur peut la modifier."
        )

        return redirect(
            "recette:recette_list"
        )

    # --------------------------------------------------------
    # ANCIENNES VALEURS
    # --------------------------------------------------------

    ancienne_valeur = {

        "montant": str(
            recette.montant
        ),

        "type_virement": (
            recette.type_virement
        ),

        "date": str(
            recette.date
        ),

        "source": (
            recette.source
        ),

        "enregistreur": (
            recette.enregistreur.username
            if recette.enregistreur
            else None
        ),
    }

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == "POST":

        form = RecetteForm(
            request.POST,
            instance=recette
        )

        if form.is_valid():

            recette = form.save(
                commit=False
            )

            # ------------------------------------------------
            # IMPORTANT
            # ------------------------------------------------
            # On conserve l'enregistreur original.
            #
            # Il ne devient PAS le dernier utilisateur
            # ayant modifié la recette.
            # ------------------------------------------------

            recette.enregistreur = user

            recette.save()

            # ------------------------------------------------
            # NOUVELLES VALEURS
            # ------------------------------------------------

            nouvelle_valeur = {

                "montant": str(
                    recette.montant
                ),

                "type_virement": (
                    recette.type_virement
                ),

                "date": str(
                    recette.date
                ),

                "source": (
                    recette.source
                ),

                "enregistreur": (
                    recette.enregistreur.username
                    if recette.enregistreur
                    else None
                ),
            }

            # ------------------------------------------------
            # AUDIT
            # ------------------------------------------------

            enregistrer_action(
                request,
                "UPDATE",
                "Recette",
                recette.id,
                ancienne_valeur,
                nouvelle_valeur,
                "Modification d'une recette"
            )

            messages.success(
                request,
                "Recette modifiée avec succès."
            )

            return redirect(
                "recette:recette_list"
            )

    # --------------------------------------------------------
    # GET
    # --------------------------------------------------------

    else:

        form = RecetteForm(
            instance=recette
        )

    return render(
        request,
        "recette/form.html",
        {
            "form": form,
            "recette": recette,
            "action": "Modifier",
            "user": user,
            "role": request.session.get("role"),
        }
    )


# ============================================================
# SUPPRESSION D'UNE RECETTE
# SEUL L'ENREGISTREUR PEUT SUPPRIMER
# ============================================================

def recette_delete(request, id):

    user = check_session(request)

    if not user:
        return redirect("users:login")

    recette = get_object_or_404(
        Recette.objects.select_related(
            "enregistreur"
        ),
        id=id
    )

    # --------------------------------------------------------
    # VÉRIFICATION DU PROPRIÉTAIRE
    # --------------------------------------------------------

    if not is_recette_owner(recette, user):

        messages.error(
            request,
            "Vous n'êtes pas autorisé à supprimer cette recette. "
            "Seul son enregistreur peut la supprimer."
        )

        return redirect(
            "recette:recette_list"
        )

    # --------------------------------------------------------
    # POST
    # --------------------------------------------------------

    if request.method == "POST":

        # ----------------------------------------------------
        # SAUVEGARDE DES DONNÉES AVANT SUPPRESSION
        # ----------------------------------------------------

        ancienne_valeur = {

            "montant": str(
                recette.montant
            ),

            "type_virement": (
                recette.type_virement
            ),

            "date": str(
                recette.date
            ),

            "source": (
                recette.source
            ),

            "enregistreur": (
                recette.enregistreur.username
                if recette.enregistreur
                else None
            ),
        }

        recette_id = recette.id

        # ----------------------------------------------------
        # AUDIT
        # ----------------------------------------------------

        enregistrer_action(
            request,
            "DELETE",
            "Recette",
            recette_id,
            ancienne_valeur,
            None,
            "Suppression d'une recette"
        )

        # ----------------------------------------------------
        # SUPPRESSION
        # ----------------------------------------------------

        recette.delete()

        messages.success(
            request,
            "Recette supprimée avec succès."
        )

        return redirect(
            "recette:recette_list"
        )

    # --------------------------------------------------------
    # CONFIRMATION
    # --------------------------------------------------------

    return render(
        request,
        "recette/confirm_delete.html",
        {
            "recette": recette,
            "user": user,
            "role": request.session.get("role"),
        }
    )