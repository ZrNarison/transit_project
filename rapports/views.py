from datetime import datetime
from decimal import Decimal
from collections import defaultdict

from django.shortcuts import render

from entretien.models import Entretien
from depense.models import Depense
from retours.models import Retour

from produit.models import PaiementProduit

from avances.models import Avance
from avanceclient.models import AvanceClient




# =====================================================
# CONSTRUIRE RAPPORT GENERAL
# =====================================================

def construire_rapport(request):

    date_debut = request.GET.get("date_debut")
    date_fin = request.GET.get("date_fin")


    rapport = defaultdict(lambda: {

        "entretien": Decimal("0"),
        "achat_mica": Decimal("0"),
        "entretien": Decimal("0"),

        "transport": Decimal("0"),

        "avance_client": Decimal("0"),

        "avance_chauffeur": Decimal("0"),

        "avance_personnel": Decimal("0"),

        "sakafo": Decimal("0"),

        "docker": Decimal("0"),

        "divers": Decimal("0"),

        "triage": Decimal("0"),

        "retour": Decimal("0"),

    })



    # =====================================================
    # ENTRETIEN CAMION
    # =====================================================

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

        montant = (
            e.nombre *
            e.prix_du_piece
        )


        rapport[e.date_cree]["entretien"] += montant





    # =====================================================
    # DEPENSES
    # =====================================================

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


        ligne = rapport[d.date]


        titre = d.titre.lower()



        if titre == "sakafo":

            ligne["sakafo"] += d.montant


        elif titre == "docker":

            ligne["docker"] += d.montant


        elif titre == "triage":

            ligne["triage"] += d.montant


        elif "transport" in titre:

            ligne["transport"] += d.montant


        else:

            ligne["divers"] += d.montant





    # =====================================================
    # ACHAT MICA (PAIEMENT PRODUIT)
    # =====================================================

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


        date = p.date.date()


        rapport[date]["achat_mica"] += p.montant






    # =====================================================
    # AVANCE PERSONNEL / CHAUFFEUR
    # =====================================================

    avances = Avance.objects.all()


    if date_debut:

        avances = avances.filter(
            dateAv__date__gte=date_debut
        )


    if date_fin:

        avances = avances.filter(
            dateAv__date__lte=date_fin
        )



    for a in avances:


        date = a.dateAv.date()


        ligne = rapport[date]



        if a.personnel:

            ligne["avance_personnel"] += a.montantAv



        elif a.distribution:

            ligne["avance_chauffeur"] += a.montantAv






    # =====================================================
    # AVANCE CLIENT
    # =====================================================

    avances_clients = AvanceClient.objects.all()


    if date_debut:

        avances_clients = avances_clients.filter(
            date__date__gte=date_debut
        )


    if date_fin:

        avances_clients = avances_clients.filter(
            date__date__lte=date_fin
        )



    for a in avances_clients:


        date = a.date.date()


        rapport[date]["avance_client"] += a.montant






    # =====================================================
    # RETOURS CLIENT
    # =====================================================

    retours = Retour.objects.all()



    if date_debut:

        retours = retours.filter(
            created_at__date__gte=date_debut
        )


    if date_fin:

        retours = retours.filter(
            created_at__date__lte=date_fin
        )



    for r in retours:


        date = r.created_at.date()


        rapport[date]["retour"] += r.montant






    # =====================================================
    # PREPARATION TABLEAU
    # =====================================================

    lignes = []


    totaux = defaultdict(
        lambda: Decimal("0")
    )



    for date,data in sorted(
        rapport.items(),
        reverse=True
    ):


        data["date"] = date



        data["total_depenses"] = (

            data["entretien"]

            + data["achat_mica"]

            + data["transport"]

            + data["avance_client"]

            + data["avance_chauffeur"]

            + data["avance_personnel"]

            + data["sakafo"]

            + data["docker"]

            + data["divers"]

            + data["triage"]

        )



        for cle,valeur in data.items():

            if cle != "date":

                totaux[cle] += valeur



        lignes.append(data)



    return (

        lignes,

        totaux,

        date_debut or "",

        date_fin or ""

    )








# =====================================================
# LISTE RAPPORT
# =====================================================

def rapport_list(request):


    lignes,totaux,date_debut,date_fin = construire_rapport(request)



    return render(

        request,

        "rapports/list.html",

        {

            "rapport": lignes,

            "totaux": totaux,

            "date_debut": date_debut,

            "date_fin": date_fin,

        }

    )







# =====================================================
# IMPRESSION
# =====================================================

def rapport_print(request):


    lignes,totaux,date_debut,date_fin = construire_rapport(request)



    return render(

        request,

        "rapports/print.html",

        {

            "rapport": lignes,

            "totaux": totaux,

            "date_debut": date_debut,

            "date_fin": date_fin,

        }

    )








# =====================================================
# DETAIL PAR DATE
# =====================================================

def rapport_detail(request,date):


    date_obj = datetime.strptime(
        date,
        "%Y-%m-%d"
    ).date()



    entretiens = Entretien.objects.filter(
        date_cree=date_obj
    )


    depenses = Depense.objects.filter(
        date=date_obj
    )


    paiements = PaiementProduit.objects.filter(
        date__date=date_obj
    )


    avances = Avance.objects.filter(
        dateAv__date=date_obj
    )


    avances_clients = AvanceClient.objects.filter(
        date__date=date_obj
    )


    retours = Retour.objects.filter(
        created_at__date=date_obj
    )



    return render(

        request,

        "rapports/detail.html",

        {

            "date":date_obj,

            "entretiens":entretiens,

            "depenses":depenses,

            "paiements":paiements,

            "avances":avances,

            "avances_clients":avances_clients,

            "retours":retours,

        }

    )