from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Sum

from .models import Materiels
from .forms import MaterielsForm
from collections import defaultdict

from audit.utils import enregistrer_action



def materiels_list(request):

    queryset = Materiels.objects.prefetch_related(
        "sorties",
        "sorties__entrees"
    )

    nom = request.GET.get('nom', '').strip()
    typeMat = request.GET.get('typeMat', '').strip()
    catMat = request.GET.get('catMat', '').strip()

    if nom:
        queryset = queryset.filter(nom__icontains=nom)

    if typeMat:
        queryset = queryset.filter(typeMat__icontains=typeMat)

    if catMat:
        queryset = queryset.filter(catMat__icontains=catMat)


    objets = queryset

    groupes = defaultdict(lambda: {
        "stock_initial": 0,
        "stock_sorti": 0,
        "stock_entre": 0,
    })


    for m in objets:

        cle = (m.nom, m.typeMat, m.catMat)

        groupes[cle]["nom"] = m.nom
        groupes[cle]["typeMat"] = m.typeMat
        groupes[cle]["catMat"] = m.catMat

        groupes[cle]["stock_initial"] += m.stock_initial
        groupes[cle]["stock_sorti"] += m.stock_sorti()
        groupes[cle]["stock_entre"] += m.stock_entre()


    materiels = []

    for cle, data in groupes.items():

        data["stock_restant"] = (
            data["stock_initial"]
            - data["stock_sorti"]
            + data["stock_entre"]
        )

        materiels.append(data)


    return render(
        request,
        "materiels/list.html",
        {
            "materiels": materiels
        }
    )



# =========================
# DETAIL
# =========================
def materiels_detail(request, nom, typeMat, catMat):

    materiels = Materiels.objects.filter(
        nom=nom,
        typeMat=typeMat,
        catMat=catMat
    )


    sorties = []
    entrees = []

    stock_initial = 0
    stock_sortie = 0
    stock_entree = 0


    for m in materiels:

        stock_initial += m.stock_initial
        stock_sortie += m.stock_sorti()
        stock_entree += m.stock_entre()


        materiel_sorties = m.sorties.all()

        sorties.extend(
            materiel_sorties
        )


        for s in materiel_sorties:

            entrees.extend(
                s.entrees.all()
            )


    context = {

        "nom": nom,
        "typeMat": typeMat,
        "catMat": catMat,

        "stock_initial": stock_initial,
        "stock_sortie": stock_sortie,
        "stock_entree": stock_entree,

        "stock_restant":
            stock_initial
            - stock_sortie
            + stock_entree,

        "sorties": sorties,
        "entrees": entrees,

    }


    return render(
        request,
        "materiels/detail.html",
        context
    )



# =========================
# AJOUTER
# =========================
def materiels_add(request):

    if request.method == "POST":

        form = MaterielsForm(
            request.POST
        )


        if form.is_valid():

            materiel = form.save()


            enregistrer_action(
                request,
                "CREATE",
                "Matériel",
                materiel.id,
                nouvelle={
                    "nom": materiel.nom,
                    "type": materiel.typeMat,
                    "categorie": materiel.catMat,
                    "stock_initial": materiel.stock_initial
                },
                description="Ajout d'un matériel"
            )


            return redirect(
                "materiels:materiels_list"
            )


    else:

        form = MaterielsForm()



    return render(
        request,
        "materiels/form.html",
        {
            "form": form
        }
    )



# =========================
# EDIT
# =========================
def materiels_edit(request, id):

    materiel = get_object_or_404(
        Materiels,
        id=id
    )


    ancienne = {

        "nom": materiel.nom,
        "type": materiel.typeMat,
        "categorie": materiel.catMat,
        "stock_initial": materiel.stock_initial

    }



    if request.method == "POST":

        form = MaterielsForm(
            request.POST,
            instance=materiel
        )


        if form.is_valid():

            materiel = form.save()


            enregistrer_action(
                request,
                "UPDATE",
                "Matériel",
                materiel.id,
                ancienne=ancienne,
                nouvelle={

                    "nom": materiel.nom,
                    "type": materiel.typeMat,
                    "categorie": materiel.catMat,
                    "stock_initial": materiel.stock_initial

                },
                description="Modification d'un matériel"
            )


            return redirect(
                "materiels:materiels_list"
            )


    else:

        form = MaterielsForm(
            instance=materiel
        )



    return render(
        request,
        "materiels/form.html",
        {
            "form": form
        }
    )



# =========================
# DELETE
# =========================
def materiels_delete(request, id):

    materiel = get_object_or_404(
        Materiels,
        id=id
    )


    ancienne = {

        "nom": materiel.nom,
        "type": materiel.typeMat,
        "categorie": materiel.catMat,
        "stock_initial": materiel.stock_initial

    }



    if request.method == "POST":


        enregistrer_action(
            request,
            "DELETE",
            "Matériel",
            materiel.id,
            ancienne=ancienne,
            description="Suppression d'un matériel"
        )


        materiel.delete()


        return redirect(
            "materiels:materiels_list"
        )


    return render(
        request,
        "materiels/confirm.html",
        {
            "materiel": materiel
        }
    )