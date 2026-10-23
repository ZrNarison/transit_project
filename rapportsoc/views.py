from collections import defaultdict
from datetime import datetime
from decimal import Decimal

from django.contrib import messages
from django.shortcuts import render

from avances.models import Avance, H_Avance
from depensesoc.models import DepenseSoc, H_DepenseSoc
from depotEntreprise.models import DepotSoc, H_DepotSoc
from users.models import H_AppUser, AppUser
from recette.models import H_Recette, Recette
from salaire.models import H_Salaire, Salaire
from materiels.models import ReparationVehicule
from materiaux.models import (
    Depense,
    DepenseGasoil,
    ReparationVehicule,
    PaiementDocker,
    MouvementMateriauMCCR,
)
# ============================================================
# CONSTRUCTION DU RAPPORT DE TRÉSORERIE SOCIÉTÉ
# ============================================================
def construire_rapport_tresorerie(request):

    date_debut_str = request.GET.get("date_debut", "").strip()

    date_fin_str = request.GET.get("date_fin", "").strip()

    date_debut = None
    date_fin = None

    ZERO = Decimal("0")

    # ========================================================
    # CONVERSION DES DATES
    # ========================================================

    if date_debut_str:

        try:

            date_debut = datetime.strptime(date_debut_str, "%Y-%m-%d").date()

        except ValueError:

            messages.error(request, "La date de début est invalide.")

            date_debut_str = ""

    if date_fin_str:

        try:

            date_fin = datetime.strptime(date_fin_str, "%Y-%m-%d").date()

        except ValueError:

            messages.error(request, "La date de fin est invalide.")

            date_fin_str = ""

    # ========================================================
    # VÉRIFICATION DE LA PÉRIODE
    # ========================================================

    if date_debut and date_fin and date_fin < date_debut:

        messages.error(
            request, "La date de fin doit être supérieure ou égale à la date de début."
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

        operations.append(
            {
                "date": depot.date,
                "piece": f"DEP-{depot.id}",
                "description": "Dépôt",
                "titre": "Dépôt société",
                "depot": depot.montant or ZERO,
                "recette": ZERO,
                "depense": ZERO,
                "source": "DepotSoc",
                "objet": depot,
            }
        )

    # ========================================================
    # 2. RECETTES
    # ========================================================

    recettes = Recette.objects.all()

    for recette in recettes:

        operations.append(
            {
                "date": recette.date,
                "piece": f"REC-{recette.id}",
                "description": "Recette",
                "titre": recette.source or "Recette",
                "depot": ZERO,
                "recette": recette.montant or ZERO,
                "depense": ZERO,
                "source": "Recette",
                "objet": recette,
            }
        )

    # ========================================================
    # 3. DÉPENSES SOCIÉTÉ
    # ========================================================

    depenses = DepenseSoc.objects.all()

    for depense in depenses:

        operations.append(
            {
                "date": depense.date,
                "piece": f"DEPENSE-{depense.id}",
                "description": (depense.description or "Dépense"),
                "titre": (depense.titre or "Dépense société"),
                "depot": ZERO,
                "recette": ZERO,
                "depense": depense.montant or ZERO,
                "source": "DepenseSoc",
                "objet": depense,
            }
        )

    # ========================================================
    # 4. SALAIRES
    # ========================================================

    salaires = Salaire.objects.select_related("personnel").all()

    for salaire in salaires:

        if salaire.personnel:

            nom_personnel = f"{salaire.personnel.nom} " f"{salaire.personnel.prenom}"

        else:

            nom_personnel = "Personnel non renseigné"

        operations.append(
            {
                "date": salaire.date,
                "piece": f"SAL-{salaire.id}",
                "description": "Salaire",
                "titre": nom_personnel,
                "depot": ZERO,
                "recette": ZERO,
                "depense": salaire.montant or ZERO,
                "source": "Salaire",
                "objet": salaire,
            }
        )

    # ========================================================
    # 5. AVANCES PERSONNEL
    # ========================================================

    avances = Avance.objects.select_related("personnel").all()

    for avance in avances:

        if not avance.dateAv:
            continue

        date_avance = avance.dateAv

        if avance.personnel:

            nom_personnel = f"{avance.personnel.nom} " f"{avance.personnel.prenom}"

        else:

            nom_personnel = "Personnel non renseigné"

        operations.append(
            {
                "date": date_avance,
                "piece": f"AV-{avance.id}",
                "description": "Avance",
                "titre": (avance.motifAv or nom_personnel),
                "depot": ZERO,
                "recette": ZERO,
                "depense": avance.montantAv or ZERO,
                "source": "Avance",
                "objet": avance,
            }
        )
        # ========================================================
    # 6. RÉPARATIONS VÉHICULES ET ENGINS — GALAXY
    # ========================================================

    reparations = ReparationVehicule.objects.all()

    for reparation in reparations:
        if not reparation.date_reparation:
            continue

        operations.append(
            {
                "date": reparation.date_reparation,
                "piece": f"MAT-{reparation.id}",
                "description": "Matériel - Réparation",
                "titre": (
                    f"{reparation.vehicule} - "
                    f"{reparation.designation}"
                ),
                "depot": ZERO,
                "recette": ZERO,
                "depense": reparation.total or ZERO,
                "source": "ReparationVehicule",
                "objet": reparation,
            }
        )

    # ========================================================
    # TRI CHRONOLOGIQUE
    # ========================================================

    operations.sort(key=lambda operation: (operation["date"], operation["objet"].id))

    # ========================================================
    # CALCUL DU REPORT
    # ========================================================

    solde_report = ZERO

    if date_debut:

        for operation in operations:

            if operation["date"] < date_debut:

                solde_report += operation["depot"] + operation["recette"]

                solde_report -= operation["depense"]

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

        operations_periode.append(operation)

    # ========================================================
    # REGROUPEMENT PAR DATE
    # ========================================================

    operations_par_date = defaultdict(list)

    for operation in operations_periode:

        operations_par_date[operation["date"]].append(operation)

    # ========================================================
    # CONSTRUCTION DU RAPPORT
    # ========================================================

    operations_grouped = []

    solde = solde_report

    total_depots = ZERO
    total_recettes = ZERO
    total_depenses = ZERO

    for date_operation in sorted(operations_par_date.keys()):

        operations_jour = operations_par_date[date_operation]

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

            pieces.append(operation["piece"])

            # Description

            descriptions.append(operation["description"] or "—")

            # Titre

            titres.append(operation["titre"] or "—")

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

        operations_grouped.append(
            {
                "date": date_operation,
                "pieces": pieces,
                "descriptions": descriptions,
                "titres": titres,
                "depot": depot_jour,
                "recette": recette_jour,
                "depense": depense_jour,
                "solde": solde,
                "nombre_operations": len(operations_jour),
            }
        )

    # ========================================================
    # SOLDE FINAL
    # ========================================================

    solde_final = solde

    # ========================================================
    # STATISTIQUES
    # ========================================================

    nombre_operations_total = len(operations_periode)

    nombre_jours = len(operations_grouped)

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
        "date_debut_affichage": (date_debut.strftime("%d/%m/%Y") if date_debut else ""),
        "date_fin_affichage": (date_fin.strftime("%d/%m/%Y") if date_fin else ""),
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
        "total_entrees": (total_depots + total_recettes),
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
        "nombre_operations": (nombre_operations_total),
        "nombre_jours": nombre_jours,
    }

    return context


