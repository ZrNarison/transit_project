from decimal import Decimal

from django.contrib import messages
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from audit.utils import enregistrer_action
from users.models import AppUser, H_AppUser

from .forms import H_MaterielsForm, MaterielsForm
from .models import H_Materiels, Materiels

# ================================================================
# UTILITAIRES
# ================================================================


def valeur_audit(valeur):
    """
    Convertit les Decimal en chaînes pour éviter les problèmes
    lors de l'enregistrement dans le JSONField de l'audit.
    """
    if isinstance(valeur, Decimal):
        return str(valeur)

    return valeur


def materiel_audit_data(materiel):
    """
    Retourne les données importantes d'un matériel
    pour l'enregistrement dans l'audit.
    """
    return {
        "id": materiel.id,
        "nom": materiel.nom,
        "type": materiel.typeMat,
        "categorie": materiel.catMat,
        "stock_initial": valeur_audit(materiel.stock_initial),
        "photo": (materiel.photo.name if materiel.photo else None),
    }


def normaliser_valeur(valeur):
    """
    Normalise une valeur texte.

    Exemple :
        " ANGADY " -> "angady"
        "Angady"   -> "angady"
    """
    return (valeur or "").strip().lower()


def groupe_materiel_queryset(nom, typeMat, catMat):
    """
    Retourne tous les matériels appartenant exactement
    au même groupe :

        NOM + TYPE + CATEGORIE

    La comparaison est insensible à la casse.
    """
    return (
        Materiels.objects.filter(
            nom__iexact=(nom or "").strip(),
            typeMat__iexact=(typeMat or "").strip(),
            catMat__iexact=(catMat or "").strip(),
        )
        .prefetch_related(
            "sorties",
            "sorties__entrees",
        )
        .order_by("id")
    )


# ================================================================
# CALCUL STOCK D'UN MATERIEL
# ================================================================


def calcul_stock_materiel(materiel):
    """
    Calcule le stock d'un matériel individuel.

    Formule :

        Stock restant =
            Stock initial
            - Sorties
            + Entrées
    """

    stock_initial = materiel.stock_initial or Decimal("0")

    stock_sortie = materiel.sorties.aggregate(total=Sum("Nb_MatSort"))[
        "total"
    ] or Decimal("0")

    stock_entree = materiel.sorties.aggregate(total=Sum("entrees__Nb_Entre"))[
        "total"
    ] or Decimal("0")

    stock_restant = stock_initial - stock_sortie + stock_entree

    return {
        "stock_initial": stock_initial,
        "stock_sorti": stock_sortie,
        "stock_entre": stock_entree,
        "stock_restant": stock_restant,
    }


# ================================================================
# CALCUL STOCK D'UN GROUPE
# ================================================================


def calcul_stock_groupe(materiels):
    """
    Calcule le stock total d'un groupe de matériels.

    Exemple :

        ANGADY | Lahy | Chantier

    peut contenir :

        ID 1
        ID 5
        ID 8

    Les stocks des trois matériels sont additionnés.
    """

    stock_initial = Decimal("0")
    stock_sortie = Decimal("0")
    stock_entree = Decimal("0")

    for materiel in materiels:

        stock_initial += materiel.stock_initial or Decimal("0")

        stock_sortie += materiel.stock_sorti() or Decimal("0")

        stock_entree += materiel.stock_entre() or Decimal("0")

    stock_restant = stock_initial - stock_sortie + stock_entree

    return {
        "stock_initial": stock_initial,
        "stock_sorti": stock_sortie,
        "stock_entre": stock_entree,
        "stock_restant": stock_restant,
    }


# ================================================================
# VERIFICATION ROLE
# ================================================================


def role_autorise(request, roles):
    """
    Vérifie si l'utilisateur connecté possède
    l'un des rôles autorisés.

    Exemple :

        roles = ["Admin", "SuperAdmin"]

        role_autorise(request, roles)
    """

    role = request.session.get("role")

    if not roles:
        return False

    return role in roles


# ================================================================
# VISIBILITE SELON LE ROLE
# ================================================================


