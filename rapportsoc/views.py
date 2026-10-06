from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from django.shortcuts import render

from depotEntreprise.models import DepotSoc
from recette.models import Recette
from depensesoc.models import DepenseSoc
from salaire.models import Salaire
from avances.models import Avance


# ============================================================
# CONSTRUCTION DU RAPPORT DE TRÉSORERIE SOCIÉTÉ
# ============================================================

def construire_rapport_tresorerie(request):

    date_debut_str = request.GET.get(
        "date_debut",
        ""
    ).strip()

    date_fin_str = request.GET.get(
        "date_fin",
        ""
    ).strip()

    date_debut = None
    date_fin = None

    ZERO = Decimal("0")

    # ========================================================
    # CONVERSION DES DATES
    # ========================================================

    if date_debut_str:

        try:

            date_debut = datetime.strptime(
                date_debut_str,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            messages.error(
                request,
                "La date de début est invalide."
            )

            date_debut_str = ""

    if date_fin_str:

        try:

            date_fin = datetime.strptime(
                date_fin_str,
                "%Y-%m-%d"
            ).date()

        except ValueError:

            messages.error(
                request,
                "La date de fin est invalide."
            )

            date_fin_str = ""

    # ========================================================
    # VÉRIFICATION DE LA PÉRIODE
    # ========================================================

    if (
        date_debut
        and date_fin
        and date_fin < date_debut
    ):

        messages.error(
            request,
            "La date de fin doit être supérieure ou égale à la date de début."
        )

        date_fin = None
        date_fin_str = ""

    # ========================================================
    # TOUTES LES OPÉRATIONS
    # ========================================================

    operations = []

    # ========================================================
    # 1. DÉPÔTS SOCIÉTÉ
    # ========================================================

    depots = DepotSoc.objects.all()

    for depot in depots:

        operations.append({

            "date": depot.date,

            "piece": f"DEP-{depot.id}",

            "description": "Dépôt",

            "titre": "Dépôt société",

            "depot": depot.montant or ZERO,

            "recette": ZERO,

            "depense": ZERO,

            "source": "DepotSoc",

            "objet": depot,
        })

    # ========================================================
    # 2. RECETTES
    # ========================================================

    recettes = Recette.objects.all()

    for recette in recettes:

        operations.append({

            "date": recette.date,

            "piece": f"REC-{recette.id}",

            "description": "Recette",

            "titre": recette.source or "Recette",

            "depot": ZERO,

            "recette": recette.montant or ZERO,

            "depense": ZERO,

            "source": "Recette",

            "objet": recette,
        })

    # ========================================================
    # 3. DÉPENSES SOCIÉTÉ
    # ========================================================

    depenses = DepenseSoc.objects.all()

    for depense in depenses:

        operations.append({

            "date": depense.date,

            "piece": f"DEPENSE-{depense.id}",

            "description": (
                depense.description
                or "Dépense"
            ),

            "titre": (
                depense.titre
                or "Dépense société"
            ),

            "depot": ZERO,

            "recette": ZERO,

            "depense": depense.montant or ZERO,

            "source": "DepenseSoc",

            "objet": depense,
        })

    # ========================================================
    # 4. SALAIRES
    # ========================================================

    salaires = Salaire.objects.select_related(
        "personnel"
    ).all()

    for salaire in salaires:

        if salaire.personnel:

            nom_personnel = (
                f"{salaire.personnel.nom} "
                f"{salaire.personnel.prenom}"
            )

        else:

            nom_personnel = (
                "Personnel non renseigné"
            )

        operations.append({

            "date": salaire.date,

            "piece": f"SAL-{salaire.id}",

            "description": "Salaire",

            "titre": nom_personnel,

            "depot": ZERO,

            "recette": ZERO,

            "depense": salaire.montant or ZERO,

            "source": "Salaire",

            "objet": salaire,
        })

    # ========================================================
    # 5. AVANCES PERSONNEL
    # ========================================================

    avances = Avance.objects.select_related(
        "personnel"
    ).all()

    for avance in avances:

        if not avance.dateAv:
            continue

        date_avance = avance.dateAv

        if avance.personnel:

            nom_personnel = (
                f"{avance.personnel.nom} "
                f"{avance.personnel.prenom}"
            )

        else:

            nom_personnel = (
                "Personnel non renseigné"
            )

        operations.append({

            "date": date_avance,

            "piece": f"AV-{avance.id}",

            "description": "Avance",

            "titre": (
                avance.motifAv
                or nom_personnel
            ),

            "depot": ZERO,

            "recette": ZERO,

            "depense": avance.montantAv or ZERO,

            "source": "Avance",

            "objet": avance,
        })

    # ========================================================
    # TRI CHRONOLOGIQUE
    # ========================================================

    operations.sort(
        key=lambda operation: (
            operation["date"],
            operation["objet"].id
        )
    )

    # ========================================================
    # CALCUL DU REPORT
    # ========================================================

    solde_report = ZERO

    if date_debut:

        for operation in operations:

            if operation["date"] < date_debut:

                solde_report += (
                    operation["depot"]
                    + operation["recette"]
                )

                solde_report -= (
                    operation["depense"]
                )

    # ========================================================
    # FILTRAGE DE LA PÉRIODE
    # ========================================================

    operations_periode = []

    for operation in operations:

        if date_debut:

            if operation["date"] < date_debut:
                continue

        if date_fin:

            if operation["date"] > date_fin:
                continue

        operations_periode.append(
            operation
        )

    # ========================================================
    # REGROUPEMENT PAR DATE
    # ========================================================

    operations_par_date = defaultdict(list)

    for operation in operations_periode:

        operations_par_date[
            operation["date"]
        ].append(operation)

    # ========================================================
    # CONSTRUCTION DU RAPPORT
    # ========================================================

    operations_grouped = []

    solde = solde_report

    total_depots = ZERO
    total_recettes = ZERO
    total_depenses = ZERO

    for date_operation in sorted(
        operations_par_date.keys()
    ):

        operations_jour = (
            operations_par_date[
                date_operation
            ]
        )

        # ----------------------------------------------------
        # TOTAUX DE LA JOURNÉE
        # ----------------------------------------------------

        depot_jour = ZERO
        recette_jour = ZERO
        depense_jour = ZERO

        # ----------------------------------------------------
        # INFORMATIONS
        # ----------------------------------------------------

        pieces = []
        descriptions = []
        titres = []

        for operation in operations_jour:

            # Montants

            depot_jour += operation["depot"]

            recette_jour += operation["recette"]

            depense_jour += operation["depense"]

            # Pièce

            pieces.append(
                operation["piece"]
            )

            # Description

            descriptions.append(
                operation["description"]
                or "—"
            )

            # Titre

            titres.append(
                operation["titre"]
                or "—"
            )

        # ====================================================
        # CALCUL DU SOLDE
        # ====================================================

        solde += depot_jour

        solde += recette_jour

        solde -= depense_jour

        # ====================================================
        # TOTAUX
        # ====================================================

        total_depots += depot_jour

        total_recettes += recette_jour

        total_depenses += depense_jour

        # ====================================================
        # LIGNE DU JOUR
        # ====================================================

        operations_grouped.append({

            "date": date_operation,

            "pieces": pieces,

            "descriptions": descriptions,

            "titres": titres,

            "depot": depot_jour,

            "recette": recette_jour,

            "depense": depense_jour,

            "solde": solde,

            "nombre_operations": len(
                operations_jour
            ),
        })

    # ========================================================
    # SOLDE FINAL
    # ========================================================

    solde_final = solde

    # ========================================================
    # STATISTIQUES
    # ========================================================

    nombre_operations_total = len(
        operations_periode
    )

    nombre_jours = len(
        operations_grouped
    )

    # ========================================================
    # CONTEXT
    # ========================================================

    context = {

        # ----------------------------------------------------
        # OPÉRATIONS
        # ----------------------------------------------------

        "operations": operations_grouped,

        # ----------------------------------------------------
        # DATES
        # ----------------------------------------------------

        "date_debut": date_debut_str,

        "date_fin": date_fin_str,

        "date_debut_affichage": (
            date_debut.strftime("%d/%m/%Y")
            if date_debut
            else ""
        ),

        "date_fin_affichage": (
            date_fin.strftime("%d/%m/%Y")
            if date_fin
            else ""
        ),

        # ----------------------------------------------------
        # REPORT
        # ----------------------------------------------------

        "solde_report": solde_report,

        # ----------------------------------------------------
        # DÉPÔTS
        # ----------------------------------------------------

        "total_depots": total_depots,

        # ----------------------------------------------------
        # RECETTES
        # ----------------------------------------------------

        "total_recettes": total_recettes,

        # ----------------------------------------------------
        # ENTRÉES
        # ----------------------------------------------------

        "total_entrees": (
            total_depots
            + total_recettes
        ),

        # ----------------------------------------------------
        # DÉPENSES
        # ----------------------------------------------------

        "total_depenses": total_depenses,

        # ----------------------------------------------------
        # SOLDE FINAL
        # ----------------------------------------------------

        "solde_final": solde_final,

        # ----------------------------------------------------
        # STATISTIQUES
        # ----------------------------------------------------

        "nombre_operations": (
            nombre_operations_total
        ),

        "nombre_jours": nombre_jours,
    }

    return context


# ============================================================
# RAPPORT DE TRÉSORERIE — AFFICHAGE
# ============================================================

def rapport_tresorerie(request):

    context = construire_rapport_tresorerie(
        request
    )

    return render(
        request,
        "rapportsoc/list.html",
        context
    )


# ============================================================
# RAPPORT DE TRÉSORERIE — IMPRESSION
# ============================================================

def rapport_tresorerie_print(request):

    context = construire_rapport_tresorerie(
        request
    )

    return render(
        request,
        "rapportsoc/rapport_tresorerie_print.html",
        context
    )