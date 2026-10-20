
from functools import wraps

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST
from decimal import Decimal

from django.db.models import Sum, Q, F, ExpressionWrapper, DecimalField
from django.shortcuts import render
from users.models import H_AppUser

from .forms_mccr import MateriauxMCCRForm, MouvementMateriauMCCRForm
from .models import MateriauMCCR, MouvementMateriauMCCR


# ============================================================
# AUTHENTIFICATION MCCR
# ============================================================

def mccr_required(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get("h_user_id")
        role = request.session.get("h_role")

        if not user_id or not role:
            messages.warning(
                request,
                "Veuillez vous connecter à votre compte MCCR.",
            )
            return redirect("users:login")

        utilisateur = H_AppUser.objects.filter(
            pk=user_id,
            role=role,
        ).first()

        if utilisateur is None:
            for key in (
                "h_user_id",
                "h_username",
                "h_role",
                "h_photo",
            ):
                request.session.pop(key, None)

            messages.error(
                request,
                "Votre session MCCR est invalide. Reconnectez-vous.",
            )
            return redirect("users:login")

        request.h_user = utilisateur
        return view_func(request, *args, **kwargs)

    return wrapper


# ============================================================
# OUTILS
# ============================================================

def est_enregistreur(objet, utilisateur):
    return (
        objet.enregistreur_id is not None
        and objet.enregistreur_id == utilisateur.pk
    )


def refuser_si_non_enregistreur(request, objet, destination):
    """
    Seul l'enregistreur d'origine peut modifier ou supprimer
    un enregistrement, conformément à la règle actuelle.
    """
    if est_enregistreur(objet, request.h_user):
        return None

    messages.error(
        request,
        "Action refusée : seul l'enregistreur d'origine "
        "peut modifier ou supprimer cet enregistrement.",
    )
    return redirect(destination)


def valeur_type(type_mouvement):
    """
    Accepte les valeurs utilisées par les choix Django :
    ENTREE, SORTIE et RETOUR.
    """
    return type_mouvement


# ============================================================
# DASHBOARD MCCR
# ============================================================

@mccr_required
def dashboard_mccr(request):
    materiaux = MateriauMCCR.objects.all().order_by("nom")

    # Le modèle MouvementMateriauMCCR ne possède pas
    # de relation "enregistreur".
    mouvements = (
        MouvementMateriauMCCR.objects
        .select_related("materiau")
        .order_by("-date_mouvement", "-pk")
    )

    ZERO = Decimal("0.00")

    # ---------------------------------------------------------
    # 1. TOTAUX DES QUANTITÉS
    # ---------------------------------------------------------
    resume = mouvements.aggregate(
        total_entrees=Sum(
            "quantite",
            filter=Q(type_mouvement="ENTREE"),
        ),
        total_sorties=Sum(
            "quantite",
            filter=Q(type_mouvement="SORTIE"),
        ),
        total_retours=Sum(
            "quantite",
            filter=Q(type_mouvement="RETOUR"),
        ),
    )

    total_entrees = resume["total_entrees"] or ZERO
    total_sorties = resume["total_sorties"] or ZERO
    total_retours = resume["total_retours"] or ZERO

    # ---------------------------------------------------------
    # 2. TOTAUX FINANCIERS
    # Chaque mouvement a son propre prix unitaire.
    # Entrée = prix d'achat ; sortie = prix de vente.
    # ---------------------------------------------------------
    expression_montant = ExpressionWrapper(
        F("quantite") * F("prix_unitaire"),
        output_field=DecimalField(
            max_digits=24,
            decimal_places=2,
        ),
    )

    montants = mouvements.aggregate(
        montant_achats=Sum(
            expression_montant,
            filter=Q(type_mouvement="ENTREE"),
        ),
        montant_ventes=Sum(
            expression_montant,
            filter=Q(type_mouvement="SORTIE"),
        ),
        montant_retours=Sum(
            expression_montant,
            filter=Q(type_mouvement="RETOUR"),
        ),
    )

    montant_achats = montants["montant_achats"] or ZERO
    montant_ventes = montants["montant_ventes"] or ZERO
    montant_retours = montants["montant_retours"] or ZERO

    # ---------------------------------------------------------
    # 3. MONTANTS CALCULÉS POUR L'AFFICHAGE
    # ---------------------------------------------------------
    derniers_mouvements = list(mouvements[:10])

    for mouvement in derniers_mouvements:
        quantite = mouvement.quantite or ZERO
        prix = mouvement.prix_unitaire or ZERO

        mouvement.montant_mouvement = quantite * prix

        if mouvement.type_mouvement == "ENTREE":
            mouvement.libelle_prix = "Prix d'achat"
        elif mouvement.type_mouvement == "SORTIE":
            mouvement.libelle_prix = "Prix de vente"
        else:
            mouvement.libelle_prix = "Prix du retour"

    # ---------------------------------------------------------
    # 4. CONTEXTE DU DASHBOARD
    # ---------------------------------------------------------
    contexte = {
        "nombre_materiaux": materiaux.count(),
        "nombre_materiaux_actifs": materiaux.filter(
            actif=True
        ).count(),
        "nombre_materiaux_inactifs": materiaux.filter(
            actif=False
        ).count(),

        "nombre_mouvements": mouvements.count(),

        "total_entrees": total_entrees,
        "total_sorties": total_sorties,
        "total_retours": total_retours,

        "montant_achats": montant_achats,
        "montant_ventes": montant_ventes,
        "montant_retours": montant_retours,

        "materiaux": materiaux,
        "derniers_mouvements": derniers_mouvements,
    }

    return render(
        request,
        "materiaux/mccr/dashboard.html",
        contexte,
    )

# ============================================================
# LISTE DES MATÉRIAUX
# ============================================================

@mccr_required
def materiaux_mccr_list(request):
    recherche = request.GET.get("q", "").strip()
    statut = request.GET.get("statut", "")

    materiaux = MateriauMCCR.objects.all().order_by("nom")

    if recherche:
        materiaux = materiaux.filter(
            Q(nom__icontains=recherche)
            | Q(unite__icontains=recherche)
        )

    if statut == "actif":
        materiaux = materiaux.filter(actif=True)
    elif statut == "inactif":
        materiaux = materiaux.filter(actif=False)

    return render(
        request,
        "materiaux/mccr/materiaux_list.html",
        {
            "materiaux": materiaux,
            "recherche": recherche,
            "statut": statut,
        },
    )


# ============================================================
# AJOUT D'UN MATÉRIAU
# ============================================================

@mccr_required
def materiau_mccr_create(request):
    if request.method == "POST":
        form = MateriauxMCCRForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    materiau = form.save(commit=False)
                    materiau.enregistreur = request.h_user
                    materiau.save()

                messages.success(
                    request,
                    "Matériau MCCR ajouté avec succès.",
                )
                return redirect("mccr_materiaux:materiaux_list")

            except (IntegrityError, ValidationError) as exc:
                messages.error(
                    request,
                    f"Impossible d'enregistrer le matériau : {exc}",
                )
    else:
        form = MateriauxMCCRForm()

    return render(
        request,
        "materiaux/mccr/materiau_form.html",
        {
            "form": form,
            "titre": "Ajouter un matériau MCCR",
            "bouton": "Enregistrer",
        },
    )


# ============================================================
# MODIFICATION D'UN MATÉRIAU
# ============================================================

@mccr_required
def materiau_mccr_update(request, pk):
    materiau = get_object_or_404(MateriauMCCR, pk=pk)

    refus = refuser_si_non_enregistreur(
        request,
        materiau,
        "mccr_materiaux:materiaux_list",
    )
    if refus:
        return refus

    if request.method == "POST":
        form = MateriauxMCCRForm(
            request.POST,
            instance=materiau,
        )

        if form.is_valid():
            try:
                with transaction.atomic():
                    objet = form.save(commit=False)
                    objet.enregistreur = materiau.enregistreur
                    objet.save()

                messages.success(
                    request,
                    "Matériau MCCR modifié avec succès.",
                )
                return redirect("mccr_materiaux:materiaux_list")

            except (IntegrityError, ValidationError) as exc:
                messages.error(
                    request,
                    f"Modification impossible : {exc}",
                )
    else:
        form = MateriauxMCCRForm(instance=materiau)

    return render(
        request,
        "materiaux/mccr/materiau_form.html",
        {
            "form": form,
            "materiau": materiau,
            "titre": "Modifier un matériau MCCR",
            "bouton": "Enregistrer les modifications",
        },
    )


# ============================================================
# SUPPRESSION D'UN MATÉRIAU
# ============================================================

@mccr_required
@require_POST
def materiau_mccr_delete(request, pk):
    materiau = get_object_or_404(MateriauMCCR, pk=pk)

    refus = refuser_si_non_enregistreur(
        request,
        materiau,
        "mccr_materiaux:materiaux_list",
    )
    if refus:
        return refus

    try:
        materiau.delete()
        messages.success(request, "Matériau supprimé avec succès.")

    except ProtectedError:
        messages.error(
            request,
            "Ce matériau possède des mouvements. "
            "Sa suppression est refusée pour préserver l'historique.",
        )

    return redirect("mccr_materiaux:materiaux_list")


# ============================================================
# LISTE DES MOUVEMENTS
# ============================================================

@mccr_required
def mouvements_mccr_list(request):
    recherche = request.GET.get("q", "").strip()
    type_mouvement = request.GET.get("type", "")

    mouvements = MouvementMateriauMCCR.objects.select_related(
        "materiau",
        "enregistreur",
    ).order_by("-date_mouvement", "-pk")

    if recherche:
        mouvements = mouvements.filter(
            Q(materiau__nom__icontains=recherche)
            | Q(motif__icontains=recherche)
            | Q(observation__icontains=recherche)
        )

    if type_mouvement in ("ENTREE", "SORTIE", "RETOUR"):
        mouvements = mouvements.filter(
            type_mouvement=type_mouvement
        )

    return render(
        request,
        "materiaux/mccr/mouvements_list.html",
        {
            "mouvements": mouvements,
            "recherche": recherche,
            "type_selectionne": type_mouvement,
        },
    )


# ============================================================
# AJOUT D'UN MOUVEMENT
# ============================================================

@mccr_required
def mouvement_mccr_create(request):
    if request.method == "POST":
        form = MouvementMateriauMCCRForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    mouvement = form.save(commit=False)
                    mouvement.enregistreur = request.h_user
                    mouvement.save()

                messages.success(
                    request,
                    "Mouvement de stock enregistré avec succès.",
                )
                return redirect("mccr_materiaux:mouvements_list")

            except (ValidationError, IntegrityError) as exc:
                messages.error(
                    request,
                    f"Mouvement refusé : {exc}",
                )
    else:
        form = MouvementMateriauMCCRForm()

    return render(
        request,
        "materiaux/mccr/mouvement_form.html",
        {
            "form": form,
            "titre": "Enregistrer un mouvement",
            "bouton": "Enregistrer le mouvement",
        },
    )


# ============================================================
# MODIFICATION D'UN MOUVEMENT
# ============================================================

@mccr_required
def mouvement_mccr_update(request, pk):
    mouvement = get_object_or_404(
        MouvementMateriauMCCR,
        pk=pk,
    )

    refus = refuser_si_non_enregistreur(
        request,
        mouvement,
        "mccr_materiaux:mouvements_list",
    )
    if refus:
        return refus

    if request.method == "POST":
        form = MouvementMateriauMCCRForm(
            request.POST,
            instance=mouvement,
        )

        if form.is_valid():
            try:
                with transaction.atomic():
                    objet = form.save(commit=False)
                    objet.enregistreur = mouvement.enregistreur
                    objet.save()

                messages.success(
                    request,
                    "Mouvement modifié avec succès.",
                )
                return redirect("mccr_materiaux:mouvements_list")

            except (ValidationError, IntegrityError) as exc:
                messages.error(
                    request,
                    f"Modification refusée : {exc}",
                )
    else:
        form = MouvementMateriauMCCRForm(instance=mouvement)

    return render(
        request,
        "materiaux/mccr/mouvement_form.html",
        {
            "form": form,
            "mouvement": mouvement,
            "titre": "Modifier un mouvement",
            "bouton": "Enregistrer les modifications",
        },
    )


# ============================================================
# SUPPRESSION D'UN MOUVEMENT
# ============================================================

@mccr_required
@require_POST
def mouvement_mccr_delete(request, pk):
    mouvement = get_object_or_404(
        MouvementMateriauMCCR,
        pk=pk,
    )

    refus = refuser_si_non_enregistreur(
        request,
        mouvement,
        "mccr_materiaux:mouvements_list",
    )
    if refus:
        return refus

    mouvement.delete()

    messages.success(
        request,
        "Mouvement supprimé. Le stock sera recalculé à partir "
        "des mouvements conservés.",
    )
    return redirect("mccr_materiaux:mouvements_list")



# ============================================================
# SUPPRESSION D'UN MATÉRIAU
# ============================================================

@mccr_required
def materiau_mccr_delete(request, pk):
    materiau = get_object_or_404(MateriauMCCR, pk=pk)

    refus = refuser_si_non_enregistreur(
        request,
        materiau,
        "mccr_materiaux:materiaux_list",
    )
    if refus:
        return refus

    if request.method == "POST":
        try:
            materiau.delete()
            messages.success(
                request,
                "Matériau supprimé avec succès.",
            )
        except ProtectedError:
            messages.error(
                request,
                "Ce matériau possède des mouvements. "
                "Sa suppression est refusée pour préserver l'historique.",
            )

        return redirect("mccr_materiaux:materiaux_list")

    return render(
        request,
        "materiaux/mccr/materiau_confirm_delete.html",
        {"materiau": materiau},
    )


# ============================================================
# SUPPRESSION D'UN MOUVEMENT
# ============================================================

@mccr_required
def mouvement_mccr_delete(request, pk):
    mouvement = get_object_or_404(
        MouvementMateriauMCCR,
        pk=pk,
    )

    refus = refuser_si_non_enregistreur(
        request,
        mouvement,
        "mccr_materiaux:mouvements_list",
    )
    if refus:
        return refus

    if request.method == "POST":
        mouvement.delete()
        messages.success(
            request,
            "Mouvement supprimé. Le stock sera recalculé "
            "à partir des mouvements conservés.",
        )
        return redirect("mccr_materiaux:mouvements_list")

    return render(
        request,
        "materiaux/mccr/mouvement_confirm_delete.html",
        {"mouvement": mouvement},
    )
