from decimal import Decimal

from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum
from django.forms import inlineformset_factory
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from audit.utils import enregistrer_action
from personnel.models import Personnel
from users.models import AppUser

from .forms import DepotForm, DistributionForm
from .models import Depot, Distribution

# ============================================================
# FORMSET DES DISTRIBUTIONS
# ============================================================

DistributionFormSet = inlineformset_factory(
    Depot,
    Distribution,
    form=DistributionForm,
    extra=2,
    can_delete=True,
)


# ============================================================
# UTILITAIRES
# ============================================================


def get_depot_user(request):
    """
    Retourne l'utilisateur connecté à partir de la session GALAXY.
    """
    user_id = request.session.get("user_id")

    if not user_id:
        return None

    return AppUser.objects.filter(pk=user_id).first()


def depot_est_modifiable_par(depot, user):
    """
    Seul l'enregistreur du dépôt peut le modifier ou le supprimer.
    """
    if user is None:
        return False

    return depot.enregistre_par_id == user.pk


def depot_droits_contexte(depots, user):
    """
    Ajoute à chaque dépôt un indicateur utilisable dans le template.
    Cela évite les comparaisons fragiles entre les identifiants
    de session (souvent des chaînes) et les identifiants numériques.
    """
    for depot in depots:
        depot.peut_modifier = depot_est_modifiable_par(depot, user)

    return depots


def depot_montant_distributions(depot):
    """
    Calcule le total des distributions d'un dépôt.
    """
    return depot.distributions.aggregate(total=Sum("montant"))["total"] or Decimal(
        "0.00"
    )


def depot_donnees_audit(depot):
    """
    Prépare les informations principales pour le journal d'audit.
    """
    return {
        "nom": depot.nom,
        "montantG": str(depot.montantG),
        "montant": str(depot.montant),
        "personnel_1": (str(depot.personnel_1_id) if depot.personnel_1_id else None),
        "personnel_2": (str(depot.personnel_2_id) if depot.personnel_2_id else None),
        "part_1": depot.part_1,
        "part_2": depot.part_2,
        "date": str(depot.date),
        "description": depot.description,
        "enregistre_par": (
            str(depot.enregistre_par_id) if depot.enregistre_par_id else None
        ),
    }


# ============================================================
# LISTE DES DÉPÔTS
# ============================================================


def depot_list(request):
    """
    Affiche les dépôts avec filtres et totaux.
    Les utilisateurs peuvent consulter les dépôts, mais seuls
    les enregistreurs peuvent modifier ou supprimer les leurs.
    """
    user = get_depot_user(request)

    depots = (
        Depot.objects.select_related(
            "personnel_1",
            "personnel_2",
            "enregistre_par",
        )
        .prefetch_related(
            "distributions__distributeur",
        )
        .order_by("-date", "-id")
    )

    personnel = request.GET.get("personnel", "").strip()
    date_debut = request.GET.get("date_debut", "").strip()
    date_fin = request.GET.get("date_fin", "").strip()

    if personnel:
        depots = depots.filter(distributions__distributeur_id=personnel).distinct()

    if date_debut:
        depots = depots.filter(date__gte=date_debut)

    if date_fin:
        depots = depots.filter(date__lte=date_fin)

    # Calculs des totaux sur l'ensemble filtré, avant pagination.
    total_montant = depots.aggregate(total=Sum("montantG"))["total"] or Decimal("0.00")

    total_personnel = Distribution.objects.filter(depot__in=depots).aggregate(
        total=Sum("montant")
    )["total"] or Decimal("0.00")

    depots = depot_droits_contexte(list(depots), user)

    paginator = Paginator(depots, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "depots": page_obj,
        "page_obj": page_obj,
        "personnels": Personnel.objects.all().order_by("nom"),
        "personnel": personnel,
        "date_debut": date_debut,
        "date_fin": date_fin,
        "total_montant": total_montant,
        "total_personnel": total_personnel,
    }

    return render(request, "depot/list.html", context)


