from django.contrib import messages
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render

from audit.utils import enregistrer_action
from users.decorators import session_login_required
from django.core.paginator import Paginator
from .models import Retour
from .forms import RetourForm
from .models import Retour


# ==========================================
# LISTE
# ==========================================
@session_login_required
def retour_list(request):
    queryset = (
        Retour.objects
        .select_related("enregistrer_par")
        .order_by("-created_at", "-id")
    )

    # ===============================
    # FILTRES
    # ===============================
    montant = request.GET.get("montant", "").strip()
    user = request.GET.get("user", "").strip()

    if montant:
        queryset = queryset.filter(montant__icontains=montant)

    if user:
        queryset = queryset.filter(
            Q(enregistrer_par__username__icontains=user)
        )

    total_retours = (
        queryset.aggregate(total=Sum("montant"))["total"] or 0
    )

    # ===============================
    # PAGINATION : 15 RETOURS PAR PAGE
    # ===============================
    paginator = Paginator(queryset, 15)
    page_obj = paginator.get_page(request.GET.get("page"))

    context = {
        "retours": page_obj,
        "page_obj": page_obj,
        "montant": montant,
        "user": user,
        "total_retours": total_retours,
        "query_params": request.GET.copy(),
    }

    context["query_params"].pop("page", None)
    context["query_params"] = context["query_params"].urlencode()

    return render(request, "retours/list.html", context)

# ==========================================
# DETAIL
# ==========================================
@session_login_required
def retour_detail(request, id):

    retour = get_object_or_404(Retour, id=id)

    return render(request, "retours/detail.html", {"retour": retour})


# ==========================================
# AJOUT
# ==========================================
@session_login_required
def retour_add(request):

    if request.method == "POST":

        form = RetourForm(request.POST)

        if form.is_valid():

            retour = form.save(commit=False)

            user_id = request.session.get("user_id")

            if user_id:
                from users.models import AppUser

                retour.enregistrer_par = AppUser.objects.get(id=user_id)

            retour.save()

            enregistrer_action(
                request,
                "CREATE",
                "Retour",
                retour.id,
                nouvelle={"montant": str(retour.montant)},
                description="Création d'un retour",
            )

            messages.success(request, "Retour enregistré avec succès.")

            return redirect("retours:retour_list")

    else:
        form = RetourForm()

    return render(request, "retours/form.html", {"form": form, "action": "Ajouter"})


# ==========================================
# MODIFICATION
# ==========================================
@session_login_required
def retour_edit(request, id):

    retour = get_object_or_404(Retour, id=id)

    ancienne = str(retour)

    if request.method == "POST":

        form = RetourForm(request.POST, instance=retour)

        if form.is_valid():

            retour = form.save()

            enregistrer_action(
                request,
                "UPDATE",
                "Retour",
                retour.id,
                ancienne=ancienne,
                nouvelle=str(retour),
                description="Modification d'un retour",
            )

            messages.success(request, "Retour modifié avec succès.")

            return redirect("retours:retour_list")

    else:

        form = RetourForm(instance=retour)

    return render(request, "retours/form.html", {"form": form, "action": "Modifier"})


# ==========================================
# SUPPRESSION
# ==========================================
@session_login_required
def retour_delete(request, id):

    retour = get_object_or_404(Retour, id=id)

    if request.method == "POST":

        enregistrer_action(
            request,
            "DELETE",
            "Retour",
            retour.id,
            ancienne=str(retour),
            description="Suppression d'un retour",
        )

        retour.delete()

        messages.success(request, "Retour supprimé avec succès.")

        return redirect("retours:retour_list")

    return render(request, "retours/confirm.html", {"retour": retour})
