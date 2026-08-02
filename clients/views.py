from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from .models import Client
from .forms import ClientForm


# ================= LISTE =================
def client_list(request):
    queryset = Client.objects.all()
    nom = request.GET.get('nom', '').strip()
    prenom = request.GET.get('prenom', '').strip()
    contact = request.GET.get('contact', '').strip()

    if nom:
        queryset = queryset.filter(nom__icontains=nom)
    if prenom:
        queryset = queryset.filter(prenom__icontains=prenom)
    if contact:
        queryset = queryset.filter(contact__icontains=contact)

    paginator = Paginator(queryset, 5)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    query_params = request.GET.copy()
    query_params.pop('page', None)

    return render(request, "clients/list.html", {
        "clients": page_obj.object_list,
        "page_obj": page_obj,
        "query_params": query_params.urlencode(),
        "nom": nom,
        "prenom": prenom,
        "contact": contact,
    })


# ================= AJOUT =================
def client_add(request):

    form = ClientForm(request.POST or None, request.FILES or None)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect("clients:client_list")

    return render(request, "clients/form.html", {"form": form})


# ================= DETAIL =================
def client_detail(request, id):
    client = get_object_or_404(Client, id=id)
    return render(request, "clients/detail.html", {"client": client})


# ================= EDIT =================
def client_edit(request, id):

    client = get_object_or_404(Client, id=id)

    form = ClientForm(request.POST or None, request.FILES or None, instance=client)

    if request.method == "POST":
        if form.is_valid():
            form.save()
            return redirect("clients:client_list")

    return render(request, "clients/form.html", {"form": form})


# ================= DELETE =================
def client_delete(request, id):

    client = get_object_or_404(Client, id=id)

    if request.method == "POST":
        client.delete()
        return redirect("clients:client_list")

    return render(request, "clients/confirm_delete.html", {"client": client})