from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.db.models import Sum
from django.shortcuts import (
    get_object_or_404,
    redirect,
    render,
)

from users.models import AppUser

from .forms import (
    ActiviteTransportForm,
    CategorieDepenseForm,
    DepenseForm,
    DepenseGasoilForm,
    MateriauxDivisionForm,
    MateriauxEntreeForm,
    MateriauxForm,
    MateriauxOutForm,
    PaiementDockerForm,
    ReparationVehiculeForm,
    VehiculeForm,
)

from .models import (
    ActiviteTransport,
    CategorieDepense,
    Depense,
    DepenseGasoil,
    Materiaux,
    MateriauxDivision,
    MateriauxEntree,
    MateriauxOut,
    PaiementDocker,
    ReparationVehicule,
    Vehicule,
)


# ============================================================
# UTILITAIRES
# ============================================================

def get_current_user(request):
    """
    Récupère l'utilisateur connecté à partir de la session.
    """

    user_id = request.session.get("user_id")

    if not user_id:
        return None

    return AppUser.objects.filter(
        id=user_id
    ).first()


def require_user(request):
    return get_current_user(request)


def check_user(request):
    user = get_current_user(request)

    if not user:
        return redirect("users:login")

    return user


def add_validation_errors(form, error):
    """
    Ajoute proprement les ValidationError du modèle
    dans le formulaire Django.
    """

    if hasattr(error, "message_dict"):
        for field, errors in error.message_dict.items():

            if field in form.fields:
                for message in errors:
                    form.add_error(field, message)
            else:
                for message in errors:
                    form.add_error(None, message)

    else:
        form.add_error(None, str(error))


# ============================================================
# DASHBOARD
# ============================================================

