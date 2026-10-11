from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Q
from django.views.decorators.http import require_POST
from .models import Personnel, H_Personnel
from .forms import PersonnelForm, H_PersonnelForm
from audit.utils import enregistrer_action


from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages

from users.models import H_AppUser


def h_login_required(view_func):
    """Protège une vue réservée aux utilisateurs d'Entreprise H."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        h_user_id = request.session.get("h_user_id")
        h_role = request.session.get("h_role")

        if not h_user_id or not h_role:
            messages.warning(
                request,
                "Veuillez vous connecter à Entreprise H."
            )
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

            messages.error(
                request,
                "Votre session Entreprise H est invalide."
            )
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
            personnel.debutContrat.isoformat()
            if personnel.debutContrat
            else None
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
        "photo": (
            personnel.photo.name
            if personnel.photo
            else None
        ),
        "created_at": (
            personnel.created_at.isoformat()
            if personnel.created_at
            else None
        ),
    }


# =========================================================
# LISTE PERSONNEL
# =========================================================
def personnel_list(request):

    # -----------------------------------------------------
    # ROLE DE L'UTILISATEUR CONNECTE
    # -----------------------------------------------------
    role = request.session.get("role")

    # -----------------------------------------------------
    # REQUETE DE BASE
    # -----------------------------------------------------
    queryset = (
        Personnel.objects
        .select_related("categorie")
        .all()
        .order_by("nom", "prenom")
    )

    # =====================================================
    # FILTRAGE SELON LE ROLE
    # =====================================================

    if role == "UserMica":

        # UserMica voit uniquement les personnels Mica
        queryset = queryset.filter(
            typeTravail="Mica"
        )

    elif role == "UserEntreprise":

        # UserEntreprise voit uniquement Construction
        queryset = queryset.filter(
            typeTravail="Construction"
        )

    elif role in [
        "Admin",
        "SuperAdmin",
        "Superviseur",
    ]:

        # Ces rôles voient Mica + Construction
        pass

    else:

        # Aucun rôle valide
        queryset = Personnel.objects.none()

    # =====================================================
    # RECHERCHE GENERALE
    # =====================================================

    q = request.GET.get("q", "").strip()

    if q:

        queryset = queryset.filter(
            Q(nom__icontains=q)
            | Q(prenom__icontains=q)
            | Q(telephone__icontains=q)
            | Q(fonction__icontains=q)
            | Q(lieuTravail__icontains=q)
            | Q(typeTravail__icontains=q)
            | Q(typeContrat__icontains=q)
            | Q(categorie__nom__icontains=q)
        )

    # =====================================================
    # FILTRE TYPE DE TRAVAIL
    # =====================================================

    type_travail = request.GET.get(
        "typeTravail",
        ""
    ).strip()

    if role in [
        "Admin",
        "SuperAdmin",
        "Superviseur",
    ]:

        if type_travail in [
            "Mica",
            "Construction",
        ]:

            queryset = queryset.filter(
                typeTravail=type_travail
            )

    # =====================================================
    # FILTRE TYPE DE CONTRAT
    # =====================================================

    type_contrat = request.GET.get(
        "typeContrat",
        ""
    ).strip()

    if type_contrat in [
        "CDI",
        "CDD",
        "Journalier",
        "Stage",
    ]:

        queryset = queryset.filter(
            typeContrat=type_contrat
        )

    # =====================================================
    # PAGINATION
    # =====================================================

    paginator = Paginator(
        queryset,
        12
    )

    page_number = request.GET.get("page")

    page_obj = paginator.get_page(
        page_number
    )

    # =====================================================
    # PARAMETRES POUR LA PAGINATION
    # =====================================================

    query_params = request.GET.copy()

    query_params.pop(
        "page",
        None
    )

    # =====================================================
    # AFFICHAGE
    # =====================================================

    return render(
        request,
        "personnel/list.html",
        {
            "personnels": page_obj,
            "page_obj": page_obj,

            # Recherche générale
            "q": q,

            # Filtres
            "typeTravail": type_travail,
            "typeContrat": type_contrat,

            # Role
            "role": role,

            # Pagination
            "query_params": query_params.urlencode(),
        }
    )


# =========================================================
# AJOUT PERSONNEL
# =========================================================
def personnel_add(request):

    form = PersonnelForm(
        request.POST or None,
        request.FILES or None
    )

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
                    f"Ajout du personnel "
                    f"{personnel.nom} {personnel.prenom}".strip()
                )
            )

            messages.success(
                request,
                "Personnel ajouté avec succès."
            )

            return redirect(
                "personnel:personnel_list"
            )

    return render(
        request,
        "personnel/form.html",
        {
            "form": form,
            "action": "Ajouter",
        }
    )


# =========================================================
# DETAIL PERSONNEL
# =========================================================
def personnel_detail(request, id):

    personnel = get_object_or_404(
        Personnel.objects.select_related(
            "categorie"
        ),
        id=id
    )

    return render(
        request,
        "personnel/detail.html",
        {
            "personnel": personnel,
        }
    )


# =========================================================
# MODIFICATION PERSONNEL
# =========================================================
def personnel_edit(request, id):

    personnel = get_object_or_404(
        Personnel,
        id=id
    )

    ancienne = personnel_to_dict(
        personnel
    )

    form = PersonnelForm(
        request.POST or None,
        request.FILES or None,
        instance=personnel
    )

    if request.method == "POST":

        if form.is_valid():

            personnel = form.save()

            nouvelle = personnel_to_dict(
                personnel
            )

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
                )
            )

            messages.success(
                request,
                "Personnel modifié avec succès."
            )

            return redirect(
                "personnel:personnel_list"
            )

    return render(
        request,
        "personnel/form.html",
        {
            "form": form,
            "action": "Modifier",
            "personnel": personnel,
        }
    )


# =========================================================
# SUPPRESSION PERSONNEL
# =========================================================
def personnel_delete(request, id):

    personnel = get_object_or_404(
        Personnel,
        id=id
    )

    ancienne = personnel_to_dict(
        personnel
    )

    nom_personnel = (
        f"{personnel.nom} {personnel.prenom}"
    ).strip()

    if request.method == "POST":

        enregistrer_action(
            request,
            "DELETE",
            "Personnel",
            personnel.id,
            ancienne=ancienne,
            nouvelle=None,
            description=(
                f"Suppression du personnel "
                f"{nom_personnel}"
            )
        )

        personnel.delete()

        messages.success(
            request,
            f"Le personnel « {nom_personnel} » "
            "a été supprimé avec succès."
        )

        return redirect(
            "personnel:personnel_list"
        )

    return render(
        request,
        "personnel/confirm_delete.html",
        {
            "personnel": personnel,
        }
    )




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