from datetime import datetime
from decimal import Decimal
from collections import defaultdict

from django.shortcuts import render

from entretien.models import Entretien
from depense.models import Depense
from retours.models import Retour
from vehiculesortant.models import VehiculeSortant
from produit.models import PaiementProduit
from avances.models import Avance
from avanceclient.models import AvanceClient
from salaire.models import Salaire


# ============================================================
# CONFIGURATION DU RAPPORT
# ============================================================

# IMPORTANT :
# L'application "rapports" correspond au rapport MICA.
#
# Donc :
# - les avances personnelles doivent être Mica uniquement
# - les salaires doivent être Mica uniquement
# - aucune avance Construction
# - aucun salaire Construction
#
# Même un Admin ne verra pas les données Construction
# dans ce rapport.
TYPE_TRAVAIL_RAPPORT = "Mica"


# ============================================================
# CONSTRUIRE RAPPORT GENERAL
# ============================================================

def construire_rapport(request):

    date_debut = request.GET.get("date_debut", "").strip()
    date_fin = request.GET.get("date_fin", "").strip()

    rapport = defaultdict(
        lambda: {
            "entretien": Decimal("0"),
            "achat_mica": Decimal("0"),
            "transport": Decimal("0"),
            "avance_client": Decimal("0"),
            "avance_chauffeur": Decimal("0"),
            "avance_personnel": Decimal("0"),
            "salaire": Decimal("0"),
            "sakafo": Decimal("0"),
            "docker": Decimal("0"),
            "divers": Decimal("0"),
            "triage": Decimal("0"),
            "retour": Decimal("0"),
        }
    )

    # ========================================================
    # ENTRETIEN CAMION
    # ========================================================

    entretiens = Entretien.objects.all()

    if date_debut:
        entretiens = entretiens.filter(
            date_cree__gte=date_debut
        )

    if date_fin:
        entretiens = entretiens.filter(
            date_cree__lte=date_fin
        )

    for e in entretiens:

        if not e.date_cree:
            continue

        nombre = e.nombre or 0

        prix = e.prix_du_piece or Decimal("0")

        montant = (
            Decimal(str(nombre))
            * Decimal(str(prix))
        )

        rapport[e.date_cree]["entretien"] += montant

    # ========================================================
    # DEPENSES
    # ========================================================

    depenses = Depense.objects.all()

    if date_debut:
        depenses = depenses.filter(
            date__gte=date_debut
        )

    if date_fin:
        depenses = depenses.filter(
            date__lte=date_fin
        )

    for d in depenses:

        if not d.date:
            continue

        ligne = rapport[d.date]

        titre = (
            (d.titre or "")
            .strip()
            .lower()
        )

        montant = (
            d.montant
            or Decimal("0")
        )

        if titre == "sakafo":

            ligne["sakafo"] += montant

        elif titre == "docker":

            ligne["docker"] += montant

        elif titre == "triage":

            ligne["triage"] += montant

        elif "transport" in titre:

            ligne["transport"] += montant

        else:

            ligne["divers"] += montant

    # ========================================================
    # ACHAT MICA
    # PAIEMENT PRODUIT
    # ========================================================

    paiements = PaiementProduit.objects.all()

    if date_debut:
        paiements = paiements.filter(
            date__date__gte=date_debut
        )

    if date_fin:
        paiements = paiements.filter(
            date__date__lte=date_fin
        )

    for p in paiements:

        if not p.date:
            continue

        # PaiementProduit.date est traité comme DateTimeField.
        date_paiement = p.date.date()

        montant = (
            p.montant
            or Decimal("0")
        )

        rapport[date_paiement]["achat_mica"] += montant

    # ========================================================
    # TRANSPORT SORTIE
    # VEHICULES SORTANTS
    # ========================================================

    vehicules_sortants = VehiculeSortant.objects.all()

    if date_debut:
        vehicules_sortants = vehicules_sortants.filter(
            created_at__date__gte=date_debut
        )

    if date_fin:
        vehicules_sortants = vehicules_sortants.filter(
            created_at__date__lte=date_fin
        )

    for v in vehicules_sortants:

        if not v.created_at:
            continue

        date_sortie = v.created_at.date()

        montant = (
            v.montant
            or Decimal("0")
        )

        rapport[date_sortie]["transport"] += montant

    # ========================================================
    # AVANCES PERSONNEL
    #
    # REGLE ABSOLUE DU RAPPORT MICA :
    #
    # UNIQUEMENT :
    #     personnel__typeTravail = "Mica"
    #
    # Construction est totalement exclu.
    # ========================================================

    avances_personnel = (
        Avance.objects
        .select_related(
            "personnel",
            "distribution",
            "enregistre_par",
        )
        .filter(
            personnel__isnull=False,
            personnel__typeTravail=TYPE_TRAVAIL_RAPPORT,
        )
    )

    if date_debut:
        avances_personnel = avances_personnel.filter(
            dateAv__gte=date_debut
        )

    if date_fin:
        avances_personnel = avances_personnel.filter(
            dateAv__lte=date_fin
        )

    for avance in avances_personnel:

        if not avance.dateAv:
            continue

        # IMPORTANT :
        # dateAv est un DateField.
        #
        # NE PAS faire :
        #     avance.dateAv.date()
        #
        # dateAv est déjà un datetime.date.
        date_avance = avance.dateAv

        montant = (
            avance.montantAv
            or Decimal("0")
        )

        rapport[date_avance]["avance_personnel"] += montant

    # ========================================================
    # AVANCES CHAUFFEURS
    #
    # Les chauffeurs ne sont PAS liés à personnel dans cette
    # logique :
    #
    # personnel = NULL
    # distribution != NULL
    #
    # On les conserve donc séparément.
    #
    # IMPORTANT :
    # Une avance Construction ne peut pas devenir chauffeur
    # simplement parce qu'elle possède une distribution.
    # ========================================================

    avances_chauffeurs = (
        Avance.objects
        .select_related(
            "personnel",
            "distribution",
            "enregistre_par",
        )
        .filter(
            personnel__isnull=True,
            distribution__isnull=False,
        )
    )

    if date_debut:
        avances_chauffeurs = avances_chauffeurs.filter(
            dateAv__gte=date_debut
        )

    if date_fin:
        avances_chauffeurs = avances_chauffeurs.filter(
            dateAv__lte=date_fin
        )

    for avance in avances_chauffeurs:

        if not avance.dateAv:
            continue

        date_avance = avance.dateAv

        montant = (
            avance.montantAv
            or Decimal("0")
        )

        rapport[date_avance]["avance_chauffeur"] += montant

    # ========================================================
    # SALAIRES
    #
    # REGLE ABSOLUE DU RAPPORT MICA :
    #
    # UNIQUEMENT :
    #     personnel__typeTravail = "Mica"
    #
    # Aucun salaire Construction.
    # ========================================================

    salaires = (
        Salaire.objects
        .select_related("personnel")
        .filter(
            personnel__typeTravail=TYPE_TRAVAIL_RAPPORT
        )
    )

    if date_debut:
        salaires = salaires.filter(
            date__gte=date_debut
        )

    if date_fin:
        salaires = salaires.filter(
            date__lte=date_fin
        )

    for salaire in salaires:

        if not salaire.date:
            continue

        date_salaire = salaire.date

        montant = (
            salaire.montant
            or Decimal("0")
        )

        rapport[date_salaire]["salaire"] += montant

    # ========================================================
    # AVANCE CLIENT
    # ========================================================

    avances_clients = AvanceClient.objects.all()

    if date_debut:
        avances_clients = avances_clients.filter(
            date__date__gte=date_debut
        )

    if date_fin:
        avances_clients = avances_clients.filter(
            date__date__lte=date_fin
        )

    for avance_client in avances_clients:

        if not avance_client.date:
            continue

        date_avance_client = avance_client.date.date()

        montant = (
            avance_client.montant
            or Decimal("0")
        )

        rapport[
            date_avance_client
        ]["avance_client"] += montant

    # ========================================================
    # RETOURS CLIENT
    # ========================================================

    retours = Retour.objects.all()

    if date_debut:
        retours = retours.filter(
            created_at__date__gte=date_debut
        )

    if date_fin:
        retours = retours.filter(
            created_at__date__lte=date_fin
        )

    for retour in retours:

        if not retour.created_at:
            continue

        date_retour = retour.created_at.date()

        montant = (
            retour.montant
            or Decimal("0")
        )

        rapport[
            date_retour
        ]["retour"] += montant

    # ========================================================
    # PREPARATION DES LIGNES
    # ========================================================

    lignes = []

    totaux = defaultdict(
        lambda: Decimal("0")
    )

    for date, data in sorted(
        rapport.items(),
        reverse=True
    ):

        data["date"] = date

        # ====================================================
        # TOTAL DES DEPENSES
        # ====================================================

        data["total_depenses"] = (
            data["entretien"]
            + data["achat_mica"]
            + data["transport"]
            + data["avance_client"]
            + data["avance_chauffeur"]
            + data["avance_personnel"]
            + data["salaire"]
            + data["sakafo"]
            + data["docker"]
            + data["divers"]
            + data["triage"]
        )

        # ====================================================
        # TOTAUX
        # ====================================================

        for cle, valeur in data.items():

            if cle == "date":
                continue

            totaux[cle] += valeur

        lignes.append(data)

    return (
        lignes,
        totaux,
        date_debut or "",
        date_fin or "",
    )


