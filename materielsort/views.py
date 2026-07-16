from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import MaterielSort
from .forms import MaterielSortForm


def materielsort_add(request):

    if request.method == "POST":
        form = MaterielSortForm(request.POST)

        if form.is_valid():
            sortie = form.save(commit=False)

            materiel = sortie.id_Materiel

            # 🔥 contrôle stock
            if sortie.Nb_MatSort > materiel.stock_restant():
                messages.error(
                    request,
                    "❌ Stock insuffisant pour cette sortie !"
                )
                return redirect("materielsort:materielsort_add")

            # ➖ déduction stock
            materiel.stock_initial -= sortie.Nb_MatSort
            materiel.save()

            sortie.save()

            messages.success(request, "✅ Sortie enregistrée avec succès")
            return redirect("materielsort:materielsort_list")

    else:
        form = MaterielSortForm()

    return render(request, "materielsort/form.html", {"form": form})
# ==========================
# LISTE
# ==========================
def materielsort_list(request):
    queryset = MaterielSort.objects.select_related(
        "id_Materiel"
    ).order_by("-dateSortie")

    materiel = request.GET.get('materiel', '').strip()
    demandeur = request.GET.get('demandeur', '').strip()
    date = request.GET.get('date', '').strip()

    if materiel:
        queryset = queryset.filter(id_Materiel__nom__icontains=materiel)
    if demandeur:
        queryset = queryset.filter(demandeur__icontains=demandeur)
    if date:
        queryset = queryset.filter(dateSortie__date=date)

    return render(
        request,
        "materielsort/list.html",
        {
            "materielsorts": queryset,
            "materiel": materiel,
            "demandeur": demandeur,
            "date": date,
        },
    )


# ==========================
# DETAIL
# ==========================
def materielsort_detail(request, id):

    materielsort = get_object_or_404(MaterielSort, id=id)

    return render(
        request,
        "materielsort/detail.html",
        {
            "materielsort": materielsort,
        },
    )


# ==========================
# EDIT
# ==========================
def materielsort_edit(request, id):

    materielsort = get_object_or_404(MaterielSort, id=id)

    if request.method == "POST":
        form = MaterielSortForm(request.POST, instance=materielsort)

        if form.is_valid():
            form.save()
            return redirect("materielsort:materielsort_list")

    else:
        form = MaterielSortForm(instance=materielsort)

    return render(
        request,
        "materielsort/form.html",
        {"form": form},
    )


def materielsort_delete(request, id):

    sortie = get_object_or_404(MaterielSort, id=id)

    if request.method == "POST":

        materiel = sortie.id_Materiel

        # 🔥 retour stock
        materiel.stock_initial += sortie.Nb_MatSort
        materiel.save()

        sortie.delete()

        return redirect("materielsort:materielsort_list")

    return render(request, "materielsort/confirmation.html", {
        "materielsort": sortie
    })