from django.shortcuts import render, get_object_or_404, redirect
from django.db import transaction

from .models import Client
from .forms import ClientForm, ContactFormSet, CompteFormSet


# ================= LISTE =================
def client_list(request):
    clients = Client.objects.all()
    return render(request, "clients/list.html", {"clients": clients})


# ================= AJOUT =================
def client_add(request):

    form = ClientForm(request.POST or None, request.FILES or None)

    contact_formset = ContactFormSet(request.POST or None, prefix="contact")
    compte_formset = CompteFormSet(request.POST or None, prefix="compte")

    if request.method == "POST":

        if form.is_valid():

            try:
                with transaction.atomic():

                    client = form.save()

                    contact_formset = ContactFormSet(
                        request.POST,
                        instance=client,
                        prefix="contact"
                    )

                    compte_formset = CompteFormSet(
                        request.POST,
                        instance=client,
                        prefix="compte"
                    )

                    if contact_formset.is_valid() and compte_formset.is_valid():
                        contact_formset.save()
                        compte_formset.save()
                        return redirect("clients:client_list")

            except Exception as e:
                print("ERROR client_add:", e)

    return render(request, "clients/form.html", {
        "form": form,
        "contact_formset": contact_formset,
        "compte_formset": compte_formset
    })


# ================= DETAIL =================
def client_detail(request, id):
    client = get_object_or_404(Client, id=id)
    return render(request, "clients/detail.html", {"client": client})


# ================= EDIT =================
def client_edit(request, id):

    client = get_object_or_404(Client, id=id)

    form = ClientForm(request.POST or None, request.FILES or None, instance=client)

    contact_formset = ContactFormSet(request.POST or None, instance=client, prefix="contact")
    compte_formset = CompteFormSet(request.POST or None, instance=client, prefix="compte")

    if request.method == "POST":

        if form.is_valid():

            try:
                with transaction.atomic():

                    form.save()

                    if contact_formset.is_valid() and compte_formset.is_valid():
                        contact_formset.save()
                        compte_formset.save()
                        return redirect("clients:client_list")

            except Exception as e:
                print("ERROR client_edit:", e)

    return render(request, "clients/form.html", {
        "form": form,
        "contact_formset": contact_formset,
        "compte_formset": compte_formset
    })


# ================= DELETE =================
def client_delete(request, id):

    client = get_object_or_404(Client, id=id)

    if request.method == "POST":
        client.delete()
        return redirect("clients:client_list")

    return render(request, "clients/confirm_delete.html", {
        "client": client
    })