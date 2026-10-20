from functools import wraps
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models import Sum, Q
from django.http import HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_http_methods

from users.models import H_AppUser
from .models import (
    Materiaux, MateriauxEntree, MateriauxDivision, MateriauxOut, Vehicule,
    CategorieDepense, ActiviteTransport, ReceptionMateriau,
    UtilisationMateriau, MateriauxRetour, PaiementDocker, Depense,
    DepenseGasoil, ReparationVehicule,
)
from .forms import (
    MateriauxForm, MateriauxEntreeForm, MateriauxDivisionForm,
    MateriauxOutForm, VehiculeForm, CategorieDepenseForm,
    ActiviteTransportForm, ReceptionMateriauForm, UtilisationMateriauForm,
    MateriauxRetourForm, PaiementDockerForm, DepenseForm,
    DepenseGasoilForm, ReparationVehiculeForm,
)

ENTREPRISE = "MCCR"


def mccr_required(view_func):
    """Authentification propre à l'espace MCCR (session h_user_id)."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        user_id = request.session.get("h_user_id")
        if not user_id:
            messages.warning(request, "Veuillez vous connecter à votre espace MCCR.")
            return redirect("users:h_login")
        try:
            request.h_current_user = H_AppUser.objects.get(pk=user_id)
        except H_AppUser.DoesNotExist:
            request.session.flush()
            messages.error(request, "Session MCCR invalide. Veuillez vous reconnecter.")
            return redirect("users:h_login")
        return view_func(request, *args, **kwargs)
    return wrapper


def _qs(model):
    qs = model.objects.all()
    if any(f.name == "entreprise" for f in model._meta.fields):
        qs = qs.filter(entreprise=ENTREPRISE)
    return qs

def _form_save(request, form):
    """
    Enregistre les données dans l'espace MCCR.
    Associe l'utilisateur H_AppUser si le modèle possède
    un champ enregistreur compatible.
    """
    obj = form.save(commit=False)

    # À utiliser uniquement si le modèle possède ce champ.
    if hasattr(obj, "entreprise"):
        obj.entreprise = ENTREPRISE

    # Les anciens modèles utilisent le champ « enregistreur ».
    if hasattr(obj, "enregistreur_id"):
        if not obj.enregistreur_id:
            obj.enregistreur = request.h_current_user

    # Compatibilité si certains modèles utilisent ce nom.
    elif hasattr(obj, "enregistreur_mccr_id"):
        if not obj.enregistreur_mccr_id:
            obj.enregistreur_mccr = request.h_current_user

    obj.full_clean()
    obj.save()
    form.save_m2m()

    return obj



def _crud_list(request, model, template, context_name, title):
    qs = _qs(model)
    q = request.GET.get("q", "").strip()
    if q:
        searchable = [f.name for f in model._meta.fields if getattr(f, "get_internal_type", lambda: "")() in ("CharField", "TextField")]
        query = Q()
        for field in searchable:
            query |= Q(**{f"{field}__icontains": q})
        if searchable:
            qs = qs.filter(query)
    return render(request, template, {context_name: qs, "objets": qs, "q": q, "titre": title})


def _crud_form(request, model, form_class, template, list_url_name, pk=None, title=""):
    instance = get_object_or_404(_qs(model), pk=pk) if pk is not None else None
    if request.method == "POST":
        form = form_class(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            try:
                _form_save(request, form)
            except Exception as exc:
                # Les ValidationError du modèle sont présentées comme erreur de formulaire.
                from django.core.exceptions import ValidationError
                if isinstance(exc, ValidationError):
                    form.add_error(None, exc)
                else:
                    raise
            else:
                messages.success(request, "Enregistrement MCCR effectué avec succès.")
                return redirect(f"materiaux:{list_url_name}")
    else:
        form = form_class(instance=instance)
    return render(request, template, {"form": form, "objet": instance, "titre": title, "is_update": instance is not None})


def _crud_delete(request, model, pk, list_url_name, label):
    obj = get_object_or_404(_qs(model), pk=pk)
    if request.method == "POST":
        try:
            obj.delete()
            messages.success(request, f"{label} supprimé avec succès.")
        except Exception as exc:
            messages.error(request, f"Suppression impossible : {exc}")
        return redirect(f"materiaux:{list_url_name}")
    return render(request, "materiaux/confirm_delete.html", {"objet": obj, "object": obj, "titre": f"Supprimer {label.lower()}"})



@mccr_required
def dashboard(request):
    context = {
        "total_materiaux": _qs(Materiaux).count(),
        "total_entrees": _qs(MateriauxEntree).count(),
        "total_divisions": _qs(MateriauxDivision).count(),
        "total_sorties": _qs(MateriauxOut).count(),
        "total_vehicules": _qs(Vehicule).count(),
        "total_depenses": _qs(Depense).aggregate(total=Sum("montant"))["total"] or Decimal("0"),
        "total_gasoil": _qs(DepenseGasoil).aggregate(total=Sum("total"))["total"] or Decimal("0"),
        "total_reparations": _qs(ReparationVehicule).aggregate(total=Sum("total"))["total"] or Decimal("0"),
        "total_paiements_dockers": _qs(PaiementDocker).aggregate(total=Sum("montant"))["total"] or Decimal("0"),
    }
    return render(request, "materiaux/dashboard.html", context)


@mccr_required
def dashboard_alt(request):
    return dashboard(request)


# CRUD déclarés explicitement pour préserver les noms d'URL déjà utilisés par les templates.
def _make_list(model, template, context, title):
    @mccr_required
    def view(request):
        return _crud_list(request, model, template, context, title)
    return view

def _make_add(model, form, template, list_name, title):
    @mccr_required
    def view(request):
        return _crud_form(request, model, form, template, list_name, title=title)
    return view

def _make_edit(model, form, template, list_name, title):
    @mccr_required
    def view(request, pk):
        return _crud_form(request, model, form, template, list_name, pk=pk, title=title)
    return view

def _make_delete(model, list_name, label):
    @mccr_required
    def view(request, pk):
        return _crud_delete(request, model, pk, list_name, label)
    return view


materiaux_list = _make_list(Materiaux, "materiaux/materiaux_list.html", "materiaux", "Matériaux MCCR")
materiau_add = _make_add(Materiaux, MateriauxForm, "materiaux/materiaux_form.html", "materiaux_list", "Ajouter un matériau")
materiau_edit = _make_edit(Materiaux, MateriauxForm, "materiaux/materiaux_form.html", "materiaux_list", "Modifier le matériau")
materiau_delete = _make_delete(Materiaux, "materiaux_list", "matériau")

entrees_list = _make_list(MateriauxEntree, "materiaux/entrees_list.html", "entrees", "Entrées entrepôt MCCR")
entree_add = _make_add(MateriauxEntree, MateriauxEntreeForm, "materiaux/entree_form.html", "entrees_list", "Ajouter une entrée")
entree_edit = _make_edit(MateriauxEntree, MateriauxEntreeForm, "materiaux/entree_form.html", "entrees_list", "Modifier une entrée")
entree_delete = _make_delete(MateriauxEntree, "entrees_list", "entrée")

divisions_list = _make_list(MateriauxDivision, "materiaux/divisions_list.html", "divisions", "Divisions entrepôt-magasin MCCR")
division_add = _make_add(MateriauxDivision, MateriauxDivisionForm, "materiaux/division_form.html", "divisions_list", "Ajouter une division")
division_edit = _make_edit(MateriauxDivision, MateriauxDivisionForm, "materiaux/division_form.html", "divisions_list", "Modifier une division")
division_delete = _make_delete(MateriauxDivision, "divisions_list", "division")

sorties_list = _make_list(MateriauxOut, "materiaux/sorties_list.html", "sorties", "Sorties magasin MCCR")
sortie_add = _make_add(MateriauxOut, MateriauxOutForm, "materiaux/sortie_form.html", "sorties_list", "Ajouter une sortie")
sortie_edit = _make_edit(MateriauxOut, MateriauxOutForm, "materiaux/sortie_form.html", "sorties_list", "Modifier une sortie")
sortie_delete = _make_delete(MateriauxOut, "sorties_list", "sortie")

vehicules_list = _make_list(Vehicule, "materiaux/vehicules_list.html", "vehicules", "Véhicules MCCR")
vehicule_add = _make_add(Vehicule, VehiculeForm, "materiaux/vehicule_form.html", "vehicules_list", "Ajouter un véhicule")
vehicule_edit = _make_edit(Vehicule, VehiculeForm, "materiaux/vehicule_form.html", "vehicules_list", "Modifier un véhicule")
vehicule_delete = _make_delete(Vehicule, "vehicules_list", "véhicule")

categories_depenses_list = _make_list(CategorieDepense, "materiaux/categories_depenses_list.html", "categories", "Catégories de dépenses MCCR")
categorie_depense_add = _make_add(CategorieDepense, CategorieDepenseForm, "materiaux/categorie_depense_form.html", "categories_depenses_list", "Ajouter une catégorie")
categorie_depense_edit = _make_edit(CategorieDepense, CategorieDepenseForm, "materiaux/categorie_depense_form.html", "categories_depenses_list", "Modifier une catégorie")
categorie_depense_delete = _make_delete(CategorieDepense, "categories_depenses_list", "catégorie")

activites_transport_list = _make_list(ActiviteTransport, "materiaux/activites_transport_list.html", "activites", "Activités de transport MCCR")
activite_transport_add = _make_add(ActiviteTransport, ActiviteTransportForm, "materiaux/activite_transport_form.html", "activites_transport_list", "Ajouter une activité de transport")
activite_transport_edit = _make_edit(ActiviteTransport, ActiviteTransportForm, "materiaux/activite_transport_form.html", "activites_transport_list", "Modifier une activité de transport")
activite_transport_delete = _make_delete(ActiviteTransport, "activites_transport_list", "activité de transport")

paiements_dockers_list = _make_list(PaiementDocker, "materiaux/paiements_dockers_list.html", "paiements", "Paiements dockers MCCR")
paiement_docker_add = _make_add(PaiementDocker, PaiementDockerForm, "materiaux/paiement_docker_form.html", "paiements_dockers_list", "Ajouter un paiement docker")
paiement_docker_edit = _make_edit(PaiementDocker, PaiementDockerForm, "materiaux/paiement_docker_form.html", "paiements_dockers_list", "Modifier un paiement docker")
paiement_docker_delete = _make_delete(PaiementDocker, "paiements_dockers_list", "paiement docker")

depenses_list = _make_list(Depense, "materiaux/depenses_list.html", "depenses", "Dépenses MCCR")
depense_add = _make_add(Depense, DepenseForm, "materiaux/depense_form.html", "depenses_list", "Ajouter une dépense")
depense_edit = _make_edit(Depense, DepenseForm, "materiaux/depense_form.html", "depenses_list", "Modifier une dépense")
depense_delete = _make_delete(Depense, "depenses_list", "dépense")

depenses_gasoil_list = _make_list(DepenseGasoil, "materiaux/gasoil_list.html", "depenses_gasoil", "Dépenses gasoil MCCR")
depense_gasoil_add = _make_add(DepenseGasoil, DepenseGasoilForm, "materiaux/gasoil_form.html", "depenses_gasoil_list", "Ajouter une dépense gasoil")
depense_gasoil_edit = _make_edit(DepenseGasoil, DepenseGasoilForm, "materiaux/gasoil_form.html", "depenses_gasoil_list", "Modifier une dépense gasoil")
depense_gasoil_delete = _make_delete(DepenseGasoil, "depenses_gasoil_list", "dépense gasoil")

reparations_list = _make_list(ReparationVehicule, "materiaux/reparations_list.html", "reparations", "Réparations véhicules MCCR")
reparation_add = _make_add(ReparationVehicule, ReparationVehiculeForm, "materiaux/reparation_form.html", "reparations_list", "Ajouter une réparation")
reparation_edit = _make_edit(ReparationVehicule, ReparationVehiculeForm, "materiaux/reparation_form.html", "reparations_list", "Modifier une réparation")
reparation_delete = _make_delete(ReparationVehicule, "reparations_list", "réparation")

receptions_materiaux_list = _make_list(ReceptionMateriau, "materiaux/receptions_materiaux_list.html", "receptions", "Réceptions matériaux MCCR")
reception_materiau_add = _make_add(ReceptionMateriau, ReceptionMateriauForm, "materiaux/suivi_materiau_form.html", "receptions_materiaux_list", "Ajouter une réception")
reception_materiau_edit = _make_edit(ReceptionMateriau, ReceptionMateriauForm, "materiaux/suivi_materiau_form.html", "receptions_materiaux_list", "Modifier une réception")

utilisations_materiaux_list = _make_list(UtilisationMateriau, "materiaux/utilisations_materiaux_list.html", "utilisations", "Utilisations matériaux MCCR")
utilisation_materiau_add = _make_add(UtilisationMateriau, UtilisationMateriauForm, "materiaux/suivi_materiau_form.html", "utilisations_materiaux_list", "Ajouter une utilisation")
utilisation_materiau_edit = _make_edit(UtilisationMateriau, UtilisationMateriauForm, "materiaux/suivi_materiau_form.html", "utilisations_materiaux_list", "Modifier une utilisation")
utilisation_materiau_delete = _make_delete(UtilisationMateriau, "utilisations_materiaux_list", "utilisation")

retours_materiaux_list = _make_list(MateriauxRetour, "materiaux/retours_materiaux_list.html", "retours", "Retours matériaux MCCR")
retour_materiau_add = _make_add(MateriauxRetour, MateriauxRetourForm, "materiaux/suivi_materiau_form.html", "retours_materiaux_list", "Ajouter un retour")
retour_materiau_edit = _make_edit(MateriauxRetour, MateriauxRetourForm, "materiaux/suivi_materiau_form.html", "retours_materiaux_list", "Modifier un retour")
retour_materiau_delete = _make_delete(MateriauxRetour, "retours_materiaux_list", "retour")


@mccr_required
def stock_entrepot(request):
    return render(request, "materiaux/stock_entrepot.html", {"materiaux": _qs(Materiaux), "entrees": _qs(MateriauxEntree), "titre": "Stock entrepôt MCCR"})


@mccr_required
def stock_magasin(request):
    divisions = _qs(MateriauxDivision).select_related("entree", "entree__materiau")
    return render(request, "materiaux/stock_magasin.html", {"divisions": divisions, "materiaux": _qs(Materiaux), "titre": "Stock magasin MCCR"})
