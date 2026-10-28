from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q , Sum
from django.shortcuts import get_object_or_404, redirect, render

from audit.utils import enregistrer_action
from users.models import AppUser
from users.decorators import session_login_required
from .forms import AvanceClientForm
from .models import AvanceClient

# ==========================================
# LISTE DES AVANCES CLIENTS
# ==========================================
@session_login_required
def avanceclient_list(request):
    avances = (
        AvanceClient.objects
        .select_related("client", "enregistrer_par")
        .prefetch_related("remboursements")
        .order_by("-date", "-id")
    )

    recherche = request.GET.get("client", "").strip()

    if recherche:
        avances = avances.filter(
            Q(client__nom__icontains=recherche)
            | Q(client__prenom__icontains=recherche)
        )

    paginator = Paginator(avances, 15)
    page_obj = paginator.get_page(request.GET.get("page"))

    # Autoriser les actions uniquement pour le créateur
    # et si aucune utilisation ni aucun remboursement n'existe.
    user_id = request.session.get("user_id")

    for avance in page_obj.object_list:
        avance.modifiable = (
            user_id is not None
            and avance.enregistrer_par_id is not None
            and str(avance.enregistrer_par_id) == str(user_id)
            and not avance.remboursements.all()
            and avance.montant_retour == 0
            and avance.montant_utilise == 0
        )

    query_params = request.GET.copy()
    query_params.pop("page", None)

    return render(
        request,
        "avanceclient/list.html",
        {
            "avances": page_obj,
            "page_obj": page_obj,
            "client": recherche,
            "query_params": query_params.urlencode(),
        },
    )
# ==========================================
# AJOUT
# ==========================================
@session_login_required
def avanceclient_add(request):

    if request.method == "POST":

        form = AvanceClientForm(request.POST)

        if form.is_valid():

            avance = form.save(commit=False)

            user_id = request.session.get("user_id")

            if user_id:

                try:

                    avance.enregistrer_par = AppUser.objects.get(id=user_id)

                except AppUser.DoesNotExist:

                    avance.enregistrer_par = None

            avance.save()

            enregistrer_action(
                request,
                "CREATE",
                "AvanceClient",
                avance.id,
                nouvelle={
                    "client": str(avance.client),
                    "montant": str(avance.montant),
                    "type": avance.type_avance,
                },
                description="Création d'une avance client",
            )

            messages.success(request, "Avance client enregistrée.")

            return redirect("avanceclient:list")

    else:

        form = AvanceClientForm()

    return render(
        request, "avanceclient/form.html", {"form": form, "action": "Ajouter"}
    )


# ==========================================
# DETAIL
# ==========================================
@session_login_required
def avanceclient_detail(request, id):
    avance = get_object_or_404(
        AvanceClient.objects.select_related(
            "client",
            "enregistrer_par",
        ),
        id=id,
    )

    remboursements = avance.remboursements.all().order_by(
        "-date_remboursement",
        "-id",
    )

    total_remboursements = (
        remboursements.aggregate(total=Sum("montant"))["total"] or 0
    )

    user_id = request.session.get("user_id")

    peut_modifier = (
        user_id is not None
        and avance.enregistrer_par_id is not None
        and str(avance.enregistrer_par_id) == str(user_id)
        and not remboursements.exists()
        and avance.montant_retour == 0
        and avance.montant_utilise == 0
    )

    return render(
        request,
        "avanceclient/detail.html",
        {
            "avance": avance,
            "remboursements": remboursements,
            "total_remboursements": total_remboursements,
            "peut_modifier": peut_modifier,
        },
    )

