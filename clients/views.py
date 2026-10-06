from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from functools import wraps
from .models import Client
from .forms import ClientForm

from audit.utils import enregistrer_action
from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages

from .models import Client
from .forms import ClientForm

from audit.utils import enregistrer_action

# ============================================================

# UTILISATEUR CONNECTÉ

# ============================================================

def get_current_user(request):
    user_id = request.session.get("user_id")

    if not user_id:
        return None

    return (
        AppUser.objects
        .select_related("personnel")
        .filter(pk=user_id)
        .first()
    )


# ============================================================

# AUTHENTIFICATION

# ============================================================

def login_required_projet(view_func):
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        user = get_current_user(request)

        if not user:
            return redirect("users:login")

        request.current_user = user

        return view_func(request, *args, **kwargs)

    return wrapper

# ============================================================

# DROITS DE GESTION DES PROJETS

# ============================================================

def user_can_manage_projects(user):
    if not user:
        return False

    return user.role in {
        "Admin",
        "Superviseur",
        "UserMica",
    }


def project_manager_required(view_func):
    @wraps(view_func)
    @login_required_projet
    def wrapper(request, *args, **kwargs):

        if not user_can_manage_projects(request.current_user):
            messages.error(
                request,
                "Vous n'avez pas l'autorisation de gérer les projets."
            )
            return redirect("projet:projet_list")

        return view_func(request, *args, **kwargs)

    return wrapper


# ============================================================

# PERSONNEL DE L'UTILISATEUR

# ============================================================

def get_current_personnel(request):
    user = getattr(request,"current_user",None,)

    if not user:
        return None

    return getattr(
        user,
        "personnel",
        None,
    )


# ============================================================

# VÉRIFICATION D'ACCÈS À UN PROJET

# ============================================================

def user_has_project_access(user, projet):

    if not user:
        return False

    if user_can_manage_projects(user):
        return True

    personnel = getattr(
        user,
        "personnel",
        None,
    )

    if not personnel:
        return False

    aujourd_hui = timezone.localdate()

    return EquipeProjet.objects.filter(
        projet=projet,
        personnel=personnel,
        actif=True,
        date_debut__lte=aujourd_hui,
        date_fin__gte=aujourd_hui,
    ).exists()


# =========================================================
# LISTE
# =========================================================
# @project_manager_required
def client_list(request):

    queryset = Client.objects.all().order_by("nom", "prenom")

    nom = request.GET.get("nom", "").strip()
    prenom = request.GET.get("prenom", "").strip()
    contact = request.GET.get("contact", "").strip()

    if nom:
        queryset = queryset.filter(
            nom__icontains=nom
        )

    if prenom:
        queryset = queryset.filter(
            prenom__icontains=prenom
        )

    if contact:
        queryset = queryset.filter(
            contact__icontains=contact
        )

    paginator = Paginator(
        queryset,
        12
    )

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    query_params = request.GET.copy()

    query_params.pop(
        "page",
        None
    )

    return render(
        request,
        "clients/list.html",
        {
            "clients": page_obj.object_list,
            "page_obj": page_obj,
            "query_params": query_params.urlencode(),
            "nom": nom,
            "prenom": prenom,
            "contact": contact,
        }
    )


# =========================================================
# AJOUT CLIENT
# =========================================================

def client_add(request):

    form = ClientForm(
        request.POST or None,
        request.FILES or None
    )

    if request.method == "POST" and form.is_valid():

        # -------------------------------------------------
        # Récupérer l'utilisateur connecté
        # -------------------------------------------------
        user_id = request.session.get("user_id")

        # Sécurité : vérifier qu'un utilisateur est connecté
        if not user_id:
            messages.error(
                request,
                "Votre session a expiré. Veuillez vous reconnecter."
            )
            return redirect("users:login")

        # -------------------------------------------------
        # Enregistrer le client
        # -------------------------------------------------
        client = form.save(commit=False)

        # Enregistrer l'utilisateur qui a créé le client
        client.enregistre_par_id = user_id

        client.save()

        # -------------------------------------------------
        # Données pour l'audit
        # -------------------------------------------------
        nouvelle = {
            "id": client.id,
            "nom": client.nom,
            "prenom": client.prenom,
            "date_naissance": (
                client.date_naissance.isoformat()
                if client.date_naissance
                else None
            ),
            "lieu_naissance": client.lieu_naissance,
            "cin": client.cin,
            "nom_pere": client.nom_pere,
            "nom_mere": client.nom_mere,
            "contact": client.contact,
            "adresse": client.adresse,
            "photo": (
                client.photo.name
                if client.photo
                else None
            ),
            "enregistre_par": user_id,
        }

        # -------------------------------------------------
        # AUDIT
        # -------------------------------------------------
        enregistrer_action(
            request,
            action="CREATE",
            table="Client",
            objet_id=client.id,
            ancienne=None,
            nouvelle=nouvelle,
            description=(
                f"Création du client "
                f"{client.nom} {client.prenom}"
            )
        )

        # -------------------------------------------------
        # Message de succès
        # -------------------------------------------------
        messages.success(
            request,
            f"Le client « {client.nom} {client.prenom} » "
            "a été ajouté avec succès."
        )

        # -------------------------------------------------
        # Retour à la liste
        # -------------------------------------------------
        return redirect("clients:client_list")

    # -----------------------------------------------------
    # Affichage du formulaire
    # -----------------------------------------------------
    return render(
        request,
        "clients/form.html",
        {
            "form": form
        }
    )


