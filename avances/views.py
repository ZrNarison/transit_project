from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from .forms import AvanceForm
from .models import Avance


# AJOUT
def avance_add(request):
    if request.method == "POST":
        form = AvanceForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("avances:avance_list")
    else:
        form = AvanceForm()

    return render(request, "avances/form.html", {"form": form})


# LISTE + RECHERCHE
def avance_list(request):
    avances = Avance.objects.select_related("id_client").all()

    nom = request.GET.get("nom", "").strip()
    date = request.GET.get("date", "").strip()

    # Recherche par nom ou prénom
    if nom:
        avances = avances.filter(
            Q(id_client__nom__icontains=nom) |
            Q(id_client__prenom__icontains=nom)
        )

    # Recherche par date
    if date:
        avances = avances.filter(dateAv=date)

    context = {
        "avances": avances,
        "nom": nom,
        "date": date,
    }

    return render(request, "avances/list.html", context)


# DETAIL
def avance_detail(request, id):
    avance = get_object_or_404(Avance, id=id)
    return render(request, "avances/detail.html", {"avance": avance})


# MODIFIER
def avance_edit(request, id):
    avance = get_object_or_404(Avance, id=id)

    if request.method == "POST":
        form = AvanceForm(request.POST, instance=avance)
        if form.is_valid():
            form.save()
            return redirect("avances:avance_list")
    else:
        form = AvanceForm(instance=avance)

    return render(request, "avances/form.html", {"form": form})


# SUPPRIMER
def avance_delete(request, id):
    avance = get_object_or_404(Avance, id=id)

    if request.method == "POST":
        avance.delete()
        return redirect("avances:avance_list")

    return render(request, "avances/confirm_delete.html", {"avance": avance})