# ============================================================
# RAPPORT DE TRÉSORERIE — AFFICHAGE
# ============================================================
def rapport_tresorerie(request):

    context = construire_rapport_tresorerie(request)

    return render(request, "rapportsoc/list.html", context)


# ============================================================
# RAPPORT DE TRÉSORERIE — IMPRESSION
# ============================================================
def rapport_tresorerie_print(request):

    context = construire_rapport_tresorerie(request)

    return render(request, "rapportsoc/rapport_tresorerie_print.html", context)



# ===================================================================
#
# ENTREPRISE H — MCCR
#
# ===================================================================

# ============================================================
# CONSTRUCTION DU RAPPORT DE TRÉSORERIE MCCR
# ============================================================

def h_construire_rapport_tresorerie(request):
    """
    Construit le rapport de trésorerie de MCCR exclusivement
    à partir des modèles H_.

    Le solde final est calculé ainsi :
        Solde reporté + Dépôts + Recettes - Dépenses
    """

    date_debut_str = request.GET.get("date_debut", "").strip()
    date_fin_str = request.GET.get("date_fin", "").strip()

    date_debut = None
    date_fin = None
    ZERO = Decimal("0")

    # ========================================================
    # 1. CONVERSION ET VALIDATION DES DATES
    # ========================================================

    if date_debut_str:
        try:
            date_debut = datetime.strptime(
                date_debut_str, "%Y-%m-%d"
            ).date()
        except ValueError:
            messages.error(request, "La date de début est invalide.")
            date_debut_str = ""

    if date_fin_str:
        try:
            date_fin = datetime.strptime(
                date_fin_str, "%Y-%m-%d"
            ).date()
        except ValueError:
            messages.error(request, "La date de fin est invalide.")
            date_fin_str = ""

    if date_debut and date_fin and date_fin < date_debut:
        messages.error(
            request,
            "La date de fin doit être supérieure ou égale "
            "à la date de début.",
        )
        date_fin = None
        date_fin_str = ""

    # ========================================================
    # 2. COLLECTE DES OPÉRATIONS MCCR UNIQUEMENT
    # ========================================================

    operations = []

    # --------------------------------------------------------
    # 2.1. DÉPÔTS SOCIÉTÉ MCCR
    # --------------------------------------------------------

    depots = H_DepotSoc.objects.all()

    for depot in depots:
        if not depot.date:
            continue

        operations.append(
            {
                "date": depot.date,
                "piece": f"DEP-{depot.id}",
                "description": "Dépôt",
                "titre": "Dépôt société MCCR",
                "depot": depot.montant or ZERO,
                "recette": ZERO,
                "depense": ZERO,
                "source": "H_DepotSoc",
                "objet": depot,
            }
        )

    # --------------------------------------------------------
    # 2.2. RECETTES MCCR
    # --------------------------------------------------------

    recettes = H_Recette.objects.all()

    for recette in recettes:
        if not recette.date:
            continue

        operations.append(
            {
                "date": recette.date,
                "piece": f"REC-{recette.id}",
                "description": "Recette",
                "titre": recette.source or "Recette MCCR",
                "depot": ZERO,
                "recette": recette.montant or ZERO,
                "depense": ZERO,
                "source": "H_Recette",
                "objet": recette,
            }
        )

    # --------------------------------------------------------
    # 2.3. DÉPENSES SOCIÉTÉ MCCR
    # --------------------------------------------------------

    depenses = H_DepenseSoc.objects.all()

    for depense in depenses:
        if not depense.date:
            continue

        operations.append(
            {
                "date": depense.date,
                "piece": f"DEPENSE-{depense.id}",
                "description": depense.description or "Dépense",
                "titre": depense.titre or "Dépense société MCCR",
                "depot": ZERO,
                "recette": ZERO,
                "depense": depense.montant or ZERO,
                "source": "H_DepenseSoc",
                "objet": depense,
            }
        )

    # --------------------------------------------------------
    # 2.4. SALAIRES MCCR
    # --------------------------------------------------------

    salaires = H_Salaire.objects.select_related("personnel").all()

    for salaire in salaires:
        if not salaire.date:
            continue

        if salaire.personnel:
            nom_personnel = (
                f"{salaire.personnel.nom or ''} "
                f"{salaire.personnel.prenom or ''}"
            ).strip()
        else:
            nom_personnel = "Personnel non renseigné"

        operations.append(
            {
                "date": salaire.date,
                "piece": f"SAL-{salaire.id}",
                "description": "Salaire",
                "titre": nom_personnel,
                "depot": ZERO,
                "recette": ZERO,
                "depense": salaire.montant or ZERO,
                "source": "H_Salaire",
                "objet": salaire,
            }
        )

    # --------------------------------------------------------
    # 2.5. AVANCES AU PERSONNEL MCCR
    # --------------------------------------------------------

    avances = H_Avance.objects.select_related("personnel").all()

    for avance in avances:
        if not avance.dateAv:
            continue

        if avance.personnel:
            nom_personnel = (
                f"{avance.personnel.nom or ''} "
                f"{avance.personnel.prenom or ''}"
            ).strip()
        else:
            nom_personnel = "Personnel non renseigné"

        operations.append(
            {
                "date": avance.dateAv,
                "piece": f"AV-{avance.id}",
                "description": "Avance au personnel",
                "titre": avance.motifAv or nom_personnel,
                "depot": ZERO,
                "recette": ZERO,
                "depense": avance.montantAv or ZERO,
                "source": "H_Avance",
                "objet": avance,
            }
        )

        # ========================================================
    # 2.6. DÉPENSES GÉNÉRALES MCCR
    # ========================================================

    for depense in Depense.objects.all():
        if not depense.date_depense:
            continue

        operations.append(
            {
                "date": depense.date_depense,
                "piece": f"MCCR-DEP-{depense.id}",
                "description": "Dépense matériel",
                "titre": depense.designation or "Dépense MCCR",
                "depot": ZERO,
                "recette": ZERO,
                "depense": depense.montant or ZERO,
                "source": "Depense",
                "objet": depense,
            }
        )

    # ========================================================
    # 2.7. DÉPENSES DE GASOIL MCCR
    # ========================================================

    for gasoil in DepenseGasoil.objects.select_related("vehicule").all():
        if not gasoil.date_gasoil:
            continue

        operations.append(
            {
                "date": gasoil.date_gasoil,
                "piece": f"MCCR-GAS-{gasoil.id}",
                "description": "Achat gasoil",
                "titre": (
                    f"{gasoil.vehicule.immatriculation} "
                    f"- {gasoil.quantite_litre} L"
                ),
                "depot": ZERO,
                "recette": ZERO,
                "depense": gasoil.total or ZERO,
                "source": "DepenseGasoil",
                "objet": gasoil,
            }
        )

    # ========================================================
    # 2.8. RÉPARATIONS VÉHICULES MCCR
    # ========================================================

    for reparation in ReparationVehicule.objects.select_related(
        "vehicule"
    ).all():
        if not reparation.date_reparation:
            continue

        operations.append(
            {
                "date": reparation.date_reparation,
                "piece": f"MCCR-REP-{reparation.id}",
                "description": "Réparation véhicule",
                "titre": (
                    f"{reparation.vehicule.immatriculation} "
                    f"- {reparation.designation}"
                ),
                "depot": ZERO,
                "recette": ZERO,
                "depense": reparation.montant_total_calcule or ZERO,
                "source": "ReparationVehicule",
                "objet": reparation,
            }
        )

    # ========================================================
    # 2.9. PAIEMENTS DOCKERS MCCR
    # ========================================================

    for paiement in PaiementDocker.objects.select_related(
        "activite",
        "activite__vehicule",
    ).all():
        if not paiement.date_activite:
            continue

        operations.append(
            {
                "date": paiement.date_activite,
                "piece": f"MCCR-DOC-{paiement.id}",
                "description": "Paiement docker",
                "titre": (
                    f"{paiement.activite.vehicule.immatriculation}"
                ),
                "depot": ZERO,
                "recette": ZERO,
                "depense": paiement.montant or ZERO,
                "source": "PaiementDocker",
                "objet": paiement,
            }
        )

    # ========================================================
    # 2.10. MOUVEMENTS DE MATÉRIAUX MCCR
    # ========================================================

    mouvements = MouvementMateriauMCCR.objects.select_related(
        "materiau"
    ).all()

    for mouvement in mouvements:
        if not mouvement.date_mouvement:
            continue

        montant = mouvement.montant or ZERO

        if mouvement.type_mouvement == (
            MouvementMateriauMCCR.TypeMouvement.ENTREE
        ):
            # Entrée de stock : achat, donc dépense.
            depot_materiau = ZERO
            recette_materiau = ZERO
            depense_materiau = montant
            description = "Achat matériau"

        elif mouvement.type_mouvement == (
            MouvementMateriauMCCR.TypeMouvement.SORTIE
        ):
            # Sortie de stock : vente, donc recette.
            depot_materiau = ZERO
            recette_materiau = montant
            depense_materiau = ZERO
            description = "Vente matériau"

        elif mouvement.type_mouvement == (
            MouvementMateriauMCCR.TypeMouvement.RETOUR
        ):
            # Le sens financier du retour dépend de la transaction.
            # Ne pas le comptabiliser automatiquement sans règle définie.
            continue

        else:
            continue

        operations.append(
            {
                "date": mouvement.date_mouvement,
                "piece": f"MCCR-MAT-{mouvement.id}",
                "description": description,
                "titre": mouvement.materiau.nom,
                "depot": depot_materiau,
                "recette": recette_materiau,
                "depense": depense_materiau,
                "source": "MouvementMateriauMCCR",
                "objet": mouvement,
            }
        )

    # ========================================================
    # 3. TRI CHRONOLOGIQUE
    # ========================================================

    operations.sort(
        key=lambda operation: (
            operation["date"],
            operation["piece"],
        )
    )

    # ========================================================
    # 4. CALCUL DU SOLDE REPORTÉ AVANT LA PÉRIODE
    # ========================================================

    solde_report = ZERO

    if date_debut:
        for operation in operations:
            if operation["date"] < date_debut:
                solde_report += (
                    operation["depot"]
                    + operation["recette"]
                    - operation["depense"]
                )

    # ========================================================
    # 5. FILTRAGE DES OPÉRATIONS DE LA PÉRIODE
    # ========================================================

    operations_periode = []

    for operation in operations:
        date_operation = operation["date"]

        if date_debut and date_operation < date_debut:
            continue

        if date_fin and date_operation > date_fin:
            continue

        operations_periode.append(operation)

    # ========================================================
    # 6. REGROUPEMENT DES OPÉRATIONS PAR JOUR
    # ========================================================

    operations_par_date = defaultdict(list)

    for operation in operations_periode:
        operations_par_date[operation["date"]].append(operation)

    # ========================================================
    # 7. CONSTRUCTION DU RAPPORT JOURNALIER
    # ========================================================

    operations_grouped = []

    solde = solde_report

    total_depots = ZERO
    total_recettes = ZERO
    total_depenses = ZERO

    for date_operation in sorted(operations_par_date.keys()):
        operations_jour = operations_par_date[date_operation]

        depot_jour = ZERO
        recette_jour = ZERO
        depense_jour = ZERO

        pieces = []
        descriptions = []
        titres = []

        for operation in operations_jour:
            depot_jour += operation["depot"]
            recette_jour += operation["recette"]
            depense_jour += operation["depense"]

            pieces.append(operation["piece"])
            descriptions.append(operation["description"] or "—")
            titres.append(operation["titre"] or "—")

        # Solde cumulé après les opérations de la journée.
        solde += depot_jour + recette_jour - depense_jour

        total_depots += depot_jour
        total_recettes += recette_jour
        total_depenses += depense_jour

        operations_grouped.append(
            {
                "date": date_operation,
                "pieces": pieces,
                "descriptions": descriptions,
                "titres": titres,
                "depot": depot_jour,
                "recette": recette_jour,
                "depense": depense_jour,
                "solde": solde,
                "nombre_operations": len(operations_jour),
            }
        )

    # ========================================================
    # 8. SOLDE FINAL
    # ========================================================

    solde_final = solde

    # ========================================================
    # 9. STATISTIQUES
    # ========================================================

    nombre_operations_total = len(operations_periode)
    nombre_jours = len(operations_grouped)

    # ========================================================
    # 10. CONTEXTE POUR LES TEMPLATES MCCR
    # ========================================================

    context = {
        "operations": operations_grouped,

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

        "solde_report": solde_report,

        "total_depots": total_depots,
        "total_recettes": total_recettes,
        "total_entrees": total_depots + total_recettes,
        "total_depenses": total_depenses,

        "solde_final": solde_final,

        "nombre_operations": nombre_operations_total,
        "nombre_jours": nombre_jours,
    }

    return context


# ============================================================
# RAPPORT DE TRÉSORERIE MCCR — AFFICHAGE
# ============================================================

def h_rapport_tresorerie(request):
    context = h_construire_rapport_tresorerie(request)

    return render(
        request,
        "rapportsoc/h_list.html",
        context,
    )


# ============================================================
# RAPPORT DE TRÉSORERIE MCCR — IMPRESSION
# ============================================================

def h_rapport_tresorerie_print(request):
    context = h_construire_rapport_tresorerie(request)

    return render(
        request,
        "rapportsoc/h_rapport_tresorerie_print.html",
        context,
    )
