from django.shortcuts import render

# Create your views here.
from django.shortcuts import render, get_object_or_404, redirect
from .models import MaterielEntre
from .forms import MaterielEntreForm


# ==========================
# LISTE
# ==========================
def materielEntre_list(request):

    materielEntre = materielEntre.objects.select_related(
        "id_Materiel"
    ).order_by("-dateAv")

    return render(
        request,
        "materielEntre/list.html",
        {
            "materielEntre": materielEntre,
        },
    )


# ==========================
# DETAIL
# ==========================
def materielEntre_detail(request, id):

    materielEntre = get_object_or_404(materielEntre, id=id)

    return render(
        request,
        "materielEntre/detail.html",
        {
            "materielEntre": materielEntre,
        },
    )


# ==========================
# ADD
# ==========================
def materielEntre_add(request):

    if request.method == "POST":
        form = materielEntre(request.POST)

        if form.is_valid():
            form.save()
            return redirect("materielEntre:materielEntre_list")

    else:
        form = MaterielEntre()

    return render(
        request,
        "materielEntre/form.html",
        {"form": form},
    )


# ==========================
# EDIT
# ==========================
def materielEntre_edit(request, id):

    materielEntre = get_object_or_404(MaterielEntre, id=id)

    if request.method == "POST":
        form = MaterielEntreForm(request.POST, instance=materielsort)

        if form.is_valid():
            form.save()
            return redirect("materielEntre:materielEntre_list")

    else:
        form = MaterielEntreForm(instance=materielEntre)

    return render(
        request,
        "materielEntre/form.html",
        {"form": form},
    )


# ==========================
# DELETE
# ==========================
def materielEntre_delete(request, id):

    materielEntre = get_object_or_404(MaterielEntre, id=id)

    if request.method == "POST":
        materielEntre.delete()
        return redirect("materielEntre:materielEntre_list")

    return render(
        request,
        "materielEntre/confirm_delete.html",
        {"materielEntre": materielEntre},
    )