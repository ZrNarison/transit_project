from decimal import Decimal

from django.shortcuts import (
    render,
    redirect,
    get_object_or_404,
)
from django.contrib import messages
from django.db import transaction
from django.db.models import Sum

from .models import MaterielSort
from .forms import MaterielSortForm
from materiels.models import Materiels


# ============================================================
# OUTIL :
# RÉCUPÉRER TOUS LES MATÉRIELS DU MÊME GROUPE
#
# Groupe = NOM + TYPE + CATÉGORIE
# ============================================================

def get_materiels_du_groupe(materiel):
    return Materiels.objects.filter(
        nom__iexact=materiel.nom.strip(),
        typeMat__iexact=materiel.typeMat.strip(),
        catMat__iexact=materiel.catMat.strip(),
    )


# ============================================================
# STOCK DU GROUPE
#
# Stock initial total
# - sorties totales
# + entrées/remises totales
# ============================================================

def get_stock_groupe(materiel):

    materiels = get_materiels_du_groupe(materiel)

    # --------------------------------------------------------
    # STOCK INITIAL TOTAL
    # --------------------------------------------------------

    stock_initial = (
        materiels.aggregate(
            total=Sum("stock_initial")
        )["total"]
        or Decimal("0")
    )

    # --------------------------------------------------------
    # SORTIES TOTALES
    # --------------------------------------------------------

    sorties = (
        MaterielSort.objects
        .filter(
            id_Materiel__in=materiels
        )
        .aggregate(
            total=Sum("Nb_MatSort")
        )["total"]
        or Decimal("0")
    )

    # --------------------------------------------------------
    # ENTRÉES / REMISES TOTALES
    # --------------------------------------------------------

    entrees = (
        MaterielSort.objects
        .filter(
            id_Materiel__in=materiels
        )
        .aggregate(
            total=Sum("entrees__Nb_Entre")
        )["total"]
        or Decimal("0")
    )

    # --------------------------------------------------------
    # STOCK RESTANT
    # --------------------------------------------------------

    stock_restant = (
        stock_initial
        - sorties
        + entrees
    )

    return {
        "stock_initial": stock_initial,
        "sorties": sorties,
        "entrees": entrees,
        "stock_restant": stock_restant,
    }


# ============================================================
# AJOUT SORTIE
# ============================================================

@transaction.atomic
def materielsort_add(request):

    if request.method == "POST":

        form = MaterielSortForm(request.POST)

        if form.is_valid():

            sortie = form.save(commit=False)

            materiel = sortie.id_Materiel

            quantite_sortie = (
                sortie.Nb_MatSort
                or Decimal("0")
            )

            # ------------------------------------------------
            # CONTRÔLE QUANTITÉ
            # ------------------------------------------------

            if quantite_sortie <= 0:

                messages.error(
                    request,
                    "❌ La quantité sortie doit être supérieure à 0."
                )

                return redirect(
                    "materielsort:materielsort_add"
                )

            # ------------------------------------------------
            # STOCK DU GROUPE
            # ------------------------------------------------

            stock = get_stock_groupe(materiel)

            stock_disponible = stock["stock_restant"]

            # ------------------------------------------------
            # CONTRÔLE STOCK
            # ------------------------------------------------

            if quantite_sortie > stock_disponible:

                messages.error(
                    request,
                    f"❌ Stock insuffisant ! "
                    f"Stock disponible pour "
                    f"{materiel.nom.upper()} | "
                    f"{materiel.typeMat.title()} | "
                    f"{materiel.catMat.title()} : "
                    f"{stock_disponible}"
                )

                return redirect(
                    "materielsort:materielsort_add"
                )

            # ------------------------------------------------
            # ENREGISTREMENT
            # ------------------------------------------------

            sortie.save()

            messages.success(
                request,
                "✅ Sortie enregistrée avec succès."
            )

            return redirect(
                "materielsort:materielsort_list"
            )

    else:

        form = MaterielSortForm()

    return render(
        request,
        "materielsort/form.html",
        {
            "form": form,
        }
    )


# ============================================================
# LISTE
# ============================================================

def materielsort_list(request):

    queryset = (
        MaterielSort.objects
        .select_related("id_Materiel")
        .prefetch_related("entrees")
        .order_by("-dateSortie", "-id")
    )

    materiel = request.GET.get(
        "materiel",
        ""
    ).strip()

    demandeur = request.GET.get(
        "demandeur",
        ""
    ).strip()

    date = request.GET.get(
        "date",
        ""
    ).strip()

    # --------------------------------------------------------
    # RECHERCHE MATÉRIEL
    # --------------------------------------------------------

    if materiel:

        queryset = queryset.filter(
            id_Materiel__nom__icontains=materiel
        )

    # --------------------------------------------------------
    # RECHERCHE DEMANDEUR
    # --------------------------------------------------------

    if demandeur:

        queryset = queryset.filter(
            demandeur__icontains=demandeur
        )

    # --------------------------------------------------------
    # RECHERCHE DATE
    # --------------------------------------------------------

    if date:

        queryset = queryset.filter(
            dateSortie=date
        )

    return render(
        request,
        "materielsort/list.html",
        {
            "materielsorts": queryset,
            "materiel": materiel,
            "demandeur": demandeur,
            "date": date,
        }
    )