def dashboard(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    # ========================================================
    # MATÉRIAUX
    # ========================================================

    total_materiaux = Materiaux.objects.count()

    total_entrees = (
        MateriauxEntree.objects.aggregate(
            total=Sum("entree")
        )["total"]
        or Decimal("0")
    )

    total_divisions = (
        MateriauxDivision.objects.aggregate(
            total=Sum("quantite")
        )["total"]
        or Decimal("0")
    )

    total_sorties = (
        MateriauxOut.objects.aggregate(
            total=Sum("quantite")
        )["total"]
        or Decimal("0")
    )

    stock_entrepot = total_entrees - total_divisions
    stock_magasin = total_divisions - total_sorties
    stock_total = stock_entrepot + stock_magasin

    # ========================================================
    # STATISTIQUES PAR MATÉRIAU
    # ========================================================

    materiaux_stats = []

    for materiau in Materiaux.objects.all():

        entrees = materiau.total_entrees
        divisions = materiau.total_divisions
        sorties = materiau.total_sorties

        stock_entrepot_materiau = (
            entrees - divisions
        )

        stock_magasin_materiau = (
            divisions - sorties
        )

        stock_total_materiau = (
            stock_entrepot_materiau
            + stock_magasin_materiau
        )

        materiaux_stats.append({
            "materiau": materiau,
            "entrees": entrees,
            "divisions": divisions,
            "sorties": sorties,
            "stock_entrepot": stock_entrepot_materiau,
            "stock_magasin": stock_magasin_materiau,
            "stock_total": stock_total_materiau,
        })

    # ========================================================
    # VÉHICULES
    # ========================================================

    total_vehicules = Vehicule.objects.count()

    vehicules_actifs = Vehicule.objects.filter(
        actif=True
    ).count()

    vehicules_inactifs = Vehicule.objects.filter(
        actif=False
    ).count()

    # ========================================================
    # ACTIVITÉS DE TRANSPORT
    # ========================================================

    total_activites_transport = (
        ActiviteTransport.objects.count()
    )

    activites_materiaux = (
        ActiviteTransport.objects.filter(
            type_transport=ActiviteTransport.MATERIAUX
        ).count()
    )

    activites_materiels = (
        ActiviteTransport.objects.filter(
            type_transport=ActiviteTransport.MATERIELS
        ).count()
    )

    activites_personnel = (
        ActiviteTransport.objects.filter(
            type_transport=ActiviteTransport.PERSONNEL
        ).count()
    )

    # ========================================================
    # DOCKERS
    # ========================================================

    nombre_paiements_dockers = (
        PaiementDocker.objects.count()
    )

    total_paiements_dockers = (
        PaiementDocker.objects.aggregate(
            total=Sum("montant")
        )["total"]
        or Decimal("0")
    )

    # ========================================================
    # GASOIL
    # ========================================================

    total_litres_gasoil = (
        DepenseGasoil.objects.aggregate(
            total=Sum("quantite_litre")
        )["total"]
        or Decimal("0")
    )

    total_gasoil = (
        DepenseGasoil.objects.aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0")
    )

    # ========================================================
    # DÉPENSES GÉNÉRALES
    # ========================================================

    total_depenses_generales = (
        Depense.objects.aggregate(
            total=Sum("montant")
        )["total"]
        or Decimal("0")
    )

    nombre_depenses = Depense.objects.count()

    # ========================================================
    # RÉPARATIONS
    # ========================================================

    reparations = ReparationVehicule.objects.all()

    nombre_reparations = reparations.count()

    total_pieces = sum(
        (
            reparation.montant_piece
            for reparation in reparations
        ),
        Decimal("0"),
    )

    total_main_oeuvre = sum(
        (
            reparation.montant_main_oeuvre
            for reparation in reparations
        ),
        Decimal("0"),
    )

    total_reparations = (
        total_pieces
        + total_main_oeuvre
    )

    # ========================================================
    # COÛT GLOBAL D'EXPLOITATION
    # ========================================================

    cout_exploitation = (
        total_gasoil
        + total_paiements_dockers
        + total_depenses_generales
        + total_reparations
    )

    # ========================================================
    # RECETTES TRANSPORT
    # ========================================================
    #
    # Le modèle ActiviteTransport actuel ne contient pas
    # de champ montant/recette.
    #
    # On ne crée donc pas de faux chiffre.
    #

    total_transport = Decimal("0")
    resultat_transport = (
        total_transport
        - cout_exploitation
    )

    # ========================================================
    # TOTAL GÉNÉRAL DES DÉPENSES
    # ========================================================

    total_general = cout_exploitation

    # ========================================================
    # CONTEXT
    # ========================================================

    context = {
        "user": user,

        # -------------------------
        # MATÉRIAUX
        # -------------------------

        "total_materiaux": total_materiaux,

        "total_entrees": total_entrees,
        "total_divisions": total_divisions,
        "total_divise": total_divisions,
        "total_sorties": total_sorties,

        "stock_entrepot": stock_entrepot,
        "stock_magasin": stock_magasin,
        "stock_total": stock_total,

        "materiaux_stats": materiaux_stats,

        # -------------------------
        # VÉHICULES
        # -------------------------

        "total_vehicules": total_vehicules,
        "vehicules_actifs": vehicules_actifs,
        "vehicules_inactifs": vehicules_inactifs,

        # -------------------------
        # TRANSPORT
        # -------------------------

        "total_activites_transport":
            total_activites_transport,

        "nombre_activites":
            total_activites_transport,

        "activites_materiaux":
            activites_materiaux,

        "activites_materiels":
            activites_materiels,

        "activites_personnel":
            activites_personnel,

        # -------------------------
        # DOCKERS
        # -------------------------

        "total_dockers":
            nombre_paiements_dockers,

        "nombre_paiements_dockers":
            nombre_paiements_dockers,

        "total_paiements_dockers":
            total_paiements_dockers,

        # -------------------------
        # GASOIL
        # -------------------------

        "total_gasoil":
            total_gasoil,

        "total_litres_gasoil":
            total_litres_gasoil,

        # -------------------------
        # DÉPENSES
        # -------------------------

        "total_depenses":
            total_depenses_generales,

        "total_depenses_generales":
            total_depenses_generales,

        "nombre_depenses":
            nombre_depenses,

        # -------------------------
        # RÉPARATIONS
        # -------------------------

        "total_reparations":
            total_reparations,

        "nombre_reparations":
            nombre_reparations,

        "total_pieces":
            total_pieces,

        "total_main_oeuvre":
            total_main_oeuvre,

        # -------------------------
        # FINANCES
        # -------------------------

        "total_transport":
            total_transport,

        "cout_exploitation":
            cout_exploitation,

        "resultat_transport":
            resultat_transport,

        "total_general":
            total_general,
    }

    return render(
        request,
        "materiaux/dashboard.html",
        context,
    )


# ============================================================
# MATÉRIAUX CRUD
# ============================================================
def materiaux_list(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    # ========================================================
    # FILTRE PAR NOM DU MATÉRIAU
    # ========================================================

    recherche = request.GET.get("q", "").strip()

    materiaux = Materiaux.objects.all()

    if recherche:
        materiaux = materiaux.filter(
            libelle__icontains=recherche
        )

    materiaux = materiaux.order_by("libelle")

    return render(
        request,
        "materiaux/materiaux_list.html",
        {
            "user": user,
            "materiaux": materiaux,
            "recherche": recherche,
        },
    )

def materiau_add(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    if request.method == "POST":

        form = MateriauxForm(request.POST)

        if form.is_valid():

            try:
                materiau = form.save()
                messages.success(
                    request,
                    "Matériau ajouté avec succès.",
                )

                return redirect(
                    "materiaux:materiaux_list"
                )

            except ValidationError as error:
                add_validation_errors(form, error)

    else:
        form = MateriauxForm()

    return render(
        request,
        "materiaux/materiaux_form.html",
        {
            "user": user,
            "form": form,
            "title": "Ajouter un matériau",
        },
    )


# Alias conservé
materiaux_add = materiau_add


def materiau_edit(request, pk):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    materiau = get_object_or_404(
        Materiaux,
        pk=pk,
    )

    if request.method == "POST":

        form = MateriauxForm(
            request.POST,
            instance=materiau,
        )

        if form.is_valid():

            try:
                form.save()

                messages.success(
                    request,
                    "Matériau modifié avec succès.",
                )

                return redirect(
                    "materiaux:materiaux_list"
                )

            except ValidationError as error:
                add_validation_errors(form, error)

    else:
        form = MateriauxForm(
            instance=materiau
        )

    return render(
        request,
        "materiaux/materiaux_form.html",
        {
            "user": user,
            "form": form,
            "materiau": materiau,
            "title": "Modifier le matériau",
        },
    )


# Alias conservé
materiaux_edit = materiau_edit


def materiau_delete(request, pk):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    materiau = get_object_or_404(
        Materiaux,
        pk=pk,
    )

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
                (
                    "Impossible de supprimer ce matériau "
                    "car il est déjà utilisé."
                ),
            )

    return redirect(
        "materiaux:materiaux_list"
    )


# Alias conservé
materiaux_delete = materiau_delete


# ============================================================
# ENTRÉES ENTREPÔT
# ============================================================
def entrees_list(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    recherche = request.GET.get("nom_materiau", "").strip()

    objets = (
        MateriauxEntree.objects
        .select_related("materiau", "enregistreur")
        .prefetch_related("divisions")
        .all()
    )

    if recherche:
        objets = objets.filter(
            materiau__libelle__icontains=recherche
        )

    objets = objets.order_by("-date_entree", "-id")

    return render(
        request,
        "materiaux/entrees_list.html",
        {
            "user": user,
            "objets": objets,
            "recherche": recherche,
        },
    )


def entree_add(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    if request.method == "POST":

        form = MateriauxEntreeForm(
            request.POST
        )

        if form.is_valid():

            entree = form.save(
                commit=False
            )

            entree.enregistreur = user

            try:
                entree.save()

                messages.success(
                    request,
                    "Entrée enregistrée avec succès.",
                )

                return redirect(
                    "materiaux:entrees_list"
                )

            except ValidationError as error:
                add_validation_errors(
                    form,
                    error,
                )

    else:
        form = MateriauxEntreeForm()

    return render(
        request,
        "materiaux/entree_form.html",
        {
            "user": user,
            "form": form,
            "title": "Nouvelle entrée entrepôt",
        },
    )


def entree_edit(request, pk):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    entree = get_object_or_404(
        MateriauxEntree,
        pk=pk,
    )

    # ========================================================
    # SÉCURITÉ :
    # SEUL L'ENREGISTREUR PEUT MODIFIER
    # ========================================================

    if entree.enregistreur_id != user.id:

        messages.error(
            request,
            "Vous n'êtes pas autorisé à modifier cette entrée. "
            "Seul l'utilisateur qui l'a enregistrée peut la modifier."
        )

        return redirect("materiaux:entrees_list")

    if request.method == "POST":

        form = MateriauxEntreeForm(
            request.POST,
            instance=entree,
        )

        if form.is_valid():

            try:

                objet = form.save(commit=False)

                # ====================================================
                # CONSERVATION DE L'ENREGISTREUR ORIGINAL
                # ====================================================

                objet.enregistreur_id = entree.enregistreur_id

                objet.save()

                messages.success(
                    request,
                    "L'entrée a été modifiée avec succès."
                )

                return redirect(
                    "materiaux:entrees_list"
                )

            except ValidationError as error:

                add_validation_errors(
                    form,
                    error,
                )

    else:

        form = MateriauxEntreeForm(
            instance=entree,
        )

    return render(
        request,
        "materiaux/entree_form.html",
        {
            "user": user,
            "form": form,
            "objet": entree,
            "entree": entree,
            "mode": "edit",
        },
    )

def entree_delete(request, pk):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    entree = get_object_or_404(
        MateriauxEntree,
        pk=pk,
    )

    # ========================================================
    # SÉCURITÉ :
    # SEUL L'ENREGISTREUR PEUT SUPPRIMER
    # ========================================================

    if entree.enregistreur_id != user.id:

        messages.error(
            request,
            "Vous n'êtes pas autorisé à supprimer cette entrée. "
            "Seul l'utilisateur qui l'a enregistrée peut la supprimer."
        )

        return redirect("materiaux:entrees_list")

    if request.method != "POST":

        return redirect(
            "materiaux:entrees_list"
        )

    # ========================================================
    # UNE ENTRÉE AYANT DES DIVISIONS NE PEUT PAS ÊTRE SUPPRIMÉE
    # ========================================================

    if entree.divisions.exists():

        messages.error(
            request,
            "Impossible de supprimer cette entrée car elle possède "
            "déjà une ou plusieurs divisions."
        )

        return redirect(
            "materiaux:entrees_list"
        )

    try:

        entree.delete()

        messages.success(
            request,
            "L'entrée a été supprimée avec succès."
        )

    except ProtectedError:

        messages.error(
            request,
            "Impossible de supprimer cette entrée car elle est utilisée "
            "dans d'autres enregistrements."
        )

    return redirect(
        "materiaux:entrees_list"
    )


# ============================================================
# DIVISIONS
# ============================================================

def divisions_list(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    divisions = (
        MateriauxDivision.objects
        .select_related(
            "entree",
            "entree__materiau",
            "enregistreur",
        )
        .prefetch_related("sorties")
        .all()
    )

    return render(
        request,
        "materiaux/divisions_list.html",
        {
            "user": user,
            "divisions": divisions,
        },
    )


def division_add(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    if request.method == "POST":

        form = MateriauxDivisionForm(
            request.POST
        )

        if form.is_valid():

            division = form.save(
                commit=False
            )

            division.enregistreur = user

            try:
                division.save()

                messages.success(
                    request,
                    "Division enregistrée avec succès.",
                )

                return redirect(
                    "materiaux:divisions_list"
                )

            except ValidationError as error:
                add_validation_errors(
                    form,
                    error,
                )

    else:
        form = MateriauxDivisionForm()

    return render(
        request,
        "materiaux/division_form.html",
        {
            "user": user,
            "form": form,
            "title": "Nouvelle division",
        },
    )


def division_edit(request, pk):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    division = get_object_or_404(
        MateriauxDivision,
        pk=pk,
    )

    if request.method == "POST":

        form = MateriauxDivisionForm(
            request.POST,
            instance=division,
        )

        if form.is_valid():

            objet = form.save(
                commit=False
            )

            objet.enregistreur_id = (
                division.enregistreur_id
            )

            try:
                objet.save()

                messages.success(
                    request,
                    "Division modifiée avec succès.",
                )

                return redirect(
                    "materiaux:divisions_list"
                )

            except ValidationError as error:
                add_validation_errors(
                    form,
                    error,
                )

    else:
        form = MateriauxDivisionForm(
            instance=division
        )

    return render(
        request,
        "materiaux/division_form.html",
        {
            "user": user,
            "form": form,
            "division": division,
            "title": "Modifier la division",
        },
    )


def division_delete(request, pk):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    division = get_object_or_404(
        MateriauxDivision,
        pk=pk,
    )

    if request.method == "POST":

        if division.sorties.exists():

            messages.error(
                request,
                (
                    "Impossible de supprimer cette division "
                    "car elle possède déjà des sorties."
                ),
            )

        else:

            try:
                division.delete()

                messages.success(
                    request,
                    "Division supprimée avec succès.",
                )

            except ProtectedError:
                messages.error(
                    request,
                    (
                        "Impossible de supprimer cette division "
                        "car elle est utilisée."
                    ),
                )

    return redirect(
        "materiaux:divisions_list"
    )


# ============================================================
# SORTIES
# ============================================================

def sorties_list(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    sorties = (
        MateriauxOut.objects
        .select_related(
            "division",
            "division__entree",
            "division__entree__materiau",
            "enregistreur",
        )
        .all()
    )

    return render(
        request,
        "materiaux/sorties_list.html",
        {
            "user": user,
            "sorties": sorties,
        },
    )


def sortie_add(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    if request.method == "POST":

        form = MateriauxOutForm(
            request.POST
        )

        if form.is_valid():

            sortie = form.save(
                commit=False
            )

            sortie.enregistreur = user

            try:
                sortie.save()

                messages.success(
                    request,
                    "Sortie enregistrée avec succès.",
                )

                return redirect(
                    "materiaux:sorties_list"
                )

            except ValidationError as error:
                add_validation_errors(
                    form,
                    error,
                )

    else:
        form = MateriauxOutForm()

    return render(
        request,
        "materiaux/sortie_form.html",
        {
            "user": user,
            "form": form,
            "title": "Nouvelle sortie",
        },
    )


def sortie_edit(request, pk):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    sortie = get_object_or_404(
        MateriauxOut,
        pk=pk,
    )

    if request.method == "POST":

        form = MateriauxOutForm(
            request.POST,
            instance=sortie,
        )

        if form.is_valid():

            objet = form.save(
                commit=False
            )

            objet.enregistreur_id = (
                sortie.enregistreur_id
            )

            try:
                objet.save()

                messages.success(
                    request,
                    "Sortie modifiée avec succès.",
                )

                return redirect(
                    "materiaux:sorties_list"
                )

            except ValidationError as error:
                add_validation_errors(
                    form,
                    error,
                )

    else:
        form = MateriauxOutForm(
            instance=sortie
        )

    return render(
        request,
        "materiaux/sortie_form.html",
        {
            "user": user,
            "form": form,
            "sortie": sortie,
            "title": "Modifier la sortie",
        },
    )


def sortie_delete(request, pk):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    sortie = get_object_or_404(
        MateriauxOut,
        pk=pk,
    )

    if request.method == "POST":

        try:
            sortie.delete()

            messages.success(
                request,
                "Sortie supprimée avec succès.",
            )

        except ProtectedError:
            messages.error(
                request,
                (
                    "Impossible de supprimer cette sortie "
                    "car elle est utilisée."
                ),
            )

    return redirect(
        "materiaux:sorties_list"
    )


# ============================================================
# STOCK ENTREPÔT
# ============================================================

def stock_entrepot(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    materiaux = Materiaux.objects.all()

    total_stock = sum(
        (
            materiau.stock_entrepot
            for materiau in materiaux
        ),
        Decimal("0"),
    )

    return render(
        request,
        "materiaux/stock_entrepot.html",
        {
            "user": user,
            "materiaux": materiaux,
            "total_stock": total_stock,
        },
    )


# ============================================================
# STOCK MAGASIN
# ============================================================

def stock_magasin(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    # ============================================================
    # FILTRES
    # ============================================================

    recherche = request.GET.get(
        "materiau",
        ""
    ).strip()

    destination = request.GET.get(
        "destination",
        ""
    ).strip()

    # ============================================================
    # DIVISIONS
    # ============================================================

    divisions = (
        MateriauxDivision.objects
        .select_related(
            "entree",
            "entree__materiau",
            "enregistreur",
        )
        .prefetch_related(
            "sorties",
        )
        .all()
    )

    # ============================================================
    # FILTRE MATÉRIAU
    # ============================================================

    if recherche:
        divisions = divisions.filter(
            entree__materiau__libelle__icontains=recherche
        )

    # ============================================================
    # FILTRE MAGASIN / CHANTIER
    # ============================================================

    if destination:
        divisions = divisions.filter(
            destination__icontains=destination
        )

    # ============================================================
    # REGROUPEMENT
    # MATÉRIAU + MAGASIN / CHANTIER
    # ============================================================

    groupes = {}

    for division in divisions:

        stock_restant = division.stock_restant

        # Ne pas afficher les magasins épuisés
        if stock_restant <= 0:
            continue

        materiau = division.entree.materiau

        cle = (
            materiau.id,
            division.destination,
        )

        if cle not in groupes:

            groupes[cle] = {
                "materiau": materiau,
                "destination": division.destination,

                "quantite_recue": Decimal("0"),
                "sorties": Decimal("0"),
                "stock_restant": Decimal("0"),

                "divisions": [],
            }

        groupe = groupes[cle]

        groupe["quantite_recue"] += division.quantite
        groupe["sorties"] += division.quantite_sortie
        groupe["stock_restant"] += stock_restant

        groupe["divisions"].append(
            division
        )

    # ============================================================
    # LISTE FINALE
    # ============================================================

    groupes = sorted(
        groupes.values(),
        key=lambda x: (
            x["materiau"].libelle.lower(),
            x["destination"].lower(),
        ),
    )

    # ============================================================
    # DESTINATIONS DISPONIBLES
    # ============================================================

    destinations = (
        MateriauxDivision.objects
        .values_list(
            "destination",
            flat=True,
        )
        .distinct()
        .order_by("destination")
    )

    # ============================================================
    # TOTAUX
    # ============================================================

    total_recu = sum(
        (
            groupe["quantite_recue"]
            for groupe in groupes
        ),
        Decimal("0"),
    )

    total_sorties = sum(
        (
            groupe["sorties"]
            for groupe in groupes
        ),
        Decimal("0"),
    )

    total_stock = sum(
        (
            groupe["stock_restant"]
            for groupe in groupes
        ),
        Decimal("0"),
    )

    return render(
        request,
        "materiaux/stock_magasin.html",
        {
            "user": user,

            "groupes": groupes,

            "recherche": recherche,
            "destination": destination,
            "destinations": destinations,

            "total_recu": total_recu,
            "total_sorties": total_sorties,
            "total_stock": total_stock,
        },
    )

# ============================================================
# VÉHICULES
# ============================================================

def vehicules_list(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    vehicules = (
        Vehicule.objects
        .prefetch_related(
            "depenses_gasoil",
            "depenses",
            "reparations",
            "activites_transport",
        )
        .all()
    )

    return render(
        request,
        "materiaux/vehicules_list.html",
        {
            "user": user,
            "vehicules": vehicules,
        },
    )


def vehicule_add(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    if request.method == "POST":

        form = VehiculeForm(
            request.POST
        )

        if form.is_valid():

            try:
                form.save()

                messages.success(
                    request,
                    "Véhicule ajouté avec succès.",
                )

                return redirect(
                    "materiaux:vehicules_list"
                )

            except ValidationError as error:
                add_validation_errors(
                    form,
                    error,
                )

    else:
        form = VehiculeForm()

    return render(
        request,
        "materiaux/vehicule_form.html",
        {
            "user": user,
            "form": form,
            "title": "Ajouter un véhicule",
        },
    )


def vehicule_edit(request, pk):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    vehicule = get_object_or_404(
        Vehicule,
        pk=pk,
    )

    if request.method == "POST":

        form = VehiculeForm(
            request.POST,
            instance=vehicule,
        )

        if form.is_valid():

            try:
                form.save()

                messages.success(
                    request,
                    "Véhicule modifié avec succès.",
                )

                return redirect(
                    "materiaux:vehicules_list"
                )

            except ValidationError as error:
                add_validation_errors(
                    form,
                    error,
                )

    else:
        form = VehiculeForm(
            instance=vehicule
        )

    return render(
        request,
        "materiaux/vehicule_form.html",
        {
            "user": user,
            "form": form,
            "vehicule": vehicule,
            "title": "Modifier le véhicule",
        },
    )


def vehicule_delete(request, pk):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    vehicule = get_object_or_404(
        Vehicule,
        pk=pk,
    )

    if request.method == "POST":

        try:
            vehicule.delete()

            messages.success(
                request,
                "Véhicule supprimé avec succès.",
            )

        except ProtectedError:
            messages.error(
                request,
                (
                    "Impossible de supprimer ce véhicule "
                    "car il possède des activités, dépenses, "
                    "gasoil ou réparations."
                ),
            )

    return redirect(
        "materiaux:vehicules_list"
    )


# ============================================================
# ACTIVITÉS DE TRANSPORT
# ============================================================

def activites_transport_list(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    activites = (
        ActiviteTransport.objects
        .select_related(
            "vehicule",
            "enregistreur",
        )
        .prefetch_related(
            "paiements_dockers",
        )
        .all()
    )

    return render(
        request,
        "materiaux/activites_transport_list.html",
        {
            "user": user,
            "activites": activites,
        },
    )


def activite_transport_add(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    if request.method == "POST":

        form = ActiviteTransportForm(
            request.POST
        )

        if form.is_valid():

            activite = form.save(
                commit=False
            )

            activite.enregistreur = user

            try:
                activite.save()

                messages.success(
                    request,
                    "Activité de transport ajoutée avec succès.",
                )

                return redirect(
                    "materiaux:activites_transport_list"
                )

            except ValidationError as error:
                add_validation_errors(
                    form,
                    error,
                )

    else:
        form = ActiviteTransportForm()

    return render(
        request,
        "materiaux/activite_transport_form.html",
        {
            "user": user,
            "form": form,
            "title": "Ajouter une activité de transport",
        },
    )


def activite_transport_edit(request, pk):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    activite = get_object_or_404(
        ActiviteTransport,
        pk=pk,
    )

    # Seul l'utilisateur ayant enregistré
    # l'activité peut la modifier.
    if activite.enregistreur_id != user.id:

        messages.error(
            request,
            (
                "Vous n'êtes pas autorisé à modifier "
                "cette activité."
            ),
        )

        return redirect(
            "materiaux:activites_transport_list"
        )

    if request.method == "POST":

        form = ActiviteTransportForm(
            request.POST,
            instance=activite,
        )

        if form.is_valid():

            objet = form.save(
                commit=False
            )

            objet.enregistreur_id = (
                activite.enregistreur_id
            )

            try:
                objet.save()

                messages.success(
                    request,
                    "Activité modifiée avec succès.",
                )

                return redirect(
                    "materiaux:activites_transport_list"
                )

            except ValidationError as error:
                add_validation_errors(
                    form,
                    error,
                )

    else:
        form = ActiviteTransportForm(
            instance=activite
        )

    return render(
        request,
        "materiaux/activite_transport_form.html",
        {
            "user": user,
            "form": form,
            "activite": activite,
            "title": "Modifier l'activité de transport",
        },
    )


def activite_transport_delete(request, pk):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    activite = get_object_or_404(
        ActiviteTransport,
        pk=pk,
    )

    if activite.enregistreur_id != user.id:

        messages.error(
            request,
            (
                "Vous n'êtes pas autorisé à supprimer "
                "cette activité."
            ),
        )

        return redirect(
            "materiaux:activites_transport_list"
        )

    if request.method == "POST":

        try:
            activite.delete()

            messages.success(
                request,
                "Activité supprimée avec succès.",
            )

        except ProtectedError:
            messages.error(
                request,
                (
                    "Impossible de supprimer cette activité "
                    "car elle possède des paiements docker."
                ),
            )

    return redirect(
        "materiaux:activites_transport_list"
    )

# ============================================================
# PAIEMENTS DOCKERS
# ============================================================
def paiements_dockers_list(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    paiements = (
        PaiementDocker.objects
        .select_related(
            "activite",
            "activite__vehicule",
            "enregistreur",
        )
        .all()
        .order_by(
            "-date_creation",
            "-id",
        )
    )

    total = (
        paiements.aggregate(
            total=Sum("montant")
        )["total"]
        or Decimal("0")
    )

    return render(
        request,
        "materiaux/paiements_dockers_list.html",
        {
            "user": user,
            "paiements": paiements,
            "total": total,
        },
    )
def paiement_docker_add(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    if request.method == "POST":
        form = PaiementDockerForm(request.POST)

        if form.is_valid():
            paiement = form.save(commit=False)
            paiement.enregistreur = user

            try:
                paiement.save()

                messages.success(
                    request,
                    "Le paiement docker a été enregistré avec succès."
                )

                return redirect("materiaux:paiements_dockers_list")

            except ValidationError as error:
                add_validation_errors(form, error)

    else:
        form = PaiementDockerForm()

    return render(
        request,
        "materiaux/paiement_docker_form.html",
        {
            "user": user,
            "form": form,
            "title": "Nouveau paiement docker",
            "action": "Ajouter",
        },
    )

def paiement_docker_edit(request, pk):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    paiement = get_object_or_404(
        PaiementDocker,
        pk=pk,
    )

    # ========================================================
    # SEUL L'ENREGISTREUR PEUT MODIFIER
    # ========================================================

    if paiement.enregistreur_id != user.id:

        messages.error(
            request,
            (
                "Vous ne pouvez pas modifier ce paiement. "
                "Seul son enregistreur peut le modifier."
            ),
        )

        return redirect(
            "materiaux:paiements_dockers_list"
        )

    if request.method == "POST":

        form = PaiementDockerForm(
            request.POST,
            instance=paiement,
        )

        if form.is_valid():

            objet = form.save(
                commit=False
            )

            # On conserve l'enregistreur original
            objet.enregistreur_id = (
                paiement.enregistreur_id
            )

            try:

                objet.save()

                messages.success(
                    request,
                    "Paiement docker modifié avec succès.",
                )

                return redirect(
                    "materiaux:paiements_dockers_list"
                )

            except ValidationError as error:

                add_validation_errors(
                    form,
                    error,
                )

    else:

        form = PaiementDockerForm(
            instance=paiement
        )

    return render(
        request,
        "materiaux/paiement_docker_form.html",
        {
            "user": user,
            "form": form,
            "paiement": paiement,
            "title": "Modifier le paiement docker",
        },
    )


def paiement_docker_delete(request, pk):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    paiement = get_object_or_404(
        PaiementDocker,
        pk=pk,
    )

    if request.method == "POST":

        # ====================================================
        # SEUL L'ENREGISTREUR PEUT SUPPRIMER
        # ====================================================

        if paiement.enregistreur_id != user.id:

            messages.error(
                request,
                (
                    "Vous ne pouvez pas supprimer ce paiement. "
                    "Seul son enregistreur peut le supprimer."
                ),
            )

            return redirect(
                "materiaux:paiements_dockers_list"
            )

        try:

            paiement.delete()

            messages.success(
                request,
                "Paiement docker supprimé avec succès.",
            )

        except ProtectedError:

            messages.error(
                request,
                "Impossible de supprimer ce paiement.",
            )

    return redirect(
        "materiaux:paiements_dockers_list"
    )

# ============================================================
# CATÉGORIES DE DÉPENSE
# ============================================================

def categories_depenses_list(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    categories = (
        CategorieDepense.objects
        .prefetch_related("depenses")
        .all()
    )

    return render(
        request,
        "materiaux/categories_depenses_list.html",
        {
            "user": user,
            "categories": categories,
        },
    )


def categorie_depense_add(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    if request.method == "POST":

        form = CategorieDepenseForm(
            request.POST
        )

        if form.is_valid():

            try:
                form.save()

                messages.success(
                    request,
                    "Catégorie ajoutée avec succès.",
                )

                return redirect(
                    "materiaux:categories_depenses_list"
                )

            except ValidationError as error:
                add_validation_errors(
                    form,
                    error,
                )

    else:
        form = CategorieDepenseForm()

    return render(
        request,
        "materiaux/categorie_depense_form.html",
        {
            "user": user,
            "form": form,
            "title": "Ajouter une catégorie",
        },
    )


def categorie_depense_edit(request, pk):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    categorie = get_object_or_404(
        CategorieDepense,
        pk=pk,
    )

    if request.method == "POST":

        form = CategorieDepenseForm(
            request.POST,
            instance=categorie,
        )

        if form.is_valid():

            try:
                form.save()

                messages.success(
                    request,
                    "Catégorie modifiée avec succès.",
                )

                return redirect(
                    "materiaux:categories_depenses_list"
                )

            except ValidationError as error:
                add_validation_errors(
                    form,
                    error,
                )

    else:
        form = CategorieDepenseForm(
            instance=categorie
        )

    return render(
        request,
        "materiaux/categorie_depense_form.html",
        {
            "user": user,
            "form": form,
            "categorie": categorie,
            "title": "Modifier la catégorie",
        },
    )


def categorie_depense_delete(request, pk):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    categorie = get_object_or_404(
        CategorieDepense,
        pk=pk,
    )

    if request.method == "POST":

        if categorie.depenses.exists():

            messages.error(
                request,
                (
                    "Impossible de supprimer cette catégorie "
                    "car elle est utilisée par des dépenses."
                ),
            )

        else:

            try:
                categorie.delete()

                messages.success(
                    request,
                    "Catégorie supprimée avec succès.",
                )

            except ProtectedError:
                messages.error(
                    request,
                    "Impossible de supprimer cette catégorie.",
                )

    return redirect(
        "materiaux:categories_depenses_list"
    )


# ============================================================
# DÉPENSES
# ============================================================

def depenses_list(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    depenses = (
        Depense.objects
        .select_related(
            "categorie",
            "vehicule",
            "enregistreur",
        )
        .all()
    )

    total = (
        depenses.aggregate(
            total=Sum("montant")
        )["total"]
        or Decimal("0")
    )

    return render(
        request,
        "materiaux/depenses_list.html",
        {
            "user": user,
            "depenses": depenses,
            "total": total,
        },
    )


def depense_add(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    if request.method == "POST":

        form = DepenseForm(
            request.POST
        )

        if form.is_valid():

            depense = form.save(
                commit=False
            )

            depense.enregistreur = user

            try:
                depense.save()

                messages.success(
                    request,
                    "Dépense enregistrée avec succès.",
                )

                return redirect(
                    "materiaux:depenses_list"
                )

            except ValidationError as error:
                add_validation_errors(
                    form,
                    error,
                )

    else:
        form = DepenseForm()

    return render(
        request,
        "materiaux/depense_form.html",
        {
            "user": user,
            "form": form,
            "title": "Ajouter une dépense",
        },
    )


def depense_edit(request, pk):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    depense = get_object_or_404(
        Depense,
        pk=pk,
    )

    if request.method == "POST":

        form = DepenseForm(
            request.POST,
            instance=depense,
        )

        if form.is_valid():

            objet = form.save(
                commit=False
            )

            objet.enregistreur_id = (
                depense.enregistreur_id
            )

            try:
                objet.save()

                messages.success(
                    request,
                    "Dépense modifiée avec succès.",
                )

                return redirect(
                    "materiaux:depenses_list"
                )

            except ValidationError as error:
                add_validation_errors(
                    form,
                    error,
                )

    else:
        form = DepenseForm(
            instance=depense
        )

    return render(
        request,
        "materiaux/depense_form.html",
        {
            "user": user,
            "form": form,
            "depense": depense,
            "title": "Modifier la dépense",
        },
    )


def depense_delete(request, pk):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    depense = get_object_or_404(
        Depense,
        pk=pk,
    )

    if request.method == "POST":

        try:
            depense.delete()

            messages.success(
                request,
                "Dépense supprimée avec succès.",
            )

        except ProtectedError:
            messages.error(
                request,
                "Impossible de supprimer cette dépense.",
            )

    return redirect(
        "materiaux:depenses_list"
    )


# ============================================================
# GASOIL
# ============================================================
def depenses_gasoil_list(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    # ============================================================
    # FILTRES
    # ============================================================

    vehicule_id = request.GET.get("vehicule", "").strip()
    date_debut = request.GET.get("date_debut", "").strip()
    date_fin = request.GET.get("date_fin", "").strip()

    # ============================================================
    # LISTE DES VÉHICULES POUR LE FILTRE
    # ============================================================

    vehicules = (
        Vehicule.objects
        .all()
        .order_by("immatriculation")
    )

    # ============================================================
    # DÉPENSES GASOIL
    # ============================================================

    depenses = (
        DepenseGasoil.objects
        .select_related(
            "vehicule",
            "enregistreur",
        )
        .all()
        .order_by(
            "-date_gasoil",
            "-id",
        )
    )

    # ============================================================
    # FILTRE VÉHICULE
    # ============================================================

    if vehicule_id:
        depenses = depenses.filter(
            vehicule_id=vehicule_id
        )

    # ============================================================
    # FILTRE DATE DÉBUT
    # ============================================================

    if date_debut:
        depenses = depenses.filter(
            date_gasoil__gte=date_debut
        )

    # ============================================================
    # FILTRE DATE FIN
    # ============================================================

    if date_fin:
        depenses = depenses.filter(
            date_gasoil__lte=date_fin
        )

    # ============================================================
    # TOTAL LITRES APRÈS FILTRES
    # ============================================================

    total_litres = (
        depenses.aggregate(
            total=Sum("quantite_litre")
        )["total"]
        or Decimal("0")
    )

    # ============================================================
    # TOTAL DÉPENSE APRÈS FILTRES
    # ============================================================

    total = (
        depenses.aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0")
    )

    # ============================================================
    # RENDU
    # ============================================================

    return render(
        request,
        "materiaux/gasoil_list.html",
        {
            "user": user,
            "gasoils": depenses,
            "vehicules": vehicules,

            "vehicule_id": vehicule_id,
            "date_debut": date_debut,
            "date_fin": date_fin,

            "total_litres": total_litres,
            "total": total,
        },
    )

def depense_gasoil_add(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    if request.method == "POST":

        form = DepenseGasoilForm(
            request.POST
        )

        if form.is_valid():

            depense = form.save(
                commit=False
            )

            depense.enregistreur = user

            try:
                depense.save()

                messages.success(
                    request,
                    "Dépense gasoil enregistrée avec succès.",
                )

                return redirect(
                    "materiaux:depenses_gasoil_list"
                )

            except ValidationError as error:
                add_validation_errors(
                    form,
                    error,
                )

    else:
        form = DepenseGasoilForm()

    return render(
        request,
        "materiaux/gasoil_form.html",
        {
            "user": user,
            "form": form,
            "title": "Ajouter du gasoil",
        },
    )


def depense_gasoil_edit(request, pk):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    depense = get_object_or_404(
        DepenseGasoil,
        pk=pk,
    )

    if request.method == "POST":

        form = DepenseGasoilForm(
            request.POST,
            instance=depense,
        )

        if form.is_valid():

            objet = form.save(
                commit=False
            )

            objet.enregistreur_id = (
                depense.enregistreur_id
            )

            try:
                objet.save()

                messages.success(
                    request,
                    "Dépense gasoil modifiée avec succès.",
                )

                return redirect(
                    "materiaux:depenses_gasoil_list"
                )

            except ValidationError as error:
                add_validation_errors(
                    form,
                    error,
                )

    else:
        form = DepenseGasoilForm(
            instance=depense
        )

    return render(
        request,
        "materiaux/depense_gasoil_form.html",
        {
            "user": user,
            "form": form,
            "depense": depense,
            "title": "Modifier la dépense gasoil",
        },
    )


def depense_gasoil_delete(request, pk):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    depense = get_object_or_404(
        DepenseGasoil,
        pk=pk,
    )

    if request.method == "POST":

        try:
            depense.delete()

            messages.success(
                request,
                "Dépense gasoil supprimée avec succès.",
            )

        except ProtectedError:
            messages.error(
                request,
                "Impossible de supprimer cette dépense gasoil.",
            )

    return redirect(
        "materiaux:depenses_gasoil_list"
    )


# ============================================================
# RÉPARATIONS VÉHICULES
# ============================================================

def reparations_list(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    reparations = (
        ReparationVehicule.objects
        .select_related(
            "vehicule",
            "enregistreur",
        )
        .all()
    )

    total_pieces = sum(
        (
            reparation.montant_piece
            for reparation in reparations
        ),
        Decimal("0"),
    )

    total_main_oeuvre = sum(
        (
            reparation.montant_main_oeuvre
            for reparation in reparations
        ),
        Decimal("0"),
    )

    total_general = (
        total_pieces
        + total_main_oeuvre
    )

    return render(
        request,
        "materiaux/reparations_list.html",
        {
            "user": user,
            "reparations": reparations,
            "total_pieces": total_pieces,
            "total_main_oeuvre": total_main_oeuvre,
            "total_general": total_general,
        },
    )


def reparation_add(request):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    if request.method == "POST":

        form = ReparationVehiculeForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            reparation = form.save(
                commit=False
            )

            reparation.enregistreur = user

            try:
                reparation.save()

                messages.success(
                    request,
                    "Réparation enregistrée avec succès.",
                )

                return redirect(
                    "materiaux:reparations_list"
                )

            except ValidationError as error:
                add_validation_errors(
                    form,
                    error,
                )

    else:
        form = ReparationVehiculeForm()

    return render(
        request,
        "materiaux/reparation_form.html",
        {
            "user": user,
            "form": form,
            "title": "Ajouter une réparation",
        },
    )


def reparation_edit(request, pk):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    reparation = get_object_or_404(
        ReparationVehicule,
        pk=pk,
    )

    # Seul l'utilisateur qui a enregistré
    # la réparation peut la modifier.
    if reparation.enregistreur_id != user.id:

        messages.error(
            request,
            (
                "Vous n'êtes pas autorisé à modifier "
                "cette réparation."
            ),
        )

        return redirect(
            "materiaux:reparations_list"
        )

    if request.method == "POST":

        form = ReparationVehiculeForm(
            request.POST,
            request.FILES,
            instance=reparation,
        )

        if form.is_valid():

            objet = form.save(
                commit=False
            )

            objet.enregistreur_id = (
                reparation.enregistreur_id
            )

            try:
                objet.save()

                messages.success(
                    request,
                    "Réparation modifiée avec succès.",
                )

                return redirect(
                    "materiaux:reparations_list"
                )

            except ValidationError as error:
                add_validation_errors(
                    form,
                    error,
                )

    else:
        form = ReparationVehiculeForm(
            instance=reparation
        )

    return render(
        request,
        "materiaux/reparation_form.html",
        {
            "user": user,
            "form": form,
            "reparation": reparation,
            "title": "Modifier la réparation",
        },
    )


def reparation_delete(request, pk):
    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    reparation = get_object_or_404(
        ReparationVehicule,
        pk=pk,
    )

    # Seul l'utilisateur qui a enregistré
    # la réparation peut la supprimer.
    if reparation.enregistreur_id != user.id:

        messages.error(
            request,
            (
                "Vous n'êtes pas autorisé à supprimer "
                "cette réparation."
            ),
        )

        return redirect(
            "materiaux:reparations_list"
        )

    if request.method == "POST":

        try:
            reparation.delete()

            messages.success(
                request,
                "Réparation supprimée avec succès.",
            )

            return redirect(
                "materiaux:reparations_list"
            )

        except ProtectedError:
            messages.error(
                request,
                "Impossible de supprimer cette réparation.",
            )

            return redirect(
                "materiaux:reparations_list"
            )

    return render(
        request,
        "materiaux/reparation_delete.html",
        {
            "user": user,
            "reparation": reparation,
        },
    )