# ============================================================
# IMPRESSION DES DÉPÔTS
# ============================================================


def depot_print(request):
    """
    Prépare l'impression des dépôts en conservant les filtres
    par personnel et par période.
    """
    depots = (
        Depot.objects.select_related(
            "personnel_1",
            "personnel_2",
            "enregistre_par",
        )
        .prefetch_related(
            "distributions__distributeur",
        )
        .order_by("-date", "-id")
    )

    personnel = request.GET.get("personnel", "").strip()
    date_debut = request.GET.get("date_debut", "").strip()
    date_fin = request.GET.get("date_fin", "").strip()

    if personnel:
        depots = depots.filter(distributions__distributeur_id=personnel).distinct()

    if date_debut:
        depots = depots.filter(date__gte=date_debut)

    if date_fin:
        depots = depots.filter(date__lte=date_fin)

    total_montant = depots.aggregate(total=Sum("montantG"))["total"] or Decimal("0.00")

    total_distribution = Distribution.objects.filter(depot__in=depots).aggregate(
        total=Sum("montant")
    )["total"] or Decimal("0.00")

    context = {
        "depots": depots,
        "date_debut": date_debut,
        "date_fin": date_fin,
        "personnel": personnel,
        "total_montant": total_montant,
        "total_distribution": total_distribution,
    }

    return render(request, "depot/print.html", context)


# ============================================================
# AJOUT D'UN DÉPÔT
# ============================================================


def depot_add(request):
    """
    Crée un dépôt et ses distributions.
    L'utilisateur connecté est automatiquement enregistré
    comme auteur du dépôt.
    """
    user = get_depot_user(request)

    if user is None:
        messages.error(
            request,
            "Vous devez être connecté pour enregistrer un dépôt.",
        )
        return redirect("depot:depot_list")

    if request.method == "POST":
        form = DepotForm(request.POST)
        formset = DistributionFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            distributions_a_sauver = formset.save(commit=False)

            total_distributions = sum(
                (
                    distribution.montant or Decimal("0.00")
                    for distribution in distributions_a_sauver
                ),
                Decimal("0.00"),
            )

            depot_temporaire = form.save(commit=False)

            if total_distributions > depot_temporaire.montantG:
                messages.error(
                    request,
                    "Le total des distributions ne peut pas dépasser "
                    "le montant global du dépôt.",
                )
            else:
                try:
                    with transaction.atomic():
                        depot = form.save(commit=False)
                        depot.enregistre_par = user
                        depot.save()

                        formset.instance = depot

                        # Les formulaires de création peuvent avoir
                        # été validés sans instance persistée.
                        for distribution in distributions_a_sauver:
                            distribution.depot = depot
                            distribution.save()

                        formset.save_m2m()

                        enregistrer_action(
                            request,
                            "CREATE",
                            "Depot",
                            depot.pk,
                            nouvelle=depot_donnees_audit(depot),
                            description="Création d'un dépôt",
                        )

                    messages.success(
                        request,
                        "Le dépôt a été enregistré avec succès.",
                    )
                    return redirect("depot:depot_list")

                except Exception:
                    messages.error(
                        request,
                        "Une erreur est survenue lors de " "l'enregistrement du dépôt.",
                    )
                    raise

        else:
            messages.error(
                request,
                "Veuillez corriger les erreurs du formulaire.",
            )
    else:
        form = DepotForm()
        formset = DistributionFormSet()

    context = {
        "form": form,
        "formset": formset,
        "titre": "Ajouter un dépôt",
    }

    return render(request, "depot/form.html", context)


# ============================================================
# MODIFICATION D'UN DÉPÔT
# ============================================================