# ============================================================
# DETAIL
# ============================================================

def materielsort_detail(request, id):

    materielsort = get_object_or_404(
        MaterielSort.objects
        .select_related("id_Materiel")
        .prefetch_related("entrees"),
        id=id
    )

    return render(
        request,
        "materielsort/detail.html",
        {
            "materielsort": materielsort,
        }
    )


# ============================================================
# MODIFICATION
# ============================================================

@transaction.atomic
def materielsort_edit(request, id):

    materielsort = get_object_or_404(
        MaterielSort.objects
        .select_related("id_Materiel")
        .prefetch_related("entrees"),
        id=id
    )

    ancien_materiel = materielsort.id_Materiel

    ancienne_quantite = (
        materielsort.Nb_MatSort
        or Decimal("0")
    )

    if request.method == "POST":

        form = MaterielSortForm(
            request.POST,
            instance=materielsort
        )

        if form.is_valid():

            nouveau_materiel = form.cleaned_data[
                "id_Materiel"
            ]

            nouvelle_quantite = (
                form.cleaned_data["Nb_MatSort"]
                or Decimal("0")
            )

            # ------------------------------------------------
            # CONTRÔLE QUANTITÉ
            # ------------------------------------------------

            if nouvelle_quantite <= 0:

                messages.error(
                    request,
                    "❌ La quantité sortie doit être supérieure à 0."
                )

                return redirect(
                    "materielsort:materielsort_edit",
                    id=id
                )

            # ------------------------------------------------
            # IDENTIFICATION DU GROUPE
            # ------------------------------------------------

            ancien_groupe = (
                ancien_materiel.nom.strip().lower(),
                ancien_materiel.typeMat.strip().lower(),
                ancien_materiel.catMat.strip().lower(),
            )

            nouveau_groupe = (
                nouveau_materiel.nom.strip().lower(),
                nouveau_materiel.typeMat.strip().lower(),
                nouveau_materiel.catMat.strip().lower(),
            )

            # ------------------------------------------------
            # MÊME GROUPE
            #
            # L'ancienne sortie est déjà déduite du stock.
            # On la restitue avant de vérifier la nouvelle.
            # ------------------------------------------------

            if ancien_groupe == nouveau_groupe:

                stock = get_stock_groupe(
                    nouveau_materiel
                )

                stock_disponible = (
                    stock["stock_restant"]
                    + ancienne_quantite
                )

            # ------------------------------------------------
            # NOUVEAU GROUPE
            # ------------------------------------------------

            else:

                stock = get_stock_groupe(
                    nouveau_materiel
                )

                stock_disponible = (
                    stock["stock_restant"]
                )

            # ------------------------------------------------
            # CONTRÔLE STOCK
            # ------------------------------------------------

            if nouvelle_quantite > stock_disponible:

                messages.error(
                    request,
                    f"❌ Stock insuffisant ! "
                    f"Stock disponible pour "
                    f"{nouveau_materiel.nom.upper()} | "
                    f"{nouveau_materiel.typeMat.title()} | "
                    f"{nouveau_materiel.catMat.title()} : "
                    f"{stock_disponible}"
                )

                return redirect(
                    "materielsort:materielsort_edit",
                    id=id
                )

            # ------------------------------------------------
            # SAUVEGARDE
            # ------------------------------------------------

            form.save()

            messages.success(
                request,
                "✅ Sortie modifiée avec succès."
            )

            return redirect(
                "materielsort:materielsort_list"
            )

    else:

        form = MaterielSortForm(
            instance=materielsort
        )

    return render(
        request,
        "materielsort/form.html",
        {
            "form": form,
            "materielsort": materielsort,
        }
    )


# ============================================================
# SUPPRESSION
# ============================================================

@transaction.atomic
def materielsort_delete(request, id):

    sortie = get_object_or_404(
        MaterielSort.objects
        .select_related("id_Materiel")
        .prefetch_related("entrees"),
        id=id
    )

    if request.method == "POST":

        sortie.delete()

        messages.success(
            request,
            "✅ Sortie supprimée avec succès. "
            "Le stock a été automatiquement rétabli."
        )

        return redirect(
            "materielsort:materielsort_list"
        )

    return render(
        request,
        "materielsort/confirmation.html",
        {
            "materielsort": sortie,
        }
    )