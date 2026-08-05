from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator

from .models import Client
from .forms import ClientForm

from audit.utils import enregistrer_action



# ================= LISTE =================

def client_list(request):

    queryset = Client.objects.all()

    nom = request.GET.get("nom", "").strip()
    prenom = request.GET.get("prenom", "").strip()
    contact = request.GET.get("contact", "").strip()


    if nom:
        queryset = queryset.filter(
            nom__icontains=nom
        )


    if prenom:
        queryset = queryset.filter(
            prenom__icontains=prenom
        )


    if contact:
        queryset = queryset.filter(
            contact__icontains=contact
        )


    paginator = Paginator(
        queryset,
        5
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )


    query_params = request.GET.copy()

    query_params.pop(
        "page",
        None
    )


    return render(
        request,
        "clients/list.html",
        {
            "clients": page_obj.object_list,
            "page_obj": page_obj,
            "query_params": query_params.urlencode(),
            "nom": nom,
            "prenom": prenom,
            "contact": contact,
        }
    )



# ================= AJOUT =================

def client_add(request):

    form = ClientForm(
        request.POST or None,
        request.FILES or None
    )


    if request.method == "POST" and form.is_valid():

        client = form.save()


        enregistrer_action(
            request,
            action="CREATE",
            module="Client",
            objet_id=client.id,
            ancienne=None,
            nouvelle={
                "nom": client.nom,
                "prenom": client.prenom,
                "contact": client.contact
            },
            description="Création d'un client"
        )


        return redirect(
            "clients:client_list"
        )


    return render(
        request,
        "clients/form.html",
        {
            "form": form
        }
    )



# ================= DETAIL =================

def client_detail(request, id):

    client = get_object_or_404(
        Client,
        id=id
    )


    return render(
        request,
        "clients/detail.html",
        {
            "client": client
        }
    )



# ================= MODIFICATION =================

def client_edit(request, id):

    client = get_object_or_404(
        Client,
        id=id
    )


    ancienne = {
        "nom": client.nom,
        "prenom": client.prenom,
        "contact": client.contact
    }


    form = ClientForm(
        request.POST or None,
        request.FILES or None,
        instance=client
    )


    if request.method == "POST" and form.is_valid():

        client = form.save()


        nouvelle = {
            "nom": client.nom,
            "prenom": client.prenom,
            "contact": client.contact
        }


        enregistrer_action(
            request,
            action="UPDATE",
            module="Client",
            objet_id=client.id,
            ancienne=ancienne,
            nouvelle=nouvelle,
            description="Modification d'un client"
        )


        return redirect(
            "clients:client_list"
        )


    return render(
        request,
        "clients/form.html",
        {
            "form": form
        }
    )



# ================= SUPPRESSION =================

def client_delete(request, id):

    client = get_object_or_404(
        Client,
        id=id
    )


    if request.method == "POST":


        ancienne = {
            "nom": client.nom,
            "prenom": client.prenom,
            "contact": client.contact
        }


        enregistrer_action(
            request,
            action="DELETE",
            module="Client",
            objet_id=client.id,
            ancienne=ancienne,
            nouvelle=None,
            description="Suppression d'un client"
        )


        client.delete()


        return redirect(
            "clients:client_list"
        )


    return render(
        request,
        "clients/confirm_delete.html",
        {
            "client": client
        }
    )