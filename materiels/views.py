from django.shortcuts import render, get_object_or_404, redirect
from .models import Materiels
from .forms import MaterielsForm


# ============================
# Liste des matériels
# ============================
def materiels_list(request):
    materiels = Materiels.objects.all().order_by("nom")

    return render(
        request,
        "materiels/list.html",
        {
            "materiels": materiels,
        },
    )


# ============================
# Détail
# ============================
def materiels_detail(request, id):
    materiel = get_object_or_404(Materiels, id=id)

    return render(
        request,
        "materiels/detail.html",
        {
            "materiel": materiel,
        },
    )


# ============================
# Ajouter
# ============================
def materiels_add(request):

    if request.method == "POST":
        form = MaterielsForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("materiels:materiels_list")

    else:
        form = MaterielsForm()

    return render(
        request,
        "materiels/form.html",
        {
            "form": form,
        },
    )


# ============================
# Modifier
# ============================
def materiels_edit(request, id):

    materiel = get_object_or_404(Materiels, id=id)

    if request.method == "POST":
        form = MaterielsForm(request.POST, instance=materiel)

        if form.is_valid():
            form.save()
            return redirect("materiels:materiels_list")

    else:
        form = MaterielsForm(instance=materiel)

    return render(
        request,
        "materiels/form.html",
        {
            "form": form,
        },
    )


# ============================
# Supprimer
# ============================
def materiels_delete(request, id):

    materiel = get_object_or_404(Materiels, id=id)

    if request.method == "POST":
        materiel.delete()
        return redirect("materiels:materiels_list")

    return render(
        request,
        "materiels/confirmation.html",
        {
            "materiel": materiel,
        },
    )