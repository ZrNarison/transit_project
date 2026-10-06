from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Q

from .models import Personnel
from .forms import PersonnelForm
from audit.utils import enregistrer_action


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