from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from .models import h_DepenseSoc
from .forms import h_DepenseSocForm
from users.models import AppUser


# ============================================================
# LISTE DES DÉPENSES SOC
# ============================================================

def h_soc_depense_list(request):

    depenses = DepenseSoc.objects.select_related(
        "enregistre_par"
    ).all()

    # -------------------------
    # FILTRES
    # -------------------------

    titre = request.GET.get("titre", "").strip()
    date_debut = request.GET.get("date_debut", "").strip()
    date_fin = request.GET.get("date_fin", "").strip()

    if titre:
        depenses = depenses.filter(
            titre__icontains=titre
        )

    if date_debut:
        depenses = depenses.filter(
            date__gte=date_debut
        )

    if date_fin:
        depenses = depenses.filter(
            date__lte=date_fin
        )

    context = {
        "depenses": depenses,
        "titre": titre,
        "date_debut": date_debut,
        "date_fin": date_fin,
    }

    return render(
        request,
        "depensesoc/list.html",
        context
    )


# ============================================================
# AJOUTER
# ============================================================

def h_soc_depense_add(request):

    if request.method == "POST":

        form = DepenseSocForm(request.POST)

        if form.is_valid():

            depense = form.save(commit=False)

            # -------------------------
            # UTILISATEUR CONNECTÉ
            # -------------------------

            user_id = request.session.get("user_id")

            if user_id:
                depense.enregistre_par = AppUser.objects.filter(
                    id=user_id
                ).first()

            # -------------------------
            # ENREGISTREMENT
            # -------------------------

            depense.save()

            messages.success(
                request,
                "Dépense enregistrée avec succès."
            )

            return redirect(
                "depensesoc:h_soc_depense_list"
            )

    else:
        form = h_DepenseSocForm()

    return render(
        request,
        "h/depensesoc/form.html",
        {
            "form": form,
            "action": "Ajouter"
        }
    )


# ============================================================
# MODIFIER
# ============================================================

def h_soc_depense_edit(request, id):

    depense = get_object_or_404(
        h_DepenseSoc,
        id=id
    )

    if request.method == "POST":

        form = h_DepenseSocForm(
            request.POST,
            instance=depense
        )

        if form.is_valid():

            depense = form.save(commit=False)

            # -------------------------
            # NE PAS CHANGER
            # L'UTILISATEUR QUI A CRÉÉ
            # -------------------------

            depense.save()

            messages.success(
                request,
                "Dépense modifiée avec succès."
            )

            return redirect(
                "depensesoc:soc_depense_list"
            )

    else:

        form = h_DepenseSocForm(
            instance=depense
        )

    return render(
        request,
        "h/depensesoc/form.html",
        {
            "form": form,
            "depense": depense,
            "action": "Modifier"
        }
    )


# ============================================================
# SUPPRIMER
# ============================================================

def h_soc_depense_delete(request, id):

    depense = get_object_or_404(
        h_DepenseSoc,
        id=id
    )

    if request.method == "POST":

        depense.delete()

        messages.success(
            request,
            "Dépense supprimée avec succès."
        )

        return redirect(
            "depensesoc:h_soc_depense_list"
        )

    return render(
        request,
        "h/depensesoc/delete.html",
        {
            "depense": depense
        }
    )
