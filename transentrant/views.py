from django.shortcuts import (render,get_object_or_404,redirect)
from django.contrib import messages
from .models import Transentrant
from .forms import TransentrantForm
from users.models import AppUser



# =========================
# LISTE
# =========================

def t_transentrant_list(request):
    queryset = Transentrant.objects.all()
    chauffeur = request.GET.get("chauffeur", "").strip()
    num_vehicule = request.GET.get("num_vehicule", "").strip()
    telephone = request.GET.get("telephone","").strip()

    if chauffeur:
        queryset = queryset.filter(
            chauffeur__icontains=chauffeur
        )


    if num_vehicule:
        queryset = queryset.filter(
            num_vehicule__icontains=num_vehicule
        )


    if telephone:
        queryset = queryset.filter(
            telephone__icontains=telephone
        )



    return render(
        request,
        "transentrant/list.html",
        {
            "transentrants": queryset,
            "chauffeur": chauffeur,
            "num_vehicule": num_vehicule,
            "telephone": telephone,

            # utilisateur connecté
            "user_id": request.session.get(
                "user_id"
            ),
        }
    )



# =========================
# AJOUT
# =========================

def t_transentrant_add(request):
    if not request.session.get("user_id"):
        return redirect(
            "users:login"
        )
    if request.method == "POST":

        form = TransentrantForm(
            request.POST,
            request.FILES
        )


        if form.is_valid():


            transentrant = form.save(
                commit=False
            )


            user = AppUser.objects.get(
                id=request.session.get(
                    "user_id"
                )
            )


            transentrant.created_by = user


            transentrant.save()


            messages.success(
                request,
                "Transport entrant ajouté."
            )


            return redirect(
                "transentrant:t_transentrant_liste"
            )


    else:

        form = TransentrantForm()



    return render(
        request,
        "transentrant/form.html",
        {
            "form": form
        }
    )



# =========================
# DETAIL
# =========================

def t_transentrant_detail(request, id):

    client = get_object_or_404(
        Transentrant,
        id=id
    )


    return render(
        request,
        "transentrant/detail.html",
        {
            "client": client
        }
    )



# =========================
# MODIFICATION
# =========================

def t_transentrant_edit(request, id):

    if not request.session.get("user_id"):

        return redirect(
            "users:login"
        )


    client = get_object_or_404(
        Transentrant,
        id=id
    )


    # sécurité propriétaire

    if client.created_by_id != request.session.get(
        "user_id"
    ):

        messages.error(
            request,
            "Vous ne pouvez pas modifier cet enregistrement."
        )


        return redirect(
            "transentrant:t_transentrant_liste"
        )



    if request.method == "POST":

        form = TransentrantForm(
            request.POST,
            request.FILES,
            instance=client
        )


        if form.is_valid():

            form.save()


            messages.success(
                request,
                "Modification réussie."
            )


            return redirect(
                "transentrant:t_transentrant_liste"
            )


    else:

        form = TransentrantForm(
            instance=client
        )



    return render(
        request,
        "transentrant/form.html",
        {
            "form": form
        }
    )



# =========================
# SUPPRESSION
# =========================

def t_transentrant_delete(request, id):

    if not request.session.get("user_id"):

        return redirect(
            "users:login"
        )


    client = get_object_or_404(
        Transentrant,
        id=id
    )



    if client.created_by_id != request.session.get(
        "user_id"
    ):

        messages.error(
            request,
            "Suppression interdite."
        )


        return redirect(
            "transentrant:t_transentrant_liste"
        )



    if request.method == "POST":

        client.delete()


        messages.success(
            request,
            "Suppression réussie."
        )


        return redirect(
            "transentrant:t_transentrant_liste"
        )



    return render(
        request,
        "transentrant/confirm_delete.html",
        {
            "client": client
        }
    )