def materiel_visible_pour_role(request, queryset):
    """
    Applique les restrictions de visibilité.

    Admin
        -> voit tout

    SuperAdmin
        -> voit tout

    Superviseur
        -> voit tout

    UserEntreprise
        -> ne voit pas Mica

    UserMica
        -> voit uniquement Mica

    Autres
        -> ne voient pas Mica
    """

    role = request.session.get("role")

    if role in [
        "Admin",
        "SuperAdmin",
        "Superviseur",
    ]:
        return queryset

    if role == "UserEntreprise":
        return queryset.exclude(catMat__iexact="Mica")

    if role == "UserMica":
        return queryset.filter(catMat__iexact="Mica")

    return queryset.exclude(catMat__iexact="Mica")


# ================================================================
# LISTE DES MATERIELS
# ================================================================
def materiels_list(request):
    """
    Liste principale des matériels.

    Les matériels sont regroupés par :
        Nom + Type + Catégorie

    Les stocks sont additionnés sur tous les enregistrements
    appartenant au même groupe.

    Le bas du tableau affiche les totaux généraux.
    """

    queryset = (
        Materiels.objects.all()
        .prefetch_related(
            "sorties",
            "sorties__entrees",
        )
        .order_by(
            "nom",
            "typeMat",
            "catMat",
            "id",
        )
    )

    # ============================================================
    # FILTRES
    # ============================================================

    nom = request.GET.get("nom", "").strip()
    typeMat = request.GET.get("typeMat", "").strip()
    catMat = request.GET.get("catMat", "").strip()

    if nom:
        queryset = queryset.filter(nom__icontains=nom)

    if typeMat:
        queryset = queryset.filter(typeMat__icontains=typeMat)

    if catMat:
        queryset = queryset.filter(catMat__icontains=catMat)

    # ============================================================
    # RESTRICTION PAR ROLE
    # ============================================================

    queryset = materiel_visible_pour_role(request, queryset)

    # ============================================================
    # NOMBRE TOTAL D'ENREGISTREMENTS
    # ============================================================

    total_enregistrements = queryset.count()

    # ============================================================
    # REGROUPEMENT
    # ============================================================

    groupes = {}

    for materiel in queryset:

        cle = (
            normaliser_valeur(materiel.nom),
            normaliser_valeur(materiel.typeMat),
            normaliser_valeur(materiel.catMat),
        )

        if cle not in groupes:

            groupes[cle] = {
                "nom": (materiel.nom or "").strip(),
                "typeMat": (materiel.typeMat or "").strip(),
                "catMat": (materiel.catMat or "").strip(),
                "photo": (materiel.photo if materiel.photo else None),
                "stock_initial": Decimal("0"),
                "stock_sorti": Decimal("0"),
                "stock_entre": Decimal("0"),
                # Nombre de lignes réelles
                "nombre_enregistrements": 0,
            }

        # ========================================================
        # NOMBRE D'ENREGISTREMENTS DU GROUPE
        # ========================================================

        groupes[cle]["nombre_enregistrements"] += 1

        # ========================================================
        # STOCK INITIAL
        # ========================================================

        groupes[cle]["stock_initial"] += materiel.stock_initial or Decimal("0")

        # ========================================================
        # SORTIES
        # ========================================================

        groupes[cle]["stock_sorti"] += materiel.stock_sorti() or Decimal("0")

        # ========================================================
        # ENTREES
        # ========================================================

        groupes[cle]["stock_entre"] += materiel.stock_entre() or Decimal("0")

    # ============================================================
    # LISTE FINALE DES GROUPES
    # ============================================================

    materiels = []

    for cle, data in groupes.items():

        data["stock_restant"] = (
            data["stock_initial"] - data["stock_sorti"] + data["stock_entre"]
        )

        materiels.append(data)

    # ============================================================
    # TRI
    # ============================================================

    materiels.sort(
        key=lambda x: (
            normaliser_valeur(x["nom"]),
            normaliser_valeur(x["typeMat"]),
            normaliser_valeur(x["catMat"]),
        )
    )

    # ============================================================
    # TOTAUX GENERAUX
    # ============================================================

    total_groupes = len(materiels)

    total_stock_initial = sum((m["stock_initial"] for m in materiels), Decimal("0"))

    total_sorties = sum((m["stock_sorti"] for m in materiels), Decimal("0"))

    total_entrees = sum((m["stock_entre"] for m in materiels), Decimal("0"))

    total_stock_restant = sum((m["stock_restant"] for m in materiels), Decimal("0"))

    # ============================================================
    # AFFICHAGE
    # ============================================================

    return render(
        request,
        "materiels/list.html",
        {
            "materiels": materiels,
            # Filtres
            "nom": nom,
            "typeMat": typeMat,
            "catMat": catMat,
            # Role
            "role": request.session.get("role"),
            # Totaux
            "total_groupes": total_groupes,
            "total_enregistrements": total_enregistrements,
            "total_stock_initial": total_stock_initial,
            "total_sorties": total_sorties,
            "total_entrees": total_entrees,
            "total_stock_restant": total_stock_restant,
        },
    )


