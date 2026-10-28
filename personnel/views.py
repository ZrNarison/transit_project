from functools import wraps

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from audit.utils import enregistrer_action
from users.models import H_AppUser

from .forms import H_PersonnelForm, PersonnelForm
from .models import H_Personnel, Personnel
from users.decorators import session_login_required

def h_login_required(view_func):
    """Protège une vue réservée aux utilisateurs d'Entreprise H."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        h_user_id = request.session.get("h_user_id")
        h_role = request.session.get("h_role")

        if not h_user_id or not h_role:
            messages.warning(request, "Veuillez vous connecter à Entreprise H.")
            return redirect("users:login")

        utilisateur = H_AppUser.objects.filter(
            pk=h_user_id,
            role=h_role,
        ).first()

        if utilisateur is None:
            for key in (
                "h_user_id",
                "h_username",
                "h_role",
                "h_photo",
            ):
                request.session.pop(key, None)

            messages.error(request, "Votre session Entreprise H est invalide.")
            return redirect("users:login")

        return view_func(request, *args, **kwargs)

    return wrapper


# =========================================================
# OUTIL : convertir un personnel en dictionnaire pour AUDIT
# =========================================================
def personnel_to_dict(personnel):
    return {
        "id": personnel.id,
        "nom": personnel.nom,
        "prenom": personnel.prenom,
        "adresse": personnel.adresse,
        "telephone": personnel.telephone,
        "fonction": personnel.fonction,
        "typeTravail": getattr(personnel, "typeTravail", None),
        "typeContrat": getattr(personnel, "typeContrat", None),
        "lieuTravail": getattr(personnel, "lieuTravail", None),
        "psalaire": str(personnel.psalaire),
        "debutContrat": (
            personnel.debutContrat.isoformat() if personnel.debutContrat else None
        ),
        "finContrat": (
            personnel.finContrat.isoformat()
            if getattr(personnel, "finContrat", None)
            else None
        ),
        "categorie": (
            {
                "id": personnel.categorie.id,
                "nom": str(personnel.categorie),
            }
            if personnel.categorie
            else None
        ),
        "photo": (personnel.photo.name if personnel.photo else None),
        "created_at": (
            personnel.created_at.isoformat() if personnel.created_at else None
        ),
    }


# =========================================================
# LISTE DU PERSONNEL
# =========================================================
@session_login_required
def personnel_list(request):
    # =====================================================
    # 1. UTILISATEUR ET RÔLE CONNECTÉS
    # =====================================================
    role = request.session.get("role")
    user_id = request.session.get("user_id")

    # =====================================================
    # 2. BASE DE DONNÉES AUTORISÉE SELON LE RÔLE
    # =====================================================
    if role == "Admin":
        queryset = Personnel.objects.all()

    elif role in ("SuperviseurMica", "UserMica"):
        queryset = Personnel.objects.filter(
            typeTravail="Mica"
        )

    elif role in ("SuperviseurEntreprise", "UserEntreprise"):
        queryset = Personnel.objects.filter(
            typeTravail="Construction"
        )

    else:
        queryset = Personnel.objects.none()

    # =====================================================
    # 3. RECHERCHE
    # =====================================================
    q = request.GET.get("q", "").strip()

    if q:
        queryset = queryset.filter(
            Q(nom__icontains=q)
            | Q(prenom__icontains=q)
            | Q(telephone__icontains=q)
            | Q(fonction__icontains=q)
            | Q(lieuTravail__icontains=q)
        )

    # =====================================================
    # 4. FILTRE PAR TYPE DE TRAVAIL
    # =====================================================
    type_travail = ""

    if role == "Admin":
        type_travail = request.GET.get(
            "typeTravail", ""
        ).strip()

        if type_travail in ("Mica", "Construction"):
            queryset = queryset.filter(
                typeTravail=type_travail
            )
        else:
            type_travail = ""

    elif role in ("SuperviseurMica", "UserMica"):
        type_travail = "Mica"

    elif role in ("SuperviseurEntreprise", "UserEntreprise"):
        type_travail = "Construction"

    # =====================================================
    # 5. FILTRE PAR TYPE DE CONTRAT
    # =====================================================
    type_contrat = request.GET.get(
        "typeContrat", ""
    ).strip()

    contrats_valides = (
        "CDI",
        "CDD",
        "Journalier",
        "Stage",
    )

    if type_contrat in contrats_valides:
        queryset = queryset.filter(
            typeContrat=type_contrat
        )
    else:
        type_contrat = ""

    # =====================================================
    # 6. TRI ET TOTAL
    # =====================================================
    queryset = queryset.order_by("nom", "prenom")
    total_personnels = queryset.count()

    # =====================================================
    # 7. PAGINATION
    # =====================================================
    paginator = Paginator(queryset, 10)
    personnels = paginator.get_page(
        request.GET.get("page")
    )

    # Conserver les filtres lors de la pagination
    params = request.GET.copy()
    params.pop("page", None)
    query_params = params.urlencode()

    # =====================================================
    # 8. CONTEXTE
    # =====================================================
    context = {
        "personnels": personnels,
        "total_personnels": total_personnels,
        "q": q,
        "typeTravail": type_travail,
        "typeContrat": type_contrat,
        "query_params": query_params,

        # Valeurs utilisées dans le template
        "role": role,
        "user_id": user_id,
    }

    return render(
        request,
        "personnel/list.html",
        context,
    )


# =========================================================
# AJOUT PERSONNEL
# =========================================================
@session_login_required
def personnel_add(request):

    form = PersonnelForm(request.POST or None, request.FILES or None)

    if request.method == "POST":

        if form.is_valid():

            personnel = form.save()

            enregistrer_action(
                request,
                "CREATE",
                "Personnel",
                personnel.id,
                nouvelle=personnel_to_dict(personnel),
                description=(
                    f"Ajout du personnel " f"{personnel.nom} {personnel.prenom}".strip()
                ),
            )

            messages.success(request, "Personnel ajouté avec succès.")

            return redirect("personnel:personnel_list")

    return render(
        request,
        "personnel/form.html",
        {
            "form": form,
            "action": "Ajouter",
        },
    )


# =========================================================
# DETAIL PERSONNEL
# =========================================================
@session_login_required
def personnel_detail(request, id):

    personnel = get_object_or_404(Personnel.objects.select_related("categorie"), id=id)

    return render(
        request,
        "personnel/detail.html",
        {
            "personnel": personnel,
        },
    )


# =========================================================
# MODIFICATION PERSONNEL
# =========================================================
@session_login_required
def personnel_edit(request, id):

    personnel = get_object_or_404(Personnel, id=id)

    ancienne = personnel_to_dict(personnel)

    form = PersonnelForm(
        request.POST or None, request.FILES or None, instance=personnel
    )

    if request.method == "POST":

        if form.is_valid():

            personnel = form.save()

            nouvelle = personnel_to_dict(personnel)

            enregistrer_action(
                request,
                "UPDATE",
                "Personnel",
                personnel.id,
                ancienne=ancienne,
                nouvelle=nouvelle,
                description=(
                    f"Modification du personnel "
                    f"{personnel.nom} {personnel.prenom}".strip()
                ),
            )

            messages.success(request, "Personnel modifié avec succès.")

            return redirect("personnel:personnel_list")

    return render(
        request,
        "personnel/form.html",
        {
            "form": form,
            "action": "Modifier",
            "personnel": personnel,
        },
    )


# =========================================================
# SUPPRESSION PERSONNEL
# =========================================================
@session_login_required
def personnel_delete(request, id):
    # La suppression doit être envoyée par formulaire POST.
    if request.method != "POST":
        return redirect("personnel:personnel_list")

    # Vérifier le rôle connecté.
    role = request.session.get("role")

    if role != "Admin":
        messages.error(
            request,
            "Vous n'êtes pas autorisé à supprimer un personnel.",
        )
        return redirect("personnel:personnel_list")

    # Récupérer le personnel.
    personnel = get_object_or_404(Personnel, pk=id)

    # Préparer les informations avant suppression.
    ancienne = personnel_to_dict(personnel)
    nom_personnel = f"{personnel.nom} {personnel.prenom}".strip()

    # Enregistrer la trace d'audit.
    enregistrer_action(
        request,
        "DELETE",
        "Personnel",
        personnel.pk,
        ancienne=ancienne,
        nouvelle=None,
        description=f"Suppression du personnel {nom_personnel}",
    )

    # Supprimer le personnel.
    personnel.delete()

    messages.success(
        request,
        f"Le personnel « {nom_personnel} » a été supprimé avec succès.",
    )

    return redirect("personnel:personnel_list")

# ============================================================
# LISTE ET RECHERCHE DES PERSONNELS DE L'ENTREPRISE H
# ============================================================
@h_login_required
def h_personnel_list(request):
    queryset = H_Personnel.objects.all().order_by("nom", "prenom")

    recherche = request.GET.get("q", "").strip()

    if recherche:
        queryset = queryset.filter(
            Q(nom__icontains=recherche)
            | Q(prenom__icontains=recherche)
            | Q(cin__icontains=recherche)
            | Q(telephone__icontains=recherche)
            | Q(adresse__icontains=recherche)
        )

    paginator = Paginator(queryset, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)

    context = {
        "h_personnels": page_obj,
        "personnels": page_obj,
        "page_obj": page_obj,
        "recherche": recherche,
        "total_personnels": queryset.count(),
        "query_params": query_params.urlencode(),
    }

    return render(
        request,
        "personnel/h_list.html",
        context,
    )


# ============================================================
# DÉTAIL D'UN PERSONNEL DE L'ENTREPRISE H
# ============================================================
@h_login_required
def h_personnel_detail(request, pk):
    personnel = get_object_or_404(
        H_Personnel,
        pk=pk,
    )

    return render(
        request,
        "personnel/h_detail.html",
        {"personnel": personnel},
    )


# ============================================================
# AJOUT D'UN PERSONNEL DE L'ENTREPRISE H
# ============================================================
@h_login_required
def h_personnel_create(request):
    if request.method == "POST":
        form = H_PersonnelForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            personnel = form.save()

            messages.success(
                request,
                f"L'ancien personnel {personnel.nom} "
                f"{personnel.prenom} a été ajouté avec succès.",
            )

            return redirect("personnel:h_personnel_list")

        messages.error(
            request,
            "Veuillez corriger les erreurs du formulaire.",
        )
    else:
        form = H_PersonnelForm()

    return render(
        request,
        "personnel/h_form.html",
        {
            "form": form,
            "personnel": None,
            "titre": "Ajouter un ancien personnel",
            "action": "Ajouter",
        },
    )


# ============================================================
# MODIFICATION D'UN PERSONNEL DE L'ENTREPRISE H
# ============================================================
@h_login_required
def h_personnel_update(request, id):
    personnel = get_object_or_404(
        H_Personnel,
        pk=id,
    )

    if request.method == "POST":
        form = H_PersonnelForm(
            request.POST,
            request.FILES,
            instance=personnel,
        )

        if form.is_valid():
            personnel = form.save()

            messages.success(
                request,
                f"Les informations de {personnel.nom} "
                f"{personnel.prenom} ont été modifiées avec succès.",
            )

            return redirect("personnel:h_personnel_list")

        messages.error(
            request,
            "Veuillez corriger les erreurs du formulaire.",
        )

    else:
        form = H_PersonnelForm(instance=personnel)

    return render(
        request,
        "personnel/h_form.html",
        {
            "form": form,
            "personnel": personnel,
            "titre": "Modifier un ancien personnel",
            "action": "Enregistrer les modifications",
        },
    )


# ============================================================
# SUPPRESSION D'UN PERSONNEL DE L'ENTREPRISE H
# POST UNIQUEMENT
# ============================================================
@h_login_required
@require_POST
def h_personnel_delete(request, id):
    personnel = get_object_or_404(
        H_Personnel,
        pk=id,
    )

    nom_complet = f"{personnel.nom} {personnel.prenom}".strip()
    personnel.delete()

    messages.success(
        request,
        f"L'ancien personnel {nom_complet} a été supprimé avec succès.",
    )

    return redirect("personnel:h_personnel_list")