# ==========================================
# MODIFICATION D'UNE AVANCE CLIENT
# ==========================================
@session_login_required
def avanceclient_edit(request, id):
    avance = get_object_or_404(AvanceClient, id=id)

    user_id = request.session.get("user_id")

    # Vérifier que l'utilisateur est le créateur de l'avance.
    if (
        not user_id
        or avance.enregistrer_par_id is None
        or avance.enregistrer_par_id != int(user_id)
    ):
        messages.error(
            request,
            "Vous ne pouvez pas modifier cette avance.",
        )
        return redirect("avanceclient:list")

    # Interdire la modification après utilisation ou remboursement.
    if (
        avance.remboursements.exists()
        or avance.montant_retour > 0
        or avance.montant_utilise > 0
    ):
        messages.error(
            request,
            "Modification impossible : cette avance a déjà été "
            "utilisée ou remboursée.",
        )
        return redirect("avanceclient:list")

    ancienne = {
        "client": str(avance.client),
        "montant": str(avance.montant),
        "type": avance.type_avance,
        "motif": avance.motif,
    }

    if request.method == "POST":
        form = AvanceClientForm(
            request.POST,
            instance=avance,
        )

        if form.is_valid():
            # Revérifier avant l'enregistrement pour éviter
            # de modifier une avance devenue non modifiable.
            avance.refresh_from_db()

            if (
                avance.remboursements.exists()
                or avance.montant_retour > 0
                or avance.montant_utilise > 0
            ):
                messages.error(
                    request,
                    "Modification impossible : un remboursement "
                    "ou une utilisation a été enregistré.",
                )
                return redirect("avanceclient:list")

            avance_modifiee = form.save()

            nouvelle = {
                "client": str(avance_modifiee.client),
                "montant": str(avance_modifiee.montant),
                "type": avance_modifiee.type_avance,
                "motif": avance_modifiee.motif,
            }

            enregistrer_action(
                request,
                "UPDATE",
                "AvanceClient",
                id,
                ancienne=ancienne,
                nouvelle=nouvelle,
                description="Modification avance client",
            )

            messages.success(
                request,
                "Avance client modifiée avec succès.",
            )

            return redirect("avanceclient:list")

    else:
        form = AvanceClientForm(instance=avance)

    return render(
        request,
        "avanceclient/form.html",
        {
            "form": form,
            "action": "Modifier",
            "avance": avance,
        },
    )



# ==========================================
# SUPPRESSION D'UNE AVANCE CLIENT
# ==========================================
@session_login_required
def avanceclient_delete(request, id):
    avance = get_object_or_404(AvanceClient, id=id)

    user_id = request.session.get("user_id")

    # Vérifier que l'utilisateur est le créateur de l'avance.
    if (
        not user_id
        or avance.enregistrer_par_id is None
        or avance.enregistrer_par_id != int(user_id)
    ):
        messages.error(
            request,
            "Vous ne pouvez pas supprimer cette avance.",
        )
        return redirect("avanceclient:list")

    # Interdire la suppression après utilisation ou remboursement.
    if (
        avance.remboursements.exists()
        or avance.montant_retour > 0
        or avance.montant_utilise > 0
    ):
        messages.error(
            request,
            "Suppression impossible : cette avance a déjà été "
            "utilisée ou remboursée.",
        )
        return redirect("avanceclient:list")

    # La suppression doit obligatoirement passer par POST.
    if request.method != "POST":
        messages.error(
            request,
            "Confirmez la suppression à partir du formulaire prévu.",
        )
        return redirect("avanceclient:list")

    ancienne = {
        "client": str(avance.client),
        "montant": str(avance.montant),
        "type": avance.type_avance,
        "motif": avance.motif,
    }

    # Vérifier à nouveau les montants juste avant la suppression.
    avance.refresh_from_db()

    if (
        avance.remboursements.exists()
        or avance.montant_retour > 0
        or avance.montant_utilise > 0
    ):
        messages.error(
            request,
            "Suppression impossible : cette avance a été utilisée "
            "ou remboursée entre-temps.",
        )
        return redirect("avanceclient:list")

    # Enregistrer l'audit avant la suppression.
    enregistrer_action(
        request,
        "DELETE",
        "AvanceClient",
        id,
        ancienne=ancienne,
        description="Suppression avance client",
    )

    avance.delete()

    messages.success(
        request,
        "Avance client supprimée avec succès.",
    )

    return redirect("avanceclient:list")