# ================================================================
# DETAIL D'UN GROUPE
# ================================================================


def materiels_mdetail(request, nom, typeMat, catMat):
    """
    Affiche le détail complet d'un groupe de matériels.

    Exemple :

        ANGADY | Lahy | Chantier

    affiche tous les enregistrements du groupe.
    """

    materiels = groupe_materiel_queryset(nom, typeMat, catMat)

    # ============================================================
    # RESTRICTION ROLE
    # ============================================================

    materiels = materiel_visible_pour_role(request, materiels)

    if not materiels.exists():

        messages.error(
            request, "Ce matériel n'existe pas ou vous n'avez pas accès à ce matériel."
        )

        return redirect("materiels:materiels_list")

    # ============================================================
    # LISTE DES MATERIELS
    # ============================================================

    materiels_list_data = list(materiels)

    # ============================================================
    # STOCK GLOBAL
    # ============================================================

    stocks = calcul_stock_groupe(materiels_list_data)

    # ============================================================
    # STOCK INDIVIDUEL
    # ============================================================

    lignes = []

    for materiel in materiels_list_data:

        stock = calcul_stock_materiel(materiel)

        lignes.append(
            {
                "materiel": materiel,
                "stock_initial": stock["stock_initial"],
                "stock_sorti": stock["stock_sorti"],
                "stock_entre": stock["stock_entre"],
                "stock_restant": stock["stock_restant"],
            }
        )

    # ============================================================
    # AFFICHAGE
    # ============================================================

    return render(
        request,
        "materiels/mdetail.html",
        {
            "nom": nom,
            "typeMat": typeMat,
            "catMat": catMat,
            "materiels": materiels_list_data,
            "lignes": lignes,
            "total_stock_initial": stocks["stock_initial"],
            "total_sorties": stocks["stock_sorti"],
            "total_entrees": stocks["stock_entre"],
            "stock_restant": stocks["stock_restant"],
            "role": request.session.get("role"),
        },
    )


# ================================================================
# DETAIL MATERIEL
# ================================================================


def materiels_detail(request, nom, typeMat, catMat):
    """
    Affiche le détail classique d'un groupe.

    Le premier matériel du groupe est utilisé
    comme objet principal.
    """

    materiels = groupe_materiel_queryset(nom, typeMat, catMat)

    # ============================================================
    # RESTRICTION ROLE
    # ============================================================

    materiels = materiel_visible_pour_role(request, materiels)

    if not materiels.exists():

        messages.error(request, "Matériel introuvable ou accès non autorisé.")

        return redirect("materiels:materiels_list")

    # ============================================================
    # LISTE
    # ============================================================

    materiels_list_data = list(materiels)

    # ============================================================
    # STOCK GLOBAL
    # ============================================================

    stocks = calcul_stock_groupe(materiels_list_data)

    # ============================================================
    # PREMIER MATERIEL
    # ============================================================

    materiel = materiels_list_data[0]

    # ============================================================
    # AFFICHAGE
    # ============================================================

    return render(
        request,
        "materiels/detail.html",
        {
            "materiel": materiel,
            "materiels": materiels_list_data,
            "nom": nom,
            "typeMat": typeMat,
            "catMat": catMat,
            "stock_initial": stocks["stock_initial"],
            "stock_sorti": stocks["stock_sorti"],
            "stock_entre": stocks["stock_entre"],
            "stock_restant": stocks["stock_restant"],
            "role": request.session.get("role"),
        },
    )


# ================================================================
# AJOUT MATERIEL
# ================================================================

# ================================================================
# AJOUT MATERIEL
# ================================================================

from django.contrib import messages
from django.shortcuts import redirect, render

from users.models import AppUser

# autres imports déjà présents...


