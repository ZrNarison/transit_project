from decimal import Decimal

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.db.models import Sum
from django.shortcuts import get_object_or_404, redirect, render

from users.models import AppUser

from .forms import (
    ActiviteTransportForm,
    CategorieDepenseForm,
    DepenseForm,
    DepenseGasoilForm,
    DockerForm,
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
    Docker,
    Materiaux,
    MateriauxDivision,
    MateriauxEntree,
    MateriauxOut,
    PaiementDocker,
    ReparationVehicule,
    Vehicule,
)


# ==========================================================
# UTILITAIRES
# ==========================================================

def get_current_user(request):
    """
    Récupère l'utilisateur connecté depuis la session.
    """

    user_id = request.session.get("user_id")

    if not user_id:
        return None

    return AppUser.objects.filter(id=user_id).first()


def require_user(request):
    """
    Retourne l'utilisateur connecté.
    Retourne None si aucun utilisateur n'est connecté.
    """

    return get_current_user(request)


def check_user(request):
    """
    Vérifie la connexion et redirige vers la page de connexion
    si nécessaire.
    """

    user = get_current_user(request)

    if user is None:
        return redirect("users:login")

    return user


# ==========================================================
# DASHBOARD
# ==========================================================
def dashboard(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    # ======================================================
    # MATÉRIAUX
    # ======================================================

    materiaux = (
        Materiaux.objects
        .prefetch_related(
            "entrees__divisions__sorties"
        )
        .all()
    )

    total_materiaux = materiaux.count()

    total_entrees = sum(
        (
            materiau.total_entrees
            for materiau in materiaux
        ),
        Decimal("0"),
    )

    total_divisions = sum(
        (
            materiau.total_divisions
            for materiau in materiaux
        ),
        Decimal("0"),
    )

    total_sorties = sum(
        (
            materiau.total_sorties
            for materiau in materiaux
        ),
        Decimal("0"),
    )

    stock_entrepot = (
        total_entrees - total_divisions
    )

    stock_magasin = (
        total_divisions - total_sorties
    )

    # ======================================================
    # STATISTIQUES PAR MATÉRIAU
    # ======================================================

    materiaux_stats = []

    for materiau in materiaux:

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

        materiaux_stats.append(
            {
                "materiau": materiau,
                "entrees": entrees,
                "divisions": divisions,
                "sorties": sorties,
                "stock_entrepot": stock_entrepot_materiau,
                "stock_magasin": stock_magasin_materiau,
                "stock_total": stock_total_materiau,
            }
        )

    # ======================================================
    # ACTIVITÉS
    # ======================================================

    nombre_activites = (
        ActiviteTransport.objects.count()
    )

    total_vehicules = (
        Vehicule.objects.count()
    )

    total_dockers = (
        Docker.objects.count()
    )

    # ======================================================
    # GASOIL
    # ======================================================

    total_gasoil = (
        DepenseGasoil.objects
        .aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0")
    )

    total_litres_gasoil = (
        DepenseGasoil.objects
        .aggregate(
            total=Sum("quantite_litre")
        )["total"]
        or Decimal("0")
    )

    # ======================================================
    # RÉPARATIONS
    # ======================================================

    total_reparations = (
        ReparationVehicule.objects
        .aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0")
    )

    nombre_reparations = (
        ReparationVehicule.objects.count()
    )

    # ======================================================
    # DOCKERS
    # ======================================================

    total_dockers_paye = (
        PaiementDocker.objects
        .aggregate(
            total=Sum("montant")
        )["total"]
        or Decimal("0")
    )

    # ======================================================
    # DÉPENSES GÉNÉRALES
    # ======================================================

    total_depenses = (
        Depense.objects
        .aggregate(
            total=Sum("montant")
        )["total"]
        or Decimal("0")
    )

    total_depenses_generales = (
        total_gasoil
        + total_reparations
        + total_dockers_paye
        + total_depenses
    )

    # ======================================================
    # TRANSPORT
    # ======================================================

    total_transport = (
        ActiviteTransport.objects
        .aggregate(
            total=Sum("montant_transport")
        )["total"]
        or Decimal("0")
    )

    resultat_transport = (
        total_transport
        - total_depenses_generales
    )

    # ======================================================
    # CONTEXTE
    # ======================================================

    context = {

        "user": user,

        # ------------------------------
        # MATÉRIAUX
        # ------------------------------

        "materiaux": materiaux,

        "total_materiaux": total_materiaux,

        "total_entrees": total_entrees,

        "total_divisions": total_divisions,

        "total_sorties": total_sorties,

        "stock_entrepot": stock_entrepot,

        "stock_magasin": stock_magasin,

        "materiaux_stats": materiaux_stats,

        # ------------------------------
        # ACTIVITÉS
        # ------------------------------

        "nombre_activites": nombre_activites,

        "total_vehicules": total_vehicules,

        "total_dockers": total_dockers,

        # ------------------------------
        # GASOIL
        # ------------------------------

        "total_gasoil": total_gasoil,

        "total_litres_gasoil": total_litres_gasoil,

        # ------------------------------
        # RÉPARATIONS
        # ------------------------------

        "total_reparations": total_reparations,

        "nombre_reparations": nombre_reparations,

        # ------------------------------
        # DOCKERS
        # ------------------------------

        "total_dockers_paye": total_dockers_paye,

        # ------------------------------
        # DÉPENSES
        # ------------------------------

        "total_depenses": total_depenses,

        "total_depenses_generales": (
            total_depenses_generales
        ),

        # ------------------------------
        # TRANSPORT
        # ------------------------------

        "total_transport": total_transport,

        "resultat_transport": resultat_transport,

    }

    return render(
        request,
        "materiaux/dashboard.html",
        context,
    )

# ==========================================================
# MATÉRIAUX
# ==========================================================
def materiaux_list(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    materiaux = (
        Materiaux.objects
        .prefetch_related(
            "entrees__divisions__sorties"
        )
        .all()
    )

    return render(
        request,
        "materiaux/materiaux_list.html",
        {
            "user": user,
            "objets": materiaux,
        },
    )

def materiaux_add(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    if request.method == "POST":

        form = MateriauxForm(request.POST)

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Matériau ajouté avec succès.",
            )

            return redirect(
                "materiaux:materiaux_list"
            )

    else:

        form = MateriauxForm()

    return render(
        request,
        "materiaux/materiaux_form.html",
        {
            "user": user,
            "form": form,
            "titre": "Ajouter un matériau",
        },
    )


def materiaux_edit(request, pk):

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

            form.save()

            messages.success(
                request,
                "Matériau modifié avec succès.",
            )

            return redirect(
                "materiaux:materiaux_list"
            )

    else:

        form = MateriauxForm(
            instance=materiau,
        )

    return render(
        request,
        "materiaux/materiaux_form.html",
        {
            "user": user,
            "form": form,
            "titre": "Modifier le matériau",
            "materiau": materiau,
        },
    )


def materiaux_delete(request, pk):

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

        except Exception:

            messages.error(
                request,
                "Impossible de supprimer ce matériau "
                "car il est utilisé dans des enregistrements.",
            )

    return redirect(
        "materiaux:materiaux_list"
    )


# ==========================================================
# ENTRÉES ENTREPÔT
# ==========================================================

def entrees_list(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    entrees = (
        MateriauxEntree.objects
        .select_related(
            "materiau",
            "enregistreur",
        )
        .prefetch_related(
            "divisions__sorties"
        )
        .all()
    )

    return render(
        request,
        "materiaux/entrees_list.html",
        {
            "user": user,
            "entrees": entrees,
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
            entree.save()

            messages.success(
                request,
                "Entrée entrepôt enregistrée.",
            )

            return redirect(
                "materiaux:entrees_list"
            )

    else:

        form = MateriauxEntreeForm()

    return render(
        request,
        "materiaux/entree_form.html",
        {
            "user": user,
            "form": form,
            "titre": "Nouvelle entrée entrepôt",
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

    if request.method == "POST":

        form = MateriauxEntreeForm(
            request.POST,
            instance=entree,
        )

        if form.is_valid():

            entree = form.save(
                commit=False
            )

            entree.enregistreur = user
            entree.save()

            messages.success(
                request,
                "Entrée modifiée avec succès.",
            )

            return redirect(
                "materiaux:entrees_list"
            )

    else:

        form = MateriauxEntreeForm(
            instance=entree
        )

    return render(
        request,
        "materiaux/entree_form.html",
        {
            "user": user,
            "form": form,
            "titre": "Modifier l'entrée",
            "entree": entree,
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

    if request.method == "POST":

        if entree.divisions.exists():

            messages.error(
                request,
                "Impossible de supprimer cette entrée : "
                "elle possède déjà des divisions.",
            )

        else:

            entree.delete()

            messages.success(
                request,
                "Entrée supprimée avec succès.",
            )

    return redirect(
        "materiaux:entrees_list"
    )


# ==========================================================
# DIVISIONS
# ==========================================================

def divisions_list(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    divisions = (
        MateriauxDivision.objects
        .select_related(
            "entree__materiau",
            "enregistreur",
        )
        .prefetch_related(
            "sorties"
        )
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

            try:

                division = form.save(
                    commit=False
                )

                division.enregistreur = user
                division.save()

                messages.success(
                    request,
                    "Division enregistrée avec succès.",
                )

                return redirect(
                    "materiaux:divisions_list"
                )

            except ValidationError as e:

                form.add_error(
                    None,
                    e,
                )

    else:

        form = MateriauxDivisionForm()

    return render(
        request,
        "materiaux/division_form.html",
        {
            "user": user,
            "form": form,
            "titre": "Nouvelle division",
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

            try:

                division = form.save(
                    commit=False
                )

                division.enregistreur = user
                division.save()

                messages.success(
                    request,
                    "Division modifiée avec succès.",
                )

                return redirect(
                    "materiaux:divisions_list"
                )

            except ValidationError as e:

                form.add_error(
                    None,
                    e,
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
            "titre": "Modifier la division",
            "division": division,
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
                "Impossible de supprimer cette division : "
                "elle possède déjà des sorties.",
            )

        else:

            division.delete()

            messages.success(
                request,
                "Division supprimée avec succès.",
            )

    return redirect(
        "materiaux:divisions_list"
    )


# ==========================================================
# SORTIES
# ==========================================================
def sorties_list(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    sorties = (
        MateriauxOut.objects
        .select_related(
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
            "objets": sorties,
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

            try:

                sortie = form.save(
                    commit=False
                )

                sortie.enregistreur = user
                sortie.save()

                messages.success(
                    request,
                    "Sortie magasin enregistrée.",
                )

                return redirect(
                    "materiaux:sorties_list"
                )

            except ValidationError as e:

                form.add_error(
                    None,
                    e,
                )

    else:

        form = MateriauxOutForm()

    return render(
        request,
        "materiaux/sortie_form.html",
        {
            "user": user,
            "form": form,
            "titre": "Nouvelle sortie magasin",
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

            try:

                sortie = form.save(
                    commit=False
                )

                sortie.enregistreur = user
                sortie.save()

                messages.success(
                    request,
                    "Sortie modifiée avec succès.",
                )

                return redirect(
                    "materiaux:sorties_list"
                )

            except ValidationError as e:

                form.add_error(
                    None,
                    e,
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
            "titre": "Modifier la sortie",
            "sortie": sortie,
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

        sortie.delete()

        messages.success(
            request,
            "Sortie supprimée avec succès.",
        )

    return redirect(
        "materiaux:sorties_list"
    )


# ==========================================================
# STOCK ENTREPÔT
# ==========================================================

def stock_entrepot(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    materiaux = (
        Materiaux.objects
        .prefetch_related(
            "entrees__divisions__sorties"
        )
        .all()
    )

    return render(
        request,
        "materiaux/stock_entrepot.html",
        {
            "user": user,
            "materiaux": materiaux,
            "titre": "Stock entrepôt",
        },
    )


# ==========================================================
# STOCK MAGASIN
# ==========================================================

def stock_magasin(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    materiaux = (
        Materiaux.objects
        .prefetch_related(
            "entrees__divisions__sorties"
        )
        .all()
    )

    return render(
        request,
        "materiaux/stock_magasin.html",
        {
            "user": user,
            "materiaux": materiaux,
            "titre": "Stock magasin",
        },
    )


# ==========================================================
# VÉHICULES
# ==========================================================

def vehicules_list(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    vehicules = (
        Vehicule.objects
        .prefetch_related(
            "depenses_gasoil",
            "reparations",
            "depenses",
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

            form.save()

            messages.success(
                request,
                "Véhicule ajouté avec succès.",
            )

            return redirect(
                "materiaux:vehicules_list"
            )

    else:

        form = VehiculeForm()

    return render(
        request,
        "materiaux/vehicule_form.html",
        {
            "user": user,
            "form": form,
            "titre": "Ajouter un véhicule",
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

            form.save()

            messages.success(
                request,
                "Véhicule modifié avec succès.",
            )

            return redirect(
                "materiaux:vehicules_list"
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
            "titre": "Modifier le véhicule",
            "vehicule": vehicule,
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

        except Exception:

            messages.error(
                request,
                "Impossible de supprimer ce véhicule "
                "car il possède des opérations.",
            )

    return redirect(
        "materiaux:vehicules_list"
    )


# ==========================================================
# DOCKERS
# ==========================================================

def dockers_list(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    dockers = (
        Docker.objects
        .prefetch_related(
            "paiements"
        )
        .all()
    )

    return render(
        request,
        "materiaux/dockers_list.html",
        {
            "user": user,
            "dockers": dockers,
        },
    )


def docker_add(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    if request.method == "POST":

        form = DockerForm(
            request.POST
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Docker ajouté avec succès.",
            )

            return redirect(
                "materiaux:dockers_list"
            )

    else:

        form = DockerForm()

    return render(
        request,
        "materiaux/docker_form.html",
        {
            "user": user,
            "form": form,
            "titre": "Ajouter un docker",
        },
    )


def docker_edit(request, pk):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    docker = get_object_or_404(
        Docker,
        pk=pk,
    )

    if request.method == "POST":

        form = DockerForm(
            request.POST,
            instance=docker,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Docker modifié avec succès.",
            )

            return redirect(
                "materiaux:dockers_list"
            )

    else:

        form = DockerForm(
            instance=docker
        )

    return render(
        request,
        "materiaux/docker_form.html",
        {
            "user": user,
            "form": form,
            "titre": "Modifier le docker",
            "docker": docker,
        },
    )


def docker_delete(request, pk):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    docker = get_object_or_404(
        Docker,
        pk=pk,
    )

    if request.method == "POST":

        try:

            docker.delete()

            messages.success(
                request,
                "Docker supprimé avec succès.",
            )

        except Exception:

            messages.error(
                request,
                "Impossible de supprimer ce docker "
                "car il possède des paiements.",
            )

    return redirect(
        "materiaux:dockers_list"
    )


# ==========================================================
# CATÉGORIES DE DÉPENSES
# ==========================================================

def categories_depenses_list(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    categories = (
        CategorieDepense.objects.all()
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

            form.save()

            messages.success(
                request,
                "Catégorie ajoutée avec succès.",
            )

            return redirect(
                "materiaux:categories_depenses_list"
            )

    else:

        form = CategorieDepenseForm()

    return render(
        request,
        "materiaux/categorie_depense_form.html",
        {
            "user": user,
            "form": form,
            "titre": "Ajouter une catégorie",
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

            form.save()

            messages.success(
                request,
                "Catégorie modifiée avec succès.",
            )

            return redirect(
                "materiaux:categories_depenses_list"
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
            "titre": "Modifier la catégorie",
            "categorie": categorie,
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

        try:

            categorie.delete()

            messages.success(
                request,
                "Catégorie supprimée avec succès.",
            )

        except Exception:

            messages.error(
                request,
                "Impossible de supprimer cette catégorie "
                "car elle est utilisée dans des dépenses.",
            )

    return redirect(
        "materiaux:categories_depenses_list"
    )


# ==========================================================
# ACTIVITÉS TRANSPORT
# ==========================================================

def activites_transport_list(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    activites = (
        ActiviteTransport.objects
        .select_related(
            "vehicule",
            "materiau",
            "enregistreur",
        )
        .prefetch_related(
            "depenses_gasoil",
            "reparations",
            "paiements_dockers",
            "depenses",
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
            activite.save()

            messages.success(
                request,
                "Activité de transport enregistrée.",
            )

            return redirect(
                "materiaux:activites_transport_list"
            )

    else:

        form = ActiviteTransportForm()

    return render(
        request,
        "materiaux/activite_transport_form.html",
        {
            "user": user,
            "form": form,
            "titre": "Nouvelle activité de transport",
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

    if request.method == "POST":

        form = ActiviteTransportForm(
            request.POST,
            instance=activite,
        )

        if form.is_valid():

            activite = form.save(
                commit=False
            )

            activite.enregistreur = user
            activite.save()

            messages.success(
                request,
                "Activité de transport modifiée.",
            )

            return redirect(
                "materiaux:activites_transport_list"
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
            "titre": "Modifier l'activité de transport",
            "activite": activite,
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

    if request.method == "POST":

        try:

            activite.delete()

            messages.success(
                request,
                "Activité de transport supprimée.",
            )

        except Exception:

            messages.error(
                request,
                "Impossible de supprimer cette activité "
                "car elle possède des opérations liées.",
            )

    return redirect(
        "materiaux:activites_transport_list"
    )


# ==========================================================
# PAIEMENTS DOCKERS
# ==========================================================

def paiements_dockers_list(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    paiements = (
        PaiementDocker.objects
        .select_related(
            "activite",
            "docker",
            "enregistreur",
        )
        .all()
    )

    return render(
        request,
        "materiaux/paiements_dockers_list.html",
        {
            "user": user,
            "paiements": paiements,
        },
    )


def paiement_docker_add(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    if request.method == "POST":

        form = PaiementDockerForm(
            request.POST
        )

        if form.is_valid():

            try:

                paiement = form.save(
                    commit=False
                )

                paiement.enregistreur = user
                paiement.save()

                messages.success(
                    request,
                    "Paiement docker enregistré.",
                )

                return redirect(
                    "materiaux:paiements_dockers_list"
                )

            except ValidationError as e:

                form.add_error(
                    None,
                    e,
                )

    else:

        form = PaiementDockerForm()

    return render(
        request,
        "materiaux/paiement_docker_form.html",
        {
            "user": user,
            "form": form,
            "titre": "Nouveau paiement docker",
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

    if request.method == "POST":

        form = PaiementDockerForm(
            request.POST,
            instance=paiement,
        )

        if form.is_valid():

            try:

                paiement = form.save(
                    commit=False
                )

                paiement.enregistreur = user
                paiement.save()

                messages.success(
                    request,
                    "Paiement docker modifié.",
                )

                return redirect(
                    "materiaux:paiements_dockers_list"
                )

            except ValidationError as e:

                form.add_error(
                    None,
                    e,
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
            "titre": "Modifier le paiement docker",
            "paiement": paiement,
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

        paiement.delete()

        messages.success(
            request,
            "Paiement docker supprimé.",
        )

    return redirect(
        "materiaux:paiements_dockers_list"
    )


# ==========================================================
# DÉPENSES
# ==========================================================

def depenses_list(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    depenses = (
        Depense.objects
        .select_related(
            "categorie",
            "vehicule",
            "activite",
            "materiau",
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
            depense.save()

            messages.success(
                request,
                "Dépense enregistrée avec succès.",
            )

            return redirect(
                "materiaux:depenses_list"
            )

    else:

        form = DepenseForm()

    return render(
        request,
        "materiaux/depense_form.html",
        {
            "user": user,
            "form": form,
            "titre": "Nouvelle dépense",
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

            depense = form.save(
                commit=False
            )

            depense.enregistreur = user
            depense.save()

            messages.success(
                request,
                "Dépense modifiée avec succès.",
            )

            return redirect(
                "materiaux:depenses_list"
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
            "titre": "Modifier la dépense",
            "depense": depense,
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

        depense.delete()

        messages.success(
            request,
            "Dépense supprimée avec succès.",
        )

    return redirect(
        "materiaux:depenses_list"
    )


# ==========================================================
# GASOIL
# ==========================================================

def gasoil_list(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    gasoils = (
        DepenseGasoil.objects
        .select_related(
            "vehicule",
            "activite",
            "enregistreur",
        )
        .all()
    )

    total = (
        gasoils.aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0")
    )

    total_litres = (
        gasoils.aggregate(
            total=Sum("quantite_litre")
        )["total"]
        or Decimal("0")
    )

    return render(
        request,
        "materiaux/gasoil_list.html",
        {
            "user": user,
            "gasoils": gasoils,
            "total": total,
            "total_litres": total_litres,
        },
    )

def gasoil_add(request):

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
            depense.save()

            messages.success(
                request,
                "Dépense gasoil enregistrée.",
            )

            return redirect(
                "materiaux:gasoil_list"
            )

    else:

        form = DepenseGasoilForm()

    return render(
        request,
        "materiaux/gasoil_form.html",
        {
            "user": user,
            "form": form,
            "titre": "Nouvelle dépense gasoil",
        },
    )


def gasoil_edit(request, pk):

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

            depense = form.save(
                commit=False
            )

            depense.enregistreur = user
            depense.save()

            messages.success(
                request,
                "Dépense gasoil modifiée.",
            )

            return redirect(
                "materiaux:gasoil_list"
            )

    else:

        form = DepenseGasoilForm(
            instance=depense
        )

    return render(
        request,
        "materiaux/gasoil_form.html",
        {
            "user": user,
            "form": form,
            "titre": "Modifier la dépense gasoil",
            "depense": depense,
        },
    )


def gasoil_delete(request, pk):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    depense = get_object_or_404(
        DepenseGasoil,
        pk=pk,
    )

    if request.method == "POST":

        depense.delete()

        messages.success(
            request,
            "Dépense gasoil supprimée.",
        )

    return redirect(
        "materiaux:gasoil_list"
    )


# ==========================================================
# RÉPARATIONS / ENTRETIEN
# ==========================================================

def reparations_list(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    reparations = (
        ReparationVehicule.objects
        .select_related(
            "vehicule",
            "activite",
            "enregistreur",
        )
        .all()
    )

    total = (
        reparations.aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0")
    )

    return render(
        request,
        "materiaux/reparations_list.html",
        {
            "user": user,
            "reparations": reparations,
            "total": total,
        },
    )


def reparation_add(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    if request.method == "POST":

        form = ReparationVehiculeForm(
            request.POST
        )

        if form.is_valid():

            reparation = form.save(
                commit=False
            )

            reparation.enregistreur = user
            reparation.save()

            messages.success(
                request,
                "Réparation enregistrée.",
            )

            return redirect(
                "materiaux:reparations_list"
            )

    else:

        form = ReparationVehiculeForm()

    return render(
        request,
        "materiaux/reparation_form.html",
        {
            "user": user,
            "form": form,
            "titre": "Nouvelle réparation / entretien",
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

    if request.method == "POST":

        form = ReparationVehiculeForm(
            request.POST,
            instance=reparation,
        )

        if form.is_valid():

            reparation = form.save(
                commit=False
            )

            reparation.enregistreur = user
            reparation.save()

            messages.success(
                request,
                "Réparation modifiée.",
            )

            return redirect(
                "materiaux:reparations_list"
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
            "titre": "Modifier la réparation / entretien",
            "reparation": reparation,
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

    if request.method == "POST":

        reparation.delete()

        messages.success(
            request,
            "Réparation supprimée.",
        )

    return redirect(
        "materiaux:reparations_list"
    )