# =========================================================
# DETAIL
# =========================================================

def client_detail(request, id):

    client = get_object_or_404(
        Client,
        id=id
    )

    return render(
        request,
        "clients/detail.html",
        {
            "client": client
        }
    )


# =========================================================
# MODIFICATION
# =========================================================

def client_edit(request, id):

    client = get_object_or_404(
        Client,
        id=id
    )

    ancienne = {
        "id": client.id,
        "nom": client.nom,
        "prenom": client.prenom,
        "date_naissance": (
            client.date_naissance.isoformat()
            if client.date_naissance
            else None
        ),
        "lieu_naissance": client.lieu_naissance,
        "cin": client.cin,
        "nom_pere": client.nom_pere,
        "nom_mere": client.nom_mere,
        "contact": client.contact,
        "adresse": client.adresse,
        "photo": (
            client.photo.name
            if client.photo
            else None
        ),
    }

    form = ClientForm(
        request.POST or None,
        request.FILES or None,
        instance=client
    )

    if request.method == "POST" and form.is_valid():

        client = form.save()

        nouvelle = {
            "id": client.id,
            "nom": client.nom,
            "prenom": client.prenom,
            "date_naissance": (
                client.date_naissance.isoformat()
                if client.date_naissance
                else None
            ),
            "lieu_naissance": client.lieu_naissance,
            "cin": client.cin,
            "nom_pere": client.nom_pere,
            "nom_mere": client.nom_mere,
            "contact": client.contact,
            "adresse": client.adresse,
            "photo": (
                client.photo.name
                if client.photo
                else None
            ),
        }

        enregistrer_action(
            request,
            action="UPDATE",
            table="Client",
            objet_id=client.id,
            ancienne=ancienne,
            nouvelle=nouvelle,
            description="Modification d'un client"
        )

        messages.success(
            request,
            f"Le client « {client.nom} {client.prenom} » "
            "a été modifié avec succès."
        )

        return redirect(
            "clients:client_list"
        )

    return render(
        request,
        "clients/form.html",
        {
            "form": form
        }
    )


# =========================================================
# SUPPRESSION CLIENT + PHOTO
# =========================================================

def client_delete(request, id):

    # -----------------------------------------------------
    # Récupérer le client
    # -----------------------------------------------------

    client = get_object_or_404(
        Client,
        id=id
    )

    # -----------------------------------------------------
    # Vérifier l'utilisateur connecté
    # -----------------------------------------------------

    user_id = request.session.get("user_id")

    if not user_id:

        messages.error(
            request,
            "Votre session a expiré. Veuillez vous reconnecter."
        )

        return redirect(
            "users:login"
        )

    # -----------------------------------------------------
    # Vérifier que l'utilisateur est le créateur
    # -----------------------------------------------------

    if str(client.enregistre_par_id) != str(user_id):

        messages.error(
            request,
            "Vous n'êtes pas autorisé à supprimer ce client."
        )

        return redirect(
            "clients:client_list"
        )

    # =====================================================
    # SUPPRESSION
    # =====================================================

    if request.method == "POST":

        # -------------------------------------------------
        # Données avant suppression pour l'audit
        # -------------------------------------------------

        ancienne = {
            "id": client.id,

            "nom": client.nom,

            "prenom": client.prenom,

            "date_naissance": (
                client.date_naissance.isoformat()
                if client.date_naissance
                else None
            ),

            "lieu_naissance": client.lieu_naissance,

            "cin": client.cin,

            "nom_pere": client.nom_pere,

            "nom_mere": client.nom_mere,

            "contact": client.contact,

            "adresse": client.adresse,

            "photo": (
                client.photo.name
                if client.photo
                else None
            ),
        }

        # -------------------------------------------------
        # Nom du client
        # -------------------------------------------------

        nom_client = (
            f"{client.nom} {client.prenom}"
        ).strip()

        client_id = client.id

        # -------------------------------------------------
        # Conserver la référence de la photo AVANT
        # de supprimer le client
        # -------------------------------------------------

        photo = client.photo

        # -------------------------------------------------
        # Audit
        # -------------------------------------------------

        enregistrer_action(
            request,
            action="DELETE",
            table="Client",
            objet_id=client_id,
            ancienne=ancienne,
            nouvelle=None,
            description=(
                f"Suppression du client {nom_client}"
            )
        )

        # -------------------------------------------------
        # Supprimer le client de la base
        # -------------------------------------------------

        client.delete()

        # -------------------------------------------------
        # Supprimer physiquement la photo
        # -------------------------------------------------

        if photo:

            try:

                photo.delete(
                    save=False
                )

            except Exception:

                # Ne pas bloquer la suppression du client
                # si la suppression du fichier échoue.
                pass

        # -------------------------------------------------
        # Message de succès
        # -------------------------------------------------

        messages.success(
            request,
            f"Le client « {nom_client} » "
            "et sa photo ont été supprimés avec succès."
        )

        # -------------------------------------------------
        # Retour à la liste
        # -------------------------------------------------

        return redirect(
            "clients:client_list"
        )

    # =====================================================
    # AFFICHAGE DE LA CONFIRMATION
    # =====================================================

    return render(
        request,
        "clients/confirm_delete.html",
        {
            "client": client
        }
    )