def materiels_add(request):
    """
    Ajout d'un nouveau matériel.

    Règles :
        Admin
            -> catégorie libre

        SuperAdmin
            -> catégorie libre

        Superviseur
            -> catégorie libre

        UserEntreprise
            -> catégorie automatiquement = Chantier

        UserMica
            -> catégorie automatiquement = Mica

    L'utilisateur connecté devient automatiquement
    l'enregistreur du matériel.
    """

    # ============================================================
    # ROLES AUTORISES
    # ============================================================

    roles_autorises = [
        "Admin",
        "SuperAdmin",
        "Superviseur",
        "UserEntreprise",
        "UserMica",
    ]

    if not role_autorise(request, roles_autorises):
        messages.error(request, "Vous n'êtes pas autorisé à ajouter un matériel.")

        return redirect("materiels:materiels_list")

    # ============================================================
    # ROLE CONNECTE
    # ============================================================

    role = request.session.get("role")

    # ============================================================
    # UTILISATEUR CONNECTE
    # ============================================================

    user_id = request.session.get("user_id")

    if not user_id:
        messages.error(request, "Session utilisateur invalide.")

        return redirect("users:login")

    try:
        utilisateur = AppUser.objects.get(id=user_id)
    except AppUser.DoesNotExist:
        messages.error(request, "Utilisateur introuvable.")

        return redirect("users:login")

    # ============================================================
    # POST
    # ============================================================

    if request.method == "POST":

        form = MaterielsForm(request.POST, request.FILES, role=role)

        if form.is_valid():

            # Ne pas sauvegarder immédiatement
            materiel = form.save(commit=False)

            # ====================================================
            # CATEGORIE AUTOMATIQUE
            # ====================================================

            if role == "UserEntreprise":
                materiel.catMat = "Chantier"

            elif role == "UserMica":
                materiel.catMat = "Mica"

            # ====================================================
            # ENREGISTREUR
            # ====================================================

            # IMPORTANT :
            # L'utilisateur qui crée l'enregistrement
            # devient son enregistreur.

            materiel.enregistreur = utilisateur

            # ====================================================
            # SAUVEGARDE
            # ====================================================

            materiel.save()

            # ====================================================
            # AUDIT
            # ====================================================

            enregistrer_action(
                request,
                "CREATE",
                "Matériels",
                materiel.id,
                nouvelle=materiel_audit_data(materiel),
                description="Création d'un matériel",
            )

            # ====================================================
            # MESSAGE
            # ====================================================

            messages.success(request, "Matériel ajouté avec succès.")

            return redirect("materiels:materiels_list")

    # ============================================================
    # GET
    # ============================================================

    else:

        form = MaterielsForm(role=role)

        # ========================================================
        # VALEUR PAR DEFAUT
        # ========================================================

        if role == "UserEntreprise":

            form.fields["catMat"].initial = "Chantier"

        elif role == "UserMica":

            form.fields["catMat"].initial = "Mica"

    # ============================================================
    # AFFICHAGE
    # ============================================================

    return render(
        request,
        "materiels/form.html",
        {
            "form": form,
            "titre": "Nouveau matériel",
            "role": role,
        },
    )


# ================================================================
# MODIFICATION MATERIEL
# ================================================================


