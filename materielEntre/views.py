from django.shortcuts import render, get_object_or_404, redirect
from .models import MaterielEntre
from .forms import MaterielEntreForm


# ==========================
# LISTE
# ==========================
def materielEntre_list(request):
    queryset = MaterielEntre.objects.select_related(
        "id_MaterielSort",
        "id_MaterielSort__id_Materiel"
    ).order_by("-dateEntre")

    materiel = request.GET.get('materiel', '').strip()
    demandeur = request.GET.get('demandeur', '').strip()
    date = request.GET.get('date', '').strip()

    if materiel:
        queryset = queryset.filter(id_MaterielSort__id_Materiel__nom__icontains=materiel)
    if demandeur:
        queryset = queryset.filter(id_MaterielSort__demandeur__icontains=demandeur)
    if date:
        queryset = queryset.filter(dateEntre__date=date)

    return render(
        request,
        "materielEntre/list.html",
        {
            "entrees": queryset,
            "materiel": materiel,
            "demandeur": demandeur,
            "date": date,
        },
    )


# ==========================
# DETAIL
# ==========================
def materielEntre_detail(request, id):
    entree = get_object_or_404(MaterielEntre, id=id)

    return render(
        request,
        "materielEntre/detail.html",
        {
            "entree": entree,
        },
    )


# ==========================
# ADD
# ==========================
def materielEntre_add(request):

    if request.method == "POST":
        form = MaterielEntreForm(request.POST)

        if form.is_valid():
            form.save()
            return redirect("materielEntre:materielEntre_list")

    else:
        form = MaterielEntreForm()

    return render(
        request,
        "materielEntre/form.html",
        {"form": form},
    )


# ==========================
# EDIT
# ==========================
def materielEntre_edit(request, id):

    entree = get_object_or_404(MaterielEntre, id=id)

    if request.method == "POST":
        form = MaterielEntreForm(request.POST, instance=entree)

        if form.is_valid():
            form.save()
            return redirect("materielEntre:materielEntre_list")

    else:
        form = MaterielEntreForm(instance=entree)

    return render(
        request,
        "materielEntre/form.html",
        {"form": form},
    )


# ==========================
# DELETE
# ==========================
def materielEntre_delete(request, id):

    entree = get_object_or_404(MaterielEntre, id=id)

    if request.method == "POST":
        entree.delete()
        return redirect("materielEntre:materielEntre_list")

    return render(
        request,
        "materielEntre/confirm_delete.html",
        {"entree": entree},
    )