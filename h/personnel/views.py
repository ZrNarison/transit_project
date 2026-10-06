from django.shortcuts import render, redirect, get_object_or_404
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models import Q

from .models import h_Personnel
from .forms import h_PersonnelForm
from audit.utils import enregistrer_action


# =========================================================
# OUTIL : convertir un personnel en dictionnaire pour AUDIT
# =========================================================
def h_personnel_to_dict(h_personnel):
    return {
        "id": h_personnel.id,
        "nom": h_personnel.nom,
        "prenom": h_personnel.prenom,
        "adresse": h_personnel.adresse,
        "telephone": h_personnel.telephone,
        "fonction": h_personnel.fonction,
        "typeTravail": getattr(h_personnel, "typeTravail", None),
        "typeContrat": getattr(h_personnel, "typeContrat", None),
        "lieuTravail": getattr(h_personnel, "lieuTravail", None),
        "psalaire": str(h_personnel.psalaire),
        "debutContrat": (
            h_personnel.debutContrat.isoformat()
            if h_personnel.debutContrat
            else None
        ),
        "finContrat": (
            h_personnel.finContrat.isoformat()
            if getattr(h_personnel, "finContrat", None)
            else None
        ),
        "categorie": (
            {
                "id": h_personnel.categorie.id,
                "nom": str(h_personnel.categorie),
            }
            if h_personnel.categorie
            else None
        ),
        "photo": (
            h_personnel.photo.name
            if h_personnel.photo
            else None
        ),
        "created_at": (
            h_personnel.created_at.isoformat()
            if h_personnel.created_at
            else None
        ),
    }


# =========================================================
# LISTE PERSONNEL
# =========================================================
def h_personnel_list(request):

    # -----------------------------------------------------
    # ROLE DE L'UTILISATEUR CONNECTE
    # -----------------------------------------------------
    role = request.session.get("role")

    # -----------------------------------------------------
    # REQUETE DE BASE
    # -----------------------------------------------------
    queryset = (
        h_Personnel.objects
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
        queryset = h_Personnel.objects.none()

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
        "h/personnel/list.html",
        {
            "h_personnels": page_obj,
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
def h_personnel_add(request):

    form = h_PersonnelForm(
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
                nouvelle=h_personnel_to_dict(personnel),
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
                "personnel:h_personnel_list"
            )

    return render(
        request,
        "h/personnel/form.html",
        {
            "form": form,
            "action": "Ajouter",
        }
    )


# =========================================================
# DETAIL PERSONNEL
# =========================================================
def h_personnel_detail(request, id):

    personnel = get_object_or_404(
        h_Personnel.objects.select_related(
            "categorie"
        ),
        id=id
    )

    return render(
        request,
        "h/personnel/detail.html",
        {
            "personnel": personnel,
        }
    )


# =========================================================
# MODIFICATION PERSONNEL
# =========================================================
def h_personnel_edit(request, id):

    personnel = get_object_or_404(
        h_Personnel,
        id=id
    )

    ancienne = h_personnel_to_dict(
        personnel
    )

    form = h_PersonnelForm(
        request.POST or None,
        request.FILES or None,
        instance=personnel
    )

    if request.method == "POST":

        if form.is_valid():

            personnel = form.save()

            nouvelle = h_personnel_to_dict(
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
                "personnel:h_personnel_list"
            )

    return render(
        request,
        "h/personnel/form.html",
        {
            "form": form,
            "action": "Modifier",
            "personnel": personnel,
        }
    )


# =========================================================
# SUPPRESSION PERSONNEL
# =========================================================
def h_personnel_delete(request, id):

    personnel = get_object_or_404(
        h_Personnel,
        id=id
    )

    ancienne = h_personnel_to_dict(
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
            "personnel:h_personnel_list"
        )

    return render(
        request,
        "h/personnel/confirm_delete.html",
        {
            "personnel": personnel,
        }
    )