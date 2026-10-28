from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from users.models import AppUser,H_AppUser

from .forms import DepenseSocForm,H_DepenseSocForm
from .models import DepenseSoc,H_DepenseSoc
from django.core.paginator import Paginator
from django.shortcuts import render
from users.decorators import session_login_required
# ============================================================
# LISTE DES DÉPENSES SOC
# ============================================================
@session_login_required
def soc_depense_list(request):
    depenses = DepenseSoc.objects.select_related("enregistre_par").all()

    # Filtres
    titre = request.GET.get("titre", "").strip()
    date_debut = request.GET.get("date_debut", "").strip()
    date_fin = request.GET.get("date_fin", "").strip()

    if titre:
        depenses = depenses.filter(titre__icontains=titre)

    if date_debut:
        depenses = depenses.filter(date__gte=date_debut)

    if date_fin:
        depenses = depenses.filter(date__lte=date_fin)

    # Pagination : 10 dépenses par page
    paginator = Paginator(depenses.order_by("-date", "-id"), 8)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "depenses": page_obj,
        "page_obj": page_obj,
        "titre": titre,
        "date_debut": date_debut,
        "date_fin": date_fin,
    }

    return render(request, "depensesoc/list.html", context)


# ============================================================
# AJOUTER
# ============================================================
@session_login_required
def soc_depense_add(request):

    if request.method == "POST":

        form = DepenseSocForm(request.POST)

        if form.is_valid():

            depense = form.save(commit=False)

            # -------------------------
            # UTILISATEUR CONNECTÉ
            # -------------------------

            user_id = request.session.get("user_id")

            if user_id:
                depense.enregistre_par = AppUser.objects.filter(id=user_id).first()

            # -------------------------
            # ENREGISTREMENT
            # -------------------------

            depense.save()

            messages.success(request, "Dépense enregistrée avec succès.")

            return redirect("depensesoc:soc_depense_list")

    else:
        form = DepenseSocForm()

    return render(request, "depensesoc/form.html", {"form": form, "action": "Ajouter"})


# ============================================================
# MODIFIER
# ============================================================
@session_login_required
def soc_depense_edit(request, id):

    depense = get_object_or_404(DepenseSoc, id=id)

    if request.method == "POST":

        form = DepenseSocForm(request.POST, instance=depense)

        if form.is_valid():

            depense = form.save(commit=False)

            # -------------------------
            # NE PAS CHANGER
            # L'UTILISATEUR QUI A CRÉÉ
            # -------------------------

            depense.save()

            messages.success(request, "Dépense modifiée avec succès.")

            return redirect("depensesoc:soc_depense_list")

    else:

        form = DepenseSocForm(instance=depense)

    return render(
        request,
        "depensesoc/form.html",
        {"form": form, "depense": depense, "action": "Modifier"},
    )


# ============================================================
# SUPPRIMER
# ============================================================
@session_login_required
def soc_depense_delete(request, id):

    depense = get_object_or_404(DepenseSoc, id=id)

    if request.method == "POST":

        depense.delete()

        messages.success(request, "Dépense supprimée avec succès.")

        return redirect("depensesoc:soc_depense_list")

    return render(request, "depensesoc/delete.html", {"depense": depense})


# ============================================================
# ENTREPRISE H
# ============================================================
@session_login_required
def h_soc_depense_list(request):
    depenses = H_DepenseSoc.objects.select_related("enregistre_par").all()

    # Filtres
    titre = request.GET.get("titre", "").strip()
    date_debut = request.GET.get("date_debut", "").strip()
    date_fin = request.GET.get("date_fin", "").strip()

    if titre:
        depenses = depenses.filter(titre__icontains=titre)

    if date_debut:
        depenses = depenses.filter(date__gte=date_debut)

    if date_fin:
        depenses = depenses.filter(date__lte=date_fin)

    # Pagination : 10 dépenses par page
    paginator = Paginator(depenses.order_by("-date", "-id"), 8)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "depenses": page_obj,
        "page_obj": page_obj,
        "titre": titre,
        "date_debut": date_debut,
        "date_fin": date_fin,
    }

    return render(request, "depensesoc/h_list.html", context)


# ============================================================
# AJOUTER
# ============================================================
@session_login_required
def h_soc_depense_add(request):
    if request.method == "POST":
        form = H_DepenseSocForm(request.POST)

        if form.is_valid():
            depense = form.save(commit=False)

            user_id = request.session.get("h_user_id")
            if user_id:
                depense.enregistre_par = H_AppUser.objects.filter(
                    id=user_id
                ).first()

            depense.save()
            messages.success(request, "Dépense MCCR enregistrée avec succès.")
            return redirect("depensesoc:h_soc_depense_list")
    else:
        form = H_DepenseSocForm()

    return render(
        request,
        "depensesoc/h_form.html",
        {"form": form, "action": "Ajouter"},
    )
# ============================================================
# MODIFIER
# ============================================================
@session_login_required
def h_soc_depense_edit(request, id):

    depense = get_object_or_404(H_DepenseSoc, id=id)

    if request.method == "POST":

        form = H_DepenseSocForm(request.POST, instance=depense)

        if form.is_valid():

            depense = form.save(commit=False)

            # -------------------------
            # NE PAS CHANGER
            # L'UTILISATEUR QUI A CRÉÉ
            # -------------------------

            depense.save()

            messages.success(request, "Dépense modifiée avec succès.")

            return redirect("depensesoc:h_soc_depense_list")

    else:

        form = H_DepenseSocForm(instance=depense)

    return render(
        request,
        "depensesoc/h_form.html",
        {"form": form, "depense": depense, "action": "Modifier"},
    )


# ============================================================
# SUPPRIMER
# ============================================================
@session_login_required
def h_soc_depense_delete(request, id):

    depense = get_object_or_404(H_DepenseSoc, id=id)

    if request.method == "POST":

        depense.delete()

        messages.success(request, "Dépense supprimée avec succès.")

        return redirect("depensesoc:h_soc_depense_list")

    return render(request, "depensesoc/delete.html", {"depense": depense})
