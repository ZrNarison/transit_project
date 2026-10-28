from django.contrib import messages
from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, redirect, render

from audit.models import Audit
from logs.models import Log
from users.models import AppUser
from users.decorators import session_login_required
from .forms import EntretienForm
from .models import Entretien


def get_client_ip(request):

    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")

    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]

    else:
        ip = request.META.get("REMOTE_ADDR")

    return ip


def get_user(request):

    user_id = request.session.get("user_id")

    if user_id:

        return AppUser.objects.filter(id=user_id).first()

    return None


@session_login_required
def entretien_create(request):

    utilisateur = get_user(request)

    if request.method == "POST":

        form = EntretienForm(request.POST)

        if form.is_valid():

            entretien = form.save(commit=False)

            entretien.enregistrer_par = utilisateur

            entretien.save()

            # ======================
            # AUDIT CREATE
            # ======================

            Audit.objects.create(
                utilisateur=utilisateur,
                action="CREATE",
                table="Entretien",
                objet_id=entretien.id,
                nouvelle_valeur={
                    "vehicule": entretien.num_vehicule,
                    "piece": entretien.piece_acheter,
                    "nombre": entretien.nombre,
                    "prix": str(entretien.prix_du_piece),
                },
                description=f"Création entretien véhicule {entretien.num_vehicule}",
            )

            # ======================
            # LOG SYSTEME
            # ======================

            Log.objects.create(
                level="INFO",
                module="entretien",
                message=f"Nouvel entretien créé : {entretien}",
                ip_address=get_client_ip(request),
            )

            messages.success(request, "Entretien enregistré avec succès.")

            return redirect("entretien:list")

    else:

        form = EntretienForm()

    return render(request, "entretien/form.html", {"form": form})

# =========================================================
# LISTE DES ENTRETIENS
# =========================================================
@session_login_required
def entretien_list(request):
    entretiens = Entretien.objects.all().order_by("-date_cree")

    return render(
        request,
        "entretien/list.html",
        {"entretiens": entretiens},
    )


# =========================================================
# CRÉATION D'UN ENTRETIEN
# =========================================================
@session_login_required
def entretien_create(request):
    utilisateur = get_user(request)

    if request.method == "POST":
        form = EntretienForm(request.POST)

        if form.is_valid():
            entretien = form.save(commit=False)
            entretien.enregistrer_par = utilisateur
            entretien.save()

            # AUDIT CREATE
            Audit.objects.create(
                utilisateur=utilisateur,
                action="CREATE",
                table="Entretien",
                objet_id=entretien.id,
                nouvelle_valeur={
                    "vehicule": entretien.num_vehicule,
                    "piece": entretien.piece_acheter,
                    "nombre": entretien.nombre,
                    "prix": str(entretien.prix_du_piece),
                },
                description=(
                    f"Création entretien véhicule "
                    f"{entretien.num_vehicule}"
                ),
            )

            # LOG SYSTÈME
            Log.objects.create(
                level="INFO",
                module="entretien",
                message=f"Nouvel entretien créé : {entretien}",
                ip_address=get_client_ip(request),
            )

            messages.success(
                request,
                "Entretien enregistré avec succès.",
            )

            return redirect("entretien:list")

    else:
        form = EntretienForm()

    return render(
        request,
        "entretien/form.html",
        {"form": form},
    )


# =========================================================
# MODIFICATION D'UN ENTRETIEN
# SEUL L'ENREGISTREUR PEUT MODIFIER
# =========================================================
@session_login_required
def entretien_update(request, id):
    entretien = get_object_or_404(Entretien, pk=id)
    utilisateur = get_user(request)

    # Vérification de propriété côté serveur
    if (
        utilisateur is None
        or entretien.enregistrer_par_id != utilisateur.pk
    ):
        messages.error(
            request,
            "Vous ne pouvez modifier que les entretiens "
            "que vous avez enregistrés.",
        )
        return redirect("entretien:list")

    ancienne = {
        "vehicule": entretien.num_vehicule,
        "piece": entretien.piece_acheter,
        "nombre": entretien.nombre,
        "prix": str(entretien.prix_du_piece),
    }

    if request.method == "POST":
        form = EntretienForm(
            request.POST,
            instance=entretien,
        )

        if form.is_valid():
            entretien_modifie = form.save()

            nouvelle = {
                "vehicule": entretien_modifie.num_vehicule,
                "piece": entretien_modifie.piece_acheter,
                "nombre": entretien_modifie.nombre,
                "prix": str(entretien_modifie.prix_du_piece),
            }

            # AUDIT UPDATE
            Audit.objects.create(
                utilisateur=utilisateur,
                action="UPDATE",
                table="Entretien",
                objet_id=entretien_modifie.id,
                ancienne_valeur=ancienne,
                nouvelle_valeur=nouvelle,
                description=(
                    f"Modification entretien "
                    f"{entretien_modifie.id}"
                ),
            )

            # LOG SYSTÈME
            Log.objects.create(
                level="INFO",
                module="entretien",
                message=(
                    f"Modification entretien ID "
                    f"{entretien_modifie.id}"
                ),
                ip_address=get_client_ip(request),
            )

            messages.success(
                request,
                "Entretien modifié avec succès.",
            )

            return redirect("entretien:list")

    else:
        form = EntretienForm(instance=entretien)

    return render(
        request,
        "entretien/form.html",
        {
            "form": form,
            "entretien": entretien,
        },
    )


# =========================================================
# SUPPRESSION D'UN ENTRETIEN
# SEUL L'ENREGISTREUR PEUT SUPPRIMER
# =========================================================
@session_login_required
def entretien_delete(request, id):
    entretien = get_object_or_404(Entretien, pk=id)
    utilisateur = get_user(request)

    # Vérification de propriété côté serveur
    if (
        utilisateur is None
        or entretien.enregistrer_par_id != utilisateur.pk
    ):
        messages.error(
            request,
            "Vous ne pouvez supprimer que les entretiens "
            "que vous avez enregistrés.",
        )
        return redirect("entretien:list")

    # La suppression doit passer par POST
    if request.method != "POST":
        return render(
            request,
            "entretien/confirm_delete.html",
            {"entretien": entretien},
        )

    ancienne = {
        "vehicule": entretien.num_vehicule,
        "piece": entretien.piece_acheter,
        "nombre": entretien.nombre,
        "prix": str(entretien.prix_du_piece),
    }

    entretien_id = entretien.pk

    # AUDIT DELETE avant suppression
    Audit.objects.create(
        utilisateur=utilisateur,
        action="DELETE",
        table="Entretien",
        objet_id=entretien_id,
        ancienne_valeur=ancienne,
        description=f"Suppression entretien ID {entretien_id}",
    )

    # LOG SYSTÈME
    Log.objects.create(
        level="WARNING",
        module="entretien",
        message=f"Suppression entretien ID {entretien_id}",
        ip_address=get_client_ip(request),
    )

    entretien.delete()

    messages.success(
        request,
        "Entretien supprimé avec succès.",
    )

    return redirect("entretien:list")