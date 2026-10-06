from django.contrib import messages
from django.db import transaction
from django.shortcuts import render, get_object_or_404, redirect

from .models import MaterielEntre
from .forms import MaterielEntreForm

from audit.utils import enregistrer_action


# ============================================================
# LISTE
# ============================================================

def materielEntre_list(request):

    queryset = MaterielEntre.objects.select_related(
        "id_MaterielSort",
        "id_MaterielSort__id_Materiel"
    ).order_by("-dateEntre", "-id")

    materiel = request.GET.get("materiel", "").strip()
    demandeur = request.GET.get("demandeur", "").strip()
    date = request.GET.get("date", "").strip()

    if materiel:
        queryset = queryset.filter(
            id_MaterielSort__id_Materiel__nom__icontains=materiel
        )

    if demandeur:
        queryset = queryset.filter(
            id_MaterielSort__demandeur__icontains=demandeur
        )

    if date:
        queryset = queryset.filter(
            dateEntre=date
        )

    return render(
        request,
        "materielEntre/list.html",
        {
            "entrees": queryset,
            "materiel": materiel,
            "demandeur": demandeur,
            "date": date,
        }
    )


# ============================================================
# DETAIL
# ============================================================

def materielEntre_detail(request, id):

    entree = get_object_or_404(
        MaterielEntre.objects.select_related(
            "id_MaterielSort",
            "id_MaterielSort__id_Materiel"
        ),
        id=id
    )

    return render(
        request,
        "materielEntre/detail.html",
        {
            "entree": entree
        }
    )


# ============================================================
# AJOUT
# ============================================================

@transaction.atomic
def materielEntre_add(request):

    if request.method == "POST":

        form = MaterielEntreForm(request.POST)

        if form.is_valid():

            entree = form.save()

            enregistrer_action(
                request,
                "CREATE",
                "Matériel Entrée",
                entree.id,
                nouvelle={
                    "materiel": str(
                        entree.id_MaterielSort.id_Materiel
                    ),
                    "demandeur": (
                        entree.id_MaterielSort.demandeur
                    ),
                    "quantite": str(
                        entree.Nb_Entre
                    ),
                    "responsable": (
                        entree.responsable_entree
                    ),
                    "date": str(
                        entree.dateEntre
                    ),
                },
                description="Création d'une entrée matériel"
            )

            messages.success(
                request,
                "✅ Entrée matériel enregistrée avec succès."
            )

            return redirect(
                "materielEntre:materielEntre_list"
            )

        messages.error(
            request,
            "❌ Impossible d'enregistrer l'entrée. "
            "Veuillez corriger les erreurs."
        )

    else:

        form = MaterielEntreForm()

    return render(
        request,
        "materielEntre/form.html",
        {
            "form": form
        }
    )


# ============================================================
# MODIFICATION
# ============================================================

@transaction.atomic
def materielEntre_edit(request, id):

    entree = get_object_or_404(
        MaterielEntre,
        id=id
    )

    ancienne = {
        "materiel": str(
            entree.id_MaterielSort.id_Materiel
        ),
        "demandeur": (
            entree.id_MaterielSort.demandeur
        ),
        "quantite": str(
            entree.Nb_Entre
        ),
        "responsable": (
            entree.responsable_entree
        ),
        "date": str(
            entree.dateEntre
        ),
    }

    if request.method == "POST":

        form = MaterielEntreForm(
            request.POST,
            instance=entree
        )

        if form.is_valid():

            entree = form.save()

            enregistrer_action(
                request,
                "UPDATE",
                "Matériel Entrée",
                entree.id,
                ancienne=ancienne,
                nouvelle={
                    "materiel": str(
                        entree.id_MaterielSort.id_Materiel
                    ),
                    "demandeur": (
                        entree.id_MaterielSort.demandeur
                    ),
                    "quantite": str(
                        entree.Nb_Entre
                    ),
                    "responsable": (
                        entree.responsable_entree
                    ),
                    "date": str(
                        entree.dateEntre
                    ),
                },
                description="Modification d'une entrée matériel"
            )

            messages.success(
                request,
                "✅ Entrée matériel modifiée avec succès."
            )

            return redirect(
                "materielEntre:materielEntre_list"
            )

        messages.error(
            request,
            "❌ Impossible de modifier l'entrée. "
            "Veuillez corriger les erreurs."
        )

    else:

        form = MaterielEntreForm(
            instance=entree
        )

    return render(
        request,
        "materielEntre/form.html",
        {
            "form": form,
            "entree": entree,
        }
    )


# ============================================================
# SUPPRESSION
# ============================================================

@transaction.atomic
def materielEntre_delete(request, id):

    entree = get_object_or_404(
        MaterielEntre.objects.select_related(
            "id_MaterielSort",
            "id_MaterielSort__id_Materiel"
        ),
        id=id
    )

    ancienne = {
        "materiel": str(
            entree.id_MaterielSort.id_Materiel
        ),
        "demandeur": (
            entree.id_MaterielSort.demandeur
        ),
        "quantite": str(
            entree.Nb_Entre
        ),
        "responsable": (
            entree.responsable_entree
        ),
        "date": str(
            entree.dateEntre
        ),
    }

    if request.method == "POST":

        enregistrer_action(
            request,
            "DELETE",
            "Matériel Entrée",
            entree.id,
            ancienne=ancienne,
            description="Suppression d'une entrée matériel"
        )

        entree.delete()

        messages.success(
            request,
            "✅ Entrée matériel supprimée avec succès."
        )

        return redirect(
            "materielEntre:materielEntre_list"
        )

    return render(
        request,
        "materielEntre/confirm_delete.html",
        {
            "entree": entree
        }
    )