def materiels_edit(request, pk):
    """
    Modification d'un matériel.

    RÈGLE :
        Seul l'utilisateur qui a enregistré le matériel
        peut le modifier.
    """

    # ============================================================
    # UTILISATEUR CONNECTE
    # ============================================================

    user_id = request.session.get("user_id")

    if not user_id:
        messages.error(request, "Votre session a expiré. Veuillez vous reconnecter.")

        return redirect("users:login")

    # ============================================================
    # RECUPERATION UTILISATEUR
    # ============================================================

    try:
        utilisateur = AppUser.objects.get(id=user_id)

    except AppUser.DoesNotExist:

        messages.error(request, "Utilisateur introuvable.")

        return redirect("users:login")

    # ============================================================
    # RECUPERATION MATERIEL
    # ============================================================

    try:
        materiel = Materiels.objects.get(id=pk)

    except Materiels.DoesNotExist:

        messages.error(request, "Matériel introuvable.")

        return redirect("materiels:materiels_list")

    # ============================================================
    # VERIFICATION ENREGISTREUR
    # ============================================================

    if materiel.enregistreur_id != utilisateur.id:

        messages.error(
            request,
            "Vous n'êtes pas l'enregistreur de ce matériel. "
            "Seul l'enregistreur peut le modifier.",
        )

        return redirect("materiels:materiels_list")

    # ============================================================
    # MODIFICATION
    # ============================================================

    if request.method == "POST":

        ancienne_valeur = materiel_audit_data(materiel)

        form = MaterielsForm(
            request.POST, request.FILES, instance=materiel, role=utilisateur.role
        )

        if form.is_valid():

            materiel = form.save(commit=False)

            # ====================================================
            # CATEGORIE AUTOMATIQUE
            # ====================================================

            if utilisateur.role == "UserEntreprise":
                materiel.catMat = "Chantier"

            elif utilisateur.role == "UserMica":
                materiel.catMat = "Mica"

            # ====================================================
            # CONSERVATION DE L'ENREGISTREUR
            # ====================================================

            # IMPORTANT :
            # on ne change JAMAIS l'enregistreur lors
            # d'une modification.

            materiel.enregistreur = utilisateur

            # ====================================================
            # SAUVEGARDE
            # ====================================================

            materiel.save()

            # ====================================================
            # AUDIT
            # ====================================================

            enregistrer_action(
                request,
                "UPDATE",
                "Matériels",
                materiel.id,
                ancienne=ancienne_valeur,
                nouvelle=materiel_audit_data(materiel),
                description="Modification d'un matériel",
            )

            # ====================================================
            # MESSAGE
            # ====================================================

            messages.success(request, "Matériel modifié avec succès.")

            return redirect(
                "materiels:materiels_detail",
                materiel.nom,
                materiel.typeMat,
                materiel.catMat,
            )

    # ============================================================
    # GET
    # ============================================================

    else:

        form = MaterielsForm(instance=materiel, role=utilisateur.role)

    # ============================================================
    # AFFICHAGE
    # ============================================================

    return render(
        request,
        "materiels/form.html",
        {
            "form": form,
            "titre": "Modifier le matériel",
            "materiel": materiel,
            "role": utilisateur.role,
        },
    )


# ================================================================
# SUPPRESSION MATERIEL
# ================================================================


def materiels_delete(request, id):
    """
    Suppression définitive d'un matériel.

    Seuls :

        Admin
        SuperAdmin
        Superviseur

    peuvent supprimer un matériel.

    La suppression définitive se fait uniquement en POST.
    """

    # ============================================================
    # RECUPERATION
    # ============================================================

    materiel = get_object_or_404(Materiels, id=id)

    # ============================================================
    # AUTORISATION
    # ============================================================

    roles_autorises = [
        "Admin",
        "SuperAdmin",
        "Superviseur",
    ]

    if not role_autorise(request, roles_autorises):

        messages.error(request, "Vous n'êtes pas autorisé à supprimer ce matériel.")

        return redirect("materiels:materiels_list")

    # ============================================================
    # ANCIENNES VALEURS
    # ============================================================

    ancienne = materiel_audit_data(materiel)

    # ============================================================
    # POST UNIQUEMENT
    # ============================================================

    if request.method == "POST":

        nom = materiel.nom
        type_mat = materiel.typeMat
        cat_mat = materiel.catMat
        materiel_id = materiel.id

        # ========================================================
        # AUDIT AVANT SUPPRESSION
        # ========================================================

        enregistrer_action(
            request,
            "DELETE",
            "Matériels",
            materiel_id,
            ancienne=ancienne,
            description=(
                "Suppression d'un matériel : " f"{nom} | " f"{type_mat} | " f"{cat_mat}"
            ),
        )

        # ========================================================
        # SUPPRESSION
        # ========================================================

        materiel.delete()

        messages.success(request, "Matériel supprimé avec succès.")

        return redirect("materiels:materiels_list")

    # ============================================================
    # GET -> PAGE CONFIRMATION
    # ============================================================

    return render(request, "materiels/confirm_delete.html", {"materiel": materiel})


# ================================================================
# SUPPRIMER UNIQUEMENT LE STOCK INITIAL
# ================================================================


