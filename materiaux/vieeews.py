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
# AUTHENTIFICATION / UTILISATEUR COURANT
# ============================================================

def get_current_user(request):
    """
    Récupère l'utilisateur connecté à partir de la session.
    """

    user_id = request.session.get("user_id")

    if not user_id:
        return None

    return AppUser.objects.filter(id=user_id).first()


def require_user(request):
    """
    Retourne l'utilisateur courant.
    Conservé pour compatibilité avec l'ancien code.
    """

    return get_current_user(request)


def check_user(request):
    """
    Vérifie qu'un utilisateur est connecté.
    """

    user = get_current_user(request)

    if user is None:
        return redirect("users:login")

    return user


# ============================================================
# UTILITAIRE VALIDATION
# ============================================================

def add_validation_errors(form, error):
    """
    Ajoute proprement les erreurs ValidationError
    au formulaire Django.
    """

    if hasattr(error, "message_dict"):
        for field, errors in error.message_dict.items():
            for message in errors:
                form.add_error(
                    field if field != "__all__" else None,
                    message,
                )
    else:
        form.add_error(None, error)


# ============================================================
# TABLEAU DE BORD
# ============================================================

def dashboard(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    materiaux = (
        Materiaux.objects
        .all()
        .order_by("libelle")
    )

    # --------------------------------------------------------
    # MATÉRIAUX
    # --------------------------------------------------------

    total_entrees = (
        MateriauxEntree.objects.aggregate(
            total=Sum("entree")
        )["total"]
        or Decimal("0")
    )

    total_divise = (
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

    stock_entrepot = (
        total_entrees
        - total_divise
    )

    stock_magasin = (
        total_divise
        - total_sorties
    )

    stock_total = (
        stock_entrepot
        + stock_magasin
    )

    # --------------------------------------------------------
    # VÉHICULES
    # --------------------------------------------------------

    total_vehicules = Vehicule.objects.count()

    # --------------------------------------------------------
    # GASOIL
    # --------------------------------------------------------

    total_gasoil = (
        DepenseGasoil.objects.aggregate(
            total=Sum("total")
        )["total"]
        or Decimal("0")
    )

    # --------------------------------------------------------
    # TRANSPORT
    # --------------------------------------------------------

    total_activites_transport = (
        ActiviteTransport.objects.count()
    )

    total_transport = (
        ActiviteTransport.objects.aggregate(
            total=Sum("montant_transport")
        )["total"]
        or Decimal("0")
    )

    # --------------------------------------------------------
    # DOCKERS
    # --------------------------------------------------------

    total_dockers = (
        PaiementDocker.objects.aggregate(
            total=Sum("montant")
        )["total"]
        or Decimal("0")
    )

    # --------------------------------------------------------
    # DÉPENSES
    # --------------------------------------------------------

    depenses = Depense.objects.all()

    total_depenses = sum(
        (
            d.montant or Decimal("0")
            for d in depenses
        ),
        Decimal("0"),
    )

    # --------------------------------------------------------
    # RÉPARATIONS
    # --------------------------------------------------------

    reparations = (
        ReparationVehicule.objects.all()
    )

    total_reparations = sum(
        (
            r.montant_total
            for r in reparations
        ),
        Decimal("0"),
    )

    context = {
        "user": user,

        "materiaux": materiaux,
        "total_materiaux": materiaux.count(),

        "total_entrees": total_entrees,
        "total_divise": total_divise,
        "total_sorties": total_sorties,

        "stock_entrepot": stock_entrepot,
        "stock_magasin": stock_magasin,
        "stock_total": stock_total,

        "total_vehicules": total_vehicules,

        "total_activites_transport": (
            total_activites_transport
        ),
        "total_transport": total_transport,

        "total_gasoil": total_gasoil,

        "total_dockers": total_dockers,

        "total_depenses": total_depenses,

        "total_reparations": total_reparations,
    }

    return render(
        request,
        "materiaux/dashboard.html",
        context,
    )


# ============================================================
# MATÉRIAUX
# ============================================================

def materiaux_list(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    materiaux = (
        Materiaux.objects
        .all()
        .order_by("libelle")
    )

    return render(
        request,
        "materiaux/materiaux_list.html",
        {
            "user": user,
            "materiaux": materiaux,
        },
    )


def materiau_add(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    if request.method == "POST":

        form = MateriauxForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            materiau = form.save()

            messages.success(
                request,
                f"Le matériau « {materiau.libelle} » "
                "a été ajouté.",
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
            "title": "Ajouter un matériau",
        },
    )


# ============================================================
# COMPATIBILITÉ ANCIENNES URLS
# ============================================================

def materiaux_add(request):
    return materiau_add(request)


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
            request.FILES,
            instance=materiau,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Le matériau a été modifié avec succès.",
            )

            return redirect(
                "materiaux:materiaux_list"
            )

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


def materiaux_edit(request, pk):
    return materiau_edit(request, pk)


def materiau_delete(request, pk):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    materiau = get_object_or_404(
        Materiaux,
        pk=pk,
    )

    if request.method == "POST":

        if materiau.entrees.exists():

            messages.error(
                request,
                "Impossible de supprimer ce matériau "
                "car il possède des entrées enregistrées.",
            )

            return redirect(
                "materiaux:materiaux_list"
            )

        materiau.delete()

        messages.success(
            request,
            "Le matériau a été supprimé.",
        )

        return redirect(
            "materiaux:materiaux_list"
        )

    return render(
        request,
        "materiaux/materiaux_list.html",
        {
            "user": user,
            "materiaux": Materiaux.objects.all(),
            "delete_object": materiau,
        },
    )


def materiaux_delete(request, pk):
    return materiau_delete(request, pk)


# ============================================================
# ENTRÉES ENTREPÔT
# ============================================================

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
            "divisions",
        )
        .order_by(
            "-date_entree",
            "-id",
        )
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

            try:

                entree = form.save(
                    commit=False
                )

                entree.enregistreur = user

                entree.save()

                messages.success(
                    request,
                    "L'entrée en entrepôt "
                    "a été enregistrée.",
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

    if request.method == "POST":

        form = MateriauxEntreeForm(
            request.POST,
            instance=entree,
        )

        if form.is_valid():

            try:

                entree = form.save(
                    commit=False
                )

                # Conservation de l'enregistreur original.
                entree.enregistreur = (
                    entree.enregistreur
                )

                entree.save()

                messages.success(
                    request,
                    "L'entrée entrepôt "
                    "a été modifiée.",
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
            instance=entree
        )

    return render(
        request,
        "materiaux/entree_form.html",
        {
            "user": user,
            "form": form,
            "entree": entree,
            "title": "Modifier l'entrée entrepôt",
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
                "Impossible de supprimer cette entrée "
                "car elle possède déjà des divisions.",
            )

            return redirect(
                "materiaux:entrees_list"
            )

        entree.delete()

        messages.success(
            request,
            "L'entrée a été supprimée.",
        )

        return redirect(
            "materiaux:entrees_list"
        )

    return render(
        request,
        "materiaux/entrees_list.html",
        {
            "user": user,
            "entrees": MateriauxEntree.objects.all(),
            "delete_object": entree,
        },
    )


# ============================================================
# DIVISIONS ENTREPÔT → MAGASIN
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
        .prefetch_related(
            "sorties",
        )
        .order_by(
            "-date_division",
            "-id",
        )
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
                    "La division vers le magasin "
                    "a été enregistrée.",
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
                "Impossible de supprimer cette division "
                "car elle possède déjà des sorties.",
            )

            return redirect(
                "materiaux:divisions_list"
            )

        division.delete()

        messages.success(
            request,
            "La division a été supprimée.",
        )

        return redirect(
            "materiaux:divisions_list"
        )

    return render(
        request,
        "materiaux/divisions_list.html",
        {
            "user": user,
            "divisions": (
                MateriauxDivision.objects.all()
            ),
            "delete_object": division,
        },
    )


# ============================================================
# SORTIES MAGASIN
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
        .order_by(
            "-date_sortie",
            "-id",
        )
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

            try:

                sortie = form.save(
                    commit=False
                )

                sortie.enregistreur = user

                sortie.save()

                messages.success(
                    request,
                    "La sortie de matériau "
                    "a été enregistrée.",
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

            try:

                sortie = form.save(
                    commit=False
                )

                # Conservation de l'enregistreur original.
                sortie.enregistreur_id = (
                    sortie.enregistreur_id
                )

                sortie.save()

                messages.success(
                    request,
                    "La sortie de matériau "
                    "a été modifiée.",
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

        sortie.delete()

        messages.success(
            request,
            "La sortie a été supprimée.",
        )

        return redirect(
            "materiaux:sorties_list"
        )

    return render(
        request,
        "materiaux/sorties_list.html",
        {
            "user": user,
            "sorties": MateriauxOut.objects.all(),
            "delete_object": sortie,
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
        )
        .order_by(
            "immatriculation"
        )
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
                "Le véhicule a été ajouté.",
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

            form.save()

            messages.success(
                request,
                "Le véhicule a été modifié.",
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

        vehicule.delete()

        messages.success(
            request,
            "Le véhicule a été supprimé.",
        )

        return redirect(
            "materiaux:vehicules_list"
        )

    return render(
        request,
        "materiaux/vehicules_list.html",
        {
            "user": user,
            "vehicules": Vehicule.objects.all(),
            "delete_object": vehicule,
        },
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
            "materiau",
            "enregistreur",
        )
        .prefetch_related(
            "paiements_dockers",
            "depenses",
            "depenses_gasoil",
            "reparations",
        )
        .order_by(
            "-date_activite",
            "-id",
        )
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
                "L'activité de transport "
                "a été enregistrée.",
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
            "title": "Nouvelle activité de transport",
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

            form.save()

            messages.success(
                request,
                "L'activité de transport "
                "a été modifiée.",
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

    if request.method == "POST":

        activite.delete()

        messages.success(
            request,
            "L'activité de transport "
            "a été supprimée.",
        )

        return redirect(
            "materiaux:activites_transport_list"
        )

    return render(
        request,
        "materiaux/activites_transport_list.html",
        {
            "user": user,
            "activites": (
                ActiviteTransport.objects.all()
            ),
            "delete_object": activite,
        },
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
            "enregistreur",
        )
        .order_by(
            "-date_creation",
            "-id",
        )
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

            paiement = form.save(
                commit=False
            )

            paiement.enregistreur = user

            paiement.save()

            messages.success(
                request,
                "Le paiement docker "
                "a été enregistré.",
            )

            return redirect(
                "materiaux:paiements_dockers_list"
            )

    else:

        form = PaiementDockerForm()

    return render(
        request,
        "materiaux/paiement_docker_form.html",
        {
            "user": user,
            "form": form,
            "title": "Nouveau paiement docker",
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

            form.save()

            messages.success(
                request,
                "Le paiement docker "
                "a été modifié.",
            )

            return redirect(
                "materiaux:paiements_dockers_list"
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

        paiement.delete()

        messages.success(
            request,
            "Le paiement docker "
            "a été supprimé.",
        )

        return redirect(
            "materiaux:paiements_dockers_list"
        )

    return render(
        request,
        "materiaux/paiements_dockers_list.html",
        {
            "user": user,
            "paiements": (
                PaiementDocker.objects.all()
            ),
            "delete_object": paiement,
        },
    )


# ============================================================
# CATÉGORIES DE DÉPENSES
# ============================================================

def categories_depenses_list(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    categories = (
        CategorieDepense.objects
        .order_by("nom")
    )

    return render(
        request,
        "materiaux/categories_depenses_list.html",
        {
            "user": user,
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
                "La catégorie de dépense "
                "a été ajoutée.",
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
            "title": "Nouvelle catégorie de dépense",
        },
    )


def categorie_depense_edit(request, pk=None):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    if pk is None:

        pk = (
            request.POST.get("pk")
            or request.GET.get("pk")
        )

    if not pk:

        messages.error(
            request,
            "Aucune catégorie de dépense "
            "n'a été sélectionnée.",
        )

        return redirect(
            "materiaux:categories_depenses_list"
        )

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
                "La catégorie a été modifiée.",
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
            "categorie": categorie,
            "title": "Modifier la catégorie",
        },
    )


def categorie_depense_delete(request, pk=None):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    if pk is None:

        pk = (
            request.POST.get("pk")
            or request.GET.get("pk")
        )

    if not pk:

        messages.error(
            request,
            "Aucune catégorie de dépense "
            "n'a été sélectionnée.",
        )

        return redirect(
            "materiaux:categories_depenses_list"
        )

    categorie = get_object_or_404(
        CategorieDepense,
        pk=pk,
    )

    if request.method == "POST":

        if categorie.depenses.exists():

            messages.error(
                request,
                "Impossible de supprimer cette catégorie "
                "car elle est utilisée par des dépenses.",
            )

            return redirect(
                "materiaux:categories_depenses_list"
            )

        categorie.delete()

        messages.success(
            request,
            "La catégorie a été supprimée.",
        )

        return redirect(
            "materiaux:categories_depenses_list"
        )

    return render(
        request,
        "materiaux/categories_depenses_list.html",
        {
            "user": user,
            "categories": (
                CategorieDepense.objects.all()
            ),
            "delete_object": categorie,
        },
    )


# ============================================================
# DÉPENSES GÉNÉRALES
# ============================================================

def depenses_list(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    depenses = (
        Depense.objects
        .select_related(
            "enregistreur",
        )
        .order_by(
            "-date_depense",
            "-id",
        )
    )

    total = sum(
        (
            d.montant or Decimal("0")
            for d in depenses
        ),
        Decimal("0"),
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
                "La dépense a été enregistrée.",
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
            "title": "Nouvelle dépense",
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

            form.save()

            messages.success(
                request,
                "La dépense a été modifiée.",
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

        depense.delete()

        messages.success(
            request,
            "La dépense a été supprimée.",
        )

        return redirect(
            "materiaux:depenses_list"
        )

    return render(
        request,
        "materiaux/depenses_list.html",
        {
            "user": user,
            "depenses": Depense.objects.all(),
            "delete_object": depense,
        },
    )


# ============================================================
# GASOIL
# ============================================================

def gasoil_list(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    gasoils = (
        DepenseGasoil.objects
        .select_related(
            "vehicule",
            "enregistreur",
        )
        .order_by(
            "-date_gasoil",
            "-id",
        )
    )

    total_litres = sum(
        (
            gasoil.quantite_litre or Decimal("0")
            for gasoil in gasoils
        ),
        Decimal("0"),
    )

    return render(
        request,
        "materiaux/gasoil_list.html",
        {
            "user": user,
            "gasoils": gasoils,
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

            gasoil = form.save(
                commit=False
            )

            gasoil.enregistreur = user

            gasoil.save()

            messages.success(
                request,
                "La dépense de gasoil "
                "a été enregistrée.",
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
            "title": "Nouvelle dépense gasoil",
        },
    )


def gasoil_edit(request, pk):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    gasoil = get_object_or_404(
        DepenseGasoil,
        pk=pk,
    )

    if request.method == "POST":

        form = DepenseGasoilForm(
            request.POST,
            instance=gasoil,
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                "La dépense de gasoil "
                "a été modifiée.",
            )

            return redirect(
                "materiaux:gasoil_list"
            )

    else:

        form = DepenseGasoilForm(
            instance=gasoil
        )

    return render(
        request,
        "materiaux/gasoil_form.html",
        {
            "user": user,
            "form": form,
            "gasoil": gasoil,
            "title": "Modifier la dépense gasoil",
        },
    )


def gasoil_delete(request, pk):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    gasoil = get_object_or_404(
        DepenseGasoil,
        pk=pk,
    )

    if request.method == "POST":

        gasoil.delete()

        messages.success(
            request,
            "La dépense de gasoil "
            "a été supprimée.",
        )

        return redirect(
            "materiaux:gasoil_list"
        )

    return render(
        request,
        "materiaux/gasoil_list.html",
        {
            "user": user,
            "gasoils": DepenseGasoil.objects.all(),
            "delete_object": gasoil,
        },
    )


# ============================================================
# RÉPARATIONS / ENTRETIEN
# ============================================================

def reparations_list(request):
    user = check_user(request)
    if not isinstance(user, AppUser):
        return user

    reparations = list(
        ReparationVehicule.objects
        .select_related("vehicule", "enregistreur")
        .order_by("-date_reparation", "-id")
    )

    total_pieces = sum(
        (
            (reparation.quantite or Decimal("0"))
            * (reparation.prix_unitaire or Decimal("0"))
            for reparation in reparations
        ),
        Decimal("0"),
    )

    total_main_oeuvre = sum(
        (
            reparation.montant_main_oeuvre or Decimal("0")
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

        # request.FILES est nécessaire
        # pour les photos des pièces.
        form = ReparationVehiculeForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():

            try:

                reparation = form.save(
                    commit=False
                )

                reparation.enregistreur = user

                reparation.save()

                messages.success(
                    request,
                    "La réparation / entretien "
                    "a été enregistrée avec succès.",
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
            "title": "Nouvelle réparation / entretien",
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

    # --------------------------------------------------------
    # SEUL L'ENREGISTREUR PEUT MODIFIER
    # --------------------------------------------------------

    if reparation.enregistreur_id != user.id:

        messages.error(
            request,
            "Vous n'êtes pas autorisé "
            "à modifier cet entretien.",
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

            try:

                objet = form.save(
                    commit=False
                )

                # Conservation de l'enregistreur original.
                objet.enregistreur_id = (
                    reparation.enregistreur_id
                )

                objet.save()

                messages.success(
                    request,
                    "La réparation / entretien "
                    "a été modifiée avec succès.",
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
            "title": "Modifier la réparation / entretien",
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

    # --------------------------------------------------------
    # SEUL L'ENREGISTREUR PEUT SUPPRIMER
    # --------------------------------------------------------

    if reparation.enregistreur_id != user.id:

        messages.error(
            request,
            "Vous n'êtes pas autorisé "
            "à supprimer cet entretien.",
        )

        return redirect(
            "materiaux:reparations_list"
        )

    if request.method == "POST":

        reparation.delete()

        messages.success(
            request,
            "La réparation / entretien "
            "a été supprimée.",
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


# ============================================================
# STOCK ENTREPÔT
# ============================================================

def stock_entrepot(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    materiaux = (
        Materiaux.objects
        .all()
        .order_by("libelle")
    )

    total_general = Decimal("0")

    for materiau in materiaux:

        total_general += (
            materiau.stock_entrepot
            or Decimal("0")
        )

    return render(
        request,
        "materiaux/stock_entrepot.html",
        {
            "user": user,
            "materiaux": materiaux,
            "total_general": total_general,
        },
    )


# ============================================================
# STOCK MAGASIN
# ============================================================

def stock_magasin(request):

    user = check_user(request)

    if not isinstance(user, AppUser):
        return user

    materiaux = (
        Materiaux.objects
        .all()
        .order_by("libelle")
    )

    total_general = Decimal("0")

    for materiau in materiaux:

        total_general += (
            materiau.stock_magasin
            or Decimal("0")
        )

    return render(
        request,
        "materiaux/stock_magasin.html",
        {
            "user": user,
            "materiaux": materiaux,
            "total_general": total_general,
        },
    )