# ============================================================
# LISTE RAPPORT
# ============================================================

def rapport_list(request):

    (
        lignes,
        totaux,
        date_debut,
        date_fin,
    ) = construire_rapport(request)

    return render(
        request,
        "rapports/list.html",
        {
            "rapport": lignes,
            "totaux": totaux,
            "date_debut": date_debut,
            "date_fin": date_fin,

            # Informations du rapport
            "type_travail": TYPE_TRAVAIL_RAPPORT,
            "role": request.session.get("role"),
        }
    )


# ============================================================
# IMPRESSION RAPPORT
# ============================================================

def rapport_print(request):

    (
        lignes,
        totaux,
        date_debut,
        date_fin,
    ) = construire_rapport(request)

    return render(
        request,
        "rapports/print.html",
        {
            "rapport": lignes,
            "totaux": totaux,
            "date_debut": date_debut,
            "date_fin": date_fin,

            "type_travail": TYPE_TRAVAIL_RAPPORT,
            "role": request.session.get("role"),
        }
    )


# ============================================================
# DETAIL PAR DATE
# ============================================================

def rapport_detail(request, date):

    # ========================================================
    # CONVERSION DE LA DATE
    # ========================================================

    try:

        date_obj = datetime.strptime(
            date,
            "%Y-%m-%d"
        ).date()

    except (TypeError, ValueError):

        # Date invalide :
        # on retourne simplement au rapport.
        return rapport_list(request)

    # ========================================================
    # ENTRETIENS
    # ========================================================

    entretiens = Entretien.objects.filter(
        date_cree=date_obj
    )

    # ========================================================
    # DEPENSES
    # ========================================================

    depenses = Depense.objects.filter(
        date=date_obj
    )

    # ========================================================
    # PAIEMENTS PRODUITS
    # ========================================================

    paiements = PaiementProduit.objects.filter(
        date__date=date_obj
    )

    # ========================================================
    # AVANCES PERSONNEL MICA UNIQUEMENT
    #
    # Construction est EXCLU.
    # ========================================================

    avances_personnel = (
        Avance.objects
        .filter(
            dateAv=date_obj,
            personnel__isnull=False,
            personnel__typeTravail=TYPE_TRAVAIL_RAPPORT,
        )
        .select_related(
            "personnel",
            "distribution",
            "enregistre_par",
        )
        .order_by("-dateAv")
    )

    # ========================================================
    # AVANCES CHAUFFEURS
    # ========================================================

    avances_chauffeur = (
        Avance.objects
        .filter(
            dateAv=date_obj,
            personnel__isnull=True,
            distribution__isnull=False,
        )
        .select_related(
            "personnel",
            "distribution",
            "enregistre_par",
        )
        .order_by("-dateAv")
    )

    # ========================================================
    # TOUTES LES AVANCES AUTORISEES DANS LE RAPPORT MICA
    #
    # On combine :
    #   - avances personnel Mica
    #   - avances chauffeur
    #
    # Une avance Construction est impossible ici.
    # ========================================================

    avances = (
        Avance.objects
        .filter(
            dateAv=date_obj
        )
        .filter(
            personnel__isnull=True,
            distribution__isnull=False,
        )
        | Avance.objects.filter(
            dateAv=date_obj,
            personnel__isnull=False,
            personnel__typeTravail=TYPE_TRAVAIL_RAPPORT,
        )
    ).select_related(
        "personnel",
        "distribution",
        "enregistre_par",
    ).order_by("-dateAv")

    # ========================================================
    # SALAIRES MICA UNIQUEMENT
    # ========================================================

    salaires = (
        Salaire.objects
        .filter(
            date=date_obj,
            personnel__typeTravail=TYPE_TRAVAIL_RAPPORT,
        )
        .select_related(
            "personnel"
        )
        .order_by("-date")
    )

    # ========================================================
    # SALAIRES MICA
    # ========================================================

    salaires_mica = salaires

    # ========================================================
    # POUR COMPATIBILITE TEMPLATE
    # ========================================================
    #
    # Dans ce rapport, "salaires_construction" doit toujours
    # être vide.
    #
    # Cela évite qu'un ancien template puisse afficher
    # accidentellement un salaire Construction.
    # ========================================================

    salaires_construction = Salaire.objects.none()

    # ========================================================
    # AVANCES MICA
    # ========================================================

    avances_mica = avances_personnel

    # ========================================================
    # AVANCES CONSTRUCTION
    #
    # TOUJOURS VIDE DANS LE RAPPORT MICA.
    #
    # Même si la base contient des avances Construction
    # à cette date, elles ne doivent jamais être affichées.
    # ========================================================

    avances_construction = Avance.objects.none()

    # ========================================================
    # AVANCES CLIENT
    # ========================================================

    avances_clients = AvanceClient.objects.filter(
        date__date=date_obj
    )

    # ========================================================
    # RETOURS CLIENT
    # ========================================================

    retours = Retour.objects.filter(
        created_at__date=date_obj
    )

    # ========================================================
    # RENDU
    # ========================================================

    return render(
        request,
        "rapports/detail.html",
        {
            "date": date_obj,

            # -----------------------------------------------
            # Opérations générales
            # -----------------------------------------------

            "entretiens": entretiens,

            "depenses": depenses,

            "paiements": paiements,

            # -----------------------------------------------
            # Avances
            # -----------------------------------------------

            "avances": avances,

            "avances_personnel": avances_personnel,

            "avances_mica": avances_mica,

            "avances_construction": avances_construction,

            "avances_chauffeur": avances_chauffeur,

            # -----------------------------------------------
            # Salaires
            # -----------------------------------------------

            "salaires": salaires,

            "salaires_mica": salaires_mica,

            "salaires_construction": salaires_construction,

            # -----------------------------------------------
            # Clients / retours
            # -----------------------------------------------

            "avances_clients": avances_clients,

            "retours": retours,

            # -----------------------------------------------
            # Informations rapport
            # -----------------------------------------------

            "type_travail": TYPE_TRAVAIL_RAPPORT,

            "role": request.session.get("role"),
        }
    )