def supprimer_stock_initial(request, id):
    """
    Met uniquement le stock initial à zéro.

    IMPORTANT :

    Cette opération ne supprime :

        - ni les sorties
        - ni les entrées
        - ni le matériel

    Le stock restant devient automatiquement :

        0 - sorties + entrées
    """

    # ============================================================
    # RECUPERATION
    # ============================================================

    materiel = get_object_or_404(Materiels, id=id)

    # ============================================================
    # AUTORISATION
    # ============================================================

    roles_autorises = [
        "Admin",
        "SuperAdmin",
        "Superviseur",
    ]

    if not role_autorise(request, roles_autorises):

        messages.error(request, "Vous n'êtes pas autorisé à modifier le stock initial.")

        return redirect("materiels:materiels_list")

    # ============================================================
    # POST UNIQUEMENT
    # ============================================================

    if request.method != "POST":

        messages.error(request, "Action non autorisée.")

        return redirect("materiels:materiels_list")

    # ============================================================
    # ANCIEN STOCK
    # ============================================================

    ancien_stock = materiel.stock_initial or Decimal("0")

    # ============================================================
    # NOUVEAU STOCK
    # ============================================================

    materiel.stock_initial = Decimal("0")

    materiel.save(update_fields=["stock_initial"])

    # ============================================================
    # AUDIT
    # ============================================================

    enregistrer_action(
        request,
        "UPDATE",
        "Matériels",
        materiel.id,
        ancienne={"stock_initial": valeur_audit(ancien_stock)},
        nouvelle={"stock_initial": "0"},
        description=("Suppression du stock initial"),
    )

    # ============================================================
    # MESSAGE
    # ============================================================

    messages.success(request, "Le stock initial a été supprimé.")

    # ============================================================
    # RETOUR DETAIL GROUPE
    # ============================================================

    return redirect(
        "materiels:materiels_mdetail",
        nom=materiel.nom,
        typeMat=materiel.typeMat,
        catMat=materiel.catMat,
    )


# ============================================================
# ENTREPRISE H — GESTION DES MATÉRIELS
# ============================================================

# ============================================================
# AUTORISATION ENTREPRISE H
# ============================================================


def h_role_autorise(request, roles):
    """Vérifie le rôle de l'utilisateur connecté à Entreprise H."""
    return request.session.get("h_role") in roles


def h_materiel_audit_data(materiel):
    """Prépare les informations du matériel H pour l'audit."""
    return {
        "id": materiel.pk,
        "nom": getattr(materiel, "nom", ""),
        "typeMat": getattr(materiel, "typeMat", ""),
        "catMat": getattr(materiel, "catMat", ""),
        "stock_initial": getattr(materiel, "stock_initial", 0),
    }


# ============================================================
# LISTE DES MATÉRIELS H
# ============================================================


def h_materiels_list(request):
    if not h_role_autorise(request, ["Dir", "Compta"]):
        messages.error(
            request, "Vous n'avez pas accès aux matériels de l'Entreprise H."
        )
        return redirect("users:h_login")

    materiels = H_Materiels.objects.all().order_by("nom")

    return render(
        request,
        "materiels/list.html",
        {
            "materiels": materiels,
            "role": request.session.get("h_role"),
            "entreprise_h": True,
        },
    )


# ============================================================
# AJOUTER UN MATÉRIEL H
# ============================================================


def h_materiels_add(request):
    if not h_role_autorise(request, ["Dir", "Compta"]):
        messages.error(request, "Vous n'êtes pas autorisé à ajouter un matériel.")
        return redirect("materiels:h_materiels_list")

    utilisateur_id = request.session.get("h_user_id")

    utilisateur = get_object_or_404(
        H_AppUser,
        pk=utilisateur_id,
        role__in=["Dir", "Compta"],
    )

    if request.method == "POST":
        form = H_MaterielsForm(request.POST, request.FILES)

        if form.is_valid():
            materiel = form.save(commit=False)
            materiel.enregistreur = utilisateur
            materiel.save()
            form.save_m2m()

            enregistrer_action(
                request=request,
                action="CREATE",
                modele="H_Materiels",
                objet_id=materiel.pk,
                details=h_materiel_audit_data(materiel),
            )

            messages.success(request, "Matériel H ajouté avec succès.")
            return redirect("materiels:h_materiels_list")
    else:
        form = H_MaterielsForm()

    return render(
        request,
        "materiels/h_form.html",
        {
            "form": form,
            "titre": "Ajouter un matériel — Entreprise H",
            "action": "Ajouter",
            "entreprise_h": True,
        },
    )


# ============================================================
# MODIFIER UN MATÉRIEL H
# Seul l'enregistreur peut modifier
# ============================================================


def h_materiels_edit(request, pk):
    if not h_role_autorise(request, ["Dir", "Compta"]):
        messages.error(request, "Vous n'êtes pas autorisé à modifier ce matériel.")
        return redirect("materiels:h_materiels_list")

    materiel = get_object_or_404(H_Materiels, pk=pk)

    utilisateur_id = request.session.get("h_user_id")
    utilisateur = get_object_or_404(H_AppUser, pk=utilisateur_id)

    if materiel.enregistreur_id != utilisateur.pk:
        messages.error(
            request,
            "Seul l'utilisateur ayant enregistré ce matériel peut le modifier.",
        )
        return redirect("materiels:h_materiels_detail", pk=pk)

    if request.method == "POST":
        form = H_MaterielsForm(
            request.POST,
            request.FILES,
            instance=materiel,
        )

        if form.is_valid():
            materiel_modifie = form.save(commit=False)

            # Conserver l'enregistreur d'origine.
            materiel_modifie.enregistreur_id = materiel.enregistreur_id
            materiel_modifie.save()
            form.save_m2m()

            enregistrer_action(
                request=request,
                action="UPDATE",
                modele="H_Materiels",
                objet_id=materiel_modifie.pk,
                details=h_materiel_audit_data(materiel_modifie),
            )

            messages.success(request, "Matériel H modifié avec succès.")
            return redirect(
                "materiels:h_materiels_detail",
                pk=materiel_modifie.pk,
            )
    else:
        form = H_MaterielsForm(instance=materiel)

    return render(
        request,
        "materiels/h_form.html",
        {
            "form": form,
            "materiel": materiel,
            "titre": "Modifier un matériel — Entreprise H",
            "action": "Modifier",
            "entreprise_h": True,
        },
    )


# ============================================================
# SUPPRIMER UN MATÉRIEL H
# ============================================================


def h_materiels_delete(request, pk):
    if not h_role_autorise(request, ["Dir", "Compta"]):
        messages.error(request, "Vous n'êtes pas autorisé à supprimer ce matériel.")
        return redirect("materiels:h_materiels_list")

    materiel = get_object_or_404(H_Materiels, pk=pk)

    if request.method == "POST":
        details = h_materiel_audit_data(materiel)
        objet_id = materiel.pk

        try:
            materiel.delete()

            enregistrer_action(
                request=request,
                action="DELETE",
                modele="H_Materiels",
                objet_id=objet_id,
                details=details,
            )

            messages.success(request, "Matériel H supprimé avec succès.")
            return redirect("materiels:h_materiels_list")

        except Exception as exc:
            messages.error(
                request,
                f"Impossible de supprimer ce matériel : {exc}",
            )
            return redirect(
                "materiels:h_materiels_detail",
                pk=materiel.pk,
            )

    return render(
        request,
        "materiels/h_confirm_delete.html",
        {
            "materiel": materiel,
            "entreprise_h": True,
        },
    )


# ================================================================
# ENTREPRISE H — GROUPE DE MATÉRIELS
# ================================================================


def h_groupe_materiel_queryset(nom, typeMat, catMat):
    """Récupère les matériels H appartenant au même groupe."""
    return (
        H_Materiels.objects.filter(
            nom__iexact=(nom or "").strip(),
            typeMat__iexact=(typeMat or "").strip(),
            catMat__iexact=(catMat or "").strip(),
        )
        .prefetch_related("sorties", "sorties__entrees")
        .order_by("id")
    )


def h_calcul_stock_materiel(materiel):
    """Calcule le stock restant d'un matériel H."""
    stock_initial = materiel.stock_initial or Decimal("0")

    stock_sorti = materiel.sorties.aggregate(total=Sum("Nb_MatSort"))[
        "total"
    ] or Decimal("0")

    stock_entre = materiel.sorties.aggregate(total=Sum("entrees__Nb_Entre"))[
        "total"
    ] or Decimal("0")

    return {
        "stock_initial": stock_initial,
        "stock_sorti": stock_sorti,
        "stock_entre": stock_entre,
        "stock_restant": stock_initial - stock_sorti + stock_entre,
    }


def h_calcul_stock_groupe(materiels):
    """Additionne les stocks des matériels H d'un même groupe."""
    total_initial = Decimal("0")
    total_sorti = Decimal("0")
    total_entre = Decimal("0")

    for materiel in materiels:
        stock = h_calcul_stock_materiel(materiel)
        total_initial += stock["stock_initial"]
        total_sorti += stock["stock_sorti"]
        total_entre += stock["stock_entre"]

    return {
        "stock_initial": total_initial,
        "stock_sorti": total_sorti,
        "stock_entre": total_entre,
        "stock_restant": total_initial - total_sorti + total_entre,
    }


# ================================================================
# ENTREPRISE H — DÉTAIL D'UN GROUPE
# ================================================================


def h_materiels_mdetail(request, nom, typeMat, catMat):
    if not h_role_autorise(request, ["Dir", "Compta"]):
        messages.error(request, "Accès refusé aux matériels de l'Entreprise H.")
        return redirect("materiels:h_materiels_list")

    queryset = h_groupe_materiel_queryset(nom, typeMat, catMat)
    liste = list(queryset)

    if not liste:
        messages.error(request, "Aucun matériel H trouvé pour ce groupe.")
        return redirect("materiels:h_materiels_list")

    stocks = h_calcul_stock_groupe(liste)
    lignes = []

    for materiel in liste:
        stock = h_calcul_stock_materiel(materiel)
        lignes.append(
            {
                "materiel": materiel,
                **stock,
            }
        )

    return render(
        request,
        "materiels/h_mdetail.html",
        {
            "nom": nom,
            "typeMat": typeMat,
            "catMat": catMat,
            "materiels": liste,
            "lignes": lignes,
            "total_stock_initial": stocks["stock_initial"],
            "total_sorties": stocks["stock_sorti"],
            "total_entrees": stocks["stock_entre"],
            "stock_restant": stocks["stock_restant"],
            "role": request.session.get("h_role"),
            "entreprise_h": True,
        },
    )


# ================================================================
# ENTREPRISE H — DÉTAIL CLASSIQUE
# ================================================================


def h_materiels_detail(request, nom, typeMat, catMat):
    if not h_role_autorise(request, ["Dir", "Compta"]):
        messages.error(request, "Accès refusé aux matériels de l'Entreprise H.")
        return redirect("materiels:h_materiels_list")

    liste = list(h_groupe_materiel_queryset(nom, typeMat, catMat))

    if not liste:
        messages.error(request, "Matériel H introuvable.")
        return redirect("materiels:h_materiels_list")

    stocks = h_calcul_stock_groupe(liste)

    return render(
        request,
        "materiels/h_detail.html",
        {
            "materiel": liste[0],
            "materiels": liste,
            "nom": nom,
            "typeMat": typeMat,
            "catMat": catMat,
            "stock_initial": stocks["stock_initial"],
            "stock_sorti": stocks["stock_sorti"],
            "stock_entre": stocks["stock_entre"],
            "stock_restant": stocks["stock_restant"],
            "role": request.session.get("h_role"),
            "entreprise_h": True,
        },
    )


# ================================================================
# ENTREPRISE H — SUPPRIMER LE STOCK INITIAL D'UN GROUPE
# ================================================================


def h_supprimer_stock_initial(request, nom, typeMat, catMat):
    if not h_role_autorise(request, ["Dir", "Compta"]):
        messages.error(request, "Vous n'êtes pas autorisé à modifier le stock initial.")
        return redirect("materiels:h_materiels_list")

    if request.method != "POST":
        messages.error(request, "Action non autorisée.")
        return redirect("materiels:h_materiels_list")

    liste = list(h_groupe_materiel_queryset(nom, typeMat, catMat))

    if not liste:
        messages.error(request, "Aucun matériel H trouvé pour ce groupe.")
        return redirect("materiels:h_materiels_list")

    for materiel in liste:
        ancien_stock = materiel.stock_initial or Decimal("0")

        if ancien_stock == 0:
            continue

        materiel.stock_initial = Decimal("0")
        materiel.save(update_fields=["stock_initial"])

        enregistrer_action(
            request,
            "UPDATE",
            "H_Materiels",
            materiel.pk,
            ancienne={"stock_initial": str(ancien_stock)},
            nouvelle={"stock_initial": "0"},
            description="Suppression du stock initial du groupe Entreprise H",
        )

    messages.success(request, "Le stock initial du groupe H a été remis à zéro.")

    return redirect(
        "materiels:h_materiels_mdetail",
        nom=nom,
        typeMat=typeMat,
        catMat=catMat,
    )