def depot_edit(request, pk):
    """
    Seul l'utilisateur qui a enregistré le dépôt peut le modifier.
    Le propriétaire du dépôt n'est jamais changé par le formulaire.
    """
    user = get_depot_user(request)

    if user is None:
        messages.error(
            request,
            "Vous devez être connecté pour modifier un dépôt.",
        )
        return redirect("depot:depot_list")

    depot = get_object_or_404(
        Depot.objects.select_related("enregistre_par"),
        pk=pk,
    )

    if not depot_est_modifiable_par(depot, user):
        messages.error(
            request,
            "Modification refusée : seul l'enregistreur de ce dépôt "
            "peut le modifier.",
        )
        return redirect("depot:depot_list")

    if request.method == "POST":
        form = DepotForm(request.POST, instance=depot)
        formset = DistributionFormSet(
            request.POST,
            instance=depot,
        )

        if form.is_valid() and formset.is_valid():
            try:
                with transaction.atomic():
                    ancienne = depot_donnees_audit(depot)

                    depot_modifie = form.save(commit=False)

                    # Protection contre toute modification du créateur.
                    depot_modifie.enregistre_par = user
                    depot_modifie.save()

                    formset.instance = depot_modifie

                    distributions_a_sauver = formset.save(commit=False)

                    total_distributions = sum(
                        (
                            distribution.montant or Decimal("0.00")
                            for distribution in distributions_a_sauver
                        ),
                        Decimal("0.00"),
                    )

                    # Les distributions existantes marquées pour
                    # suppression ne doivent pas compter dans le total.
                    ids_a_supprimer = {obj.pk for obj in formset.deleted_objects}

                    total_distributions += sum(
                        (
                            distribution.montant or Decimal("0.00")
                            for distribution in depot_modifie.distributions.all()
                            if distribution.pk not in ids_a_supprimer
                            and distribution.pk
                            not in {obj.pk for obj in distributions_a_sauver if obj.pk}
                        ),
                        Decimal("0.00"),
                    )

                    if total_distributions > depot_modifie.montantG:
                        raise ValueError(
                            "Le total des distributions ne peut pas "
                            "dépasser le montant global du dépôt."
                        )

                    for distribution in distributions_a_sauver:
                        distribution.depot = depot_modifie
                        distribution.save()

                    for distribution in formset.deleted_objects:
                        distribution.delete()

                    formset.save_m2m()

                    enregistrer_action(
                        request,
                        "UPDATE",
                        "Depot",
                        depot_modifie.pk,
                        ancienne=ancienne,
                        nouvelle=depot_donnees_audit(depot_modifie),
                        description="Modification d'un dépôt",
                    )

                messages.success(
                    request,
                    "Le dépôt a été modifié avec succès.",
                )
                return redirect("depot:depot_list")

            except ValueError as exc:
                messages.error(request, str(exc))
            except Exception:
                messages.error(
                    request,
                    "Une erreur est survenue lors de la modification " "du dépôt.",
                )
                raise

        else:
            messages.error(
                request,
                "Veuillez corriger les erreurs du formulaire.",
            )
    else:
        form = DepotForm(instance=depot)
        formset = DistributionFormSet(instance=depot)

    context = {
        "form": form,
        "formset": formset,
        "depot": depot,
        "titre": "Modifier un dépôt",
    }

    return render(request, "depot/form.html", context)


# ============================================================
# SUPPRESSION D'UN DÉPÔT
# ============================================================


@require_POST
def depot_delete(request, id):
    depot = get_object_or_404(Depot, pk=id)

    # Récupérer l'utilisateur connecté
    user_id = request.session.get("user_id")

    # Vérifier que seul le créateur peut supprimer son dépôt
    if not user_id or depot.enregistre_par_id != user_id:
        messages.error(request, "Vous n'êtes pas autorisé à supprimer ce dépôt.")
        return redirect("depot:depot_list")

    depot.delete()

    messages.success(request, "Le dépôt a été supprimé avec succès.")
    return redirect("depot:depot_list")
