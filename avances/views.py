from django.contrib import messages
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q,Sum
from django.db import transaction
from django.shortcuts import get_object_or_404
from .forms import H_AvanceForm
from .models import H_Avance
from django.shortcuts import get_object_or_404, redirect, render
from audit.utils import enregistrer_action
from personnel.models import Personnel, H_Personnel
from users.models import AppUser, H_AppUser
from salaire.models import H_Salaire, Salaire
from salaire.forms import H_SalaireForm,SalaireForm
from .forms import AvanceForm, H_AvanceForm
from .models import Avance, H_Avance
from users.decorators import session_login_required
# =========================================================
# OUTIL : QUERYSET PERSONNEL SELON LE RÃ”LE
# =========================================================
def get_personnel_queryset_for_role(role):

    queryset = (
        Personnel.objects.select_related("categorie").all().order_by("nom", "prenom")
    )

    # -----------------------------------------------------
    # USER MICA
    # -----------------------------------------------------

    if role == "UserMica":

        return queryset.filter(typeTravail="Mica")

    # -----------------------------------------------------
    # USER ENTREPRISE
    # -----------------------------------------------------

    elif role == "UserEntreprise":

        return queryset.filter(typeTravail="Construction")

    # -----------------------------------------------------
    # ADMIN / SUPERADMIN / SUPERVISEUR
    # -----------------------------------------------------

    elif role in ["Admin", "SuperAdmin", "Superviseur"]:

        return queryset

    # -----------------------------------------------------
    # AUTRE / RÃ”LE INVALIDE
    # -----------------------------------------------------

    return Personnel.objects.none()


# =========================================================
# OUTIL : QUERYSET AVANCE SELON LE RÃ”LE
# =========================================================
def get_avance_queryset_for_role(role):

    queryset = (
        Avance.objects.select_related("personnel", "distribution", "enregistre_par")
        .all()
        .order_by("-dateAv")
    )

    # -----------------------------------------------------
    # USER MICA
    # -----------------------------------------------------

    if role == "UserMica":

        return queryset.filter(personnel__typeTravail="Mica")

    # -----------------------------------------------------
    # USER ENTREPRISE
    # -----------------------------------------------------

    elif role == "UserEntreprise":

        return queryset.filter(personnel__typeTravail="Construction")

    # -----------------------------------------------------
    # ADMIN / SUPERADMIN / SUPERVISEUR
    # -----------------------------------------------------

    elif role in ["Admin", "SuperAdmin", "Superviseur"]:

        return queryset

    # -----------------------------------------------------
    # AUTRE / RÃ”LE INVALIDE
    # -----------------------------------------------------

    return Avance.objects.none()


# =========================================================
# AJOUT
# =========================================================
@session_login_required
def avance_add(request):

    # -----------------------------------------------------
    # RÃ”LE DE L'UTILISATEUR
    # -----------------------------------------------------

    role = request.session.get("role")

    # -----------------------------------------------------
    # VÃ‰RIFICATION SESSION
    # -----------------------------------------------------

    if not request.session.get("user_id"):

        messages.error(request, "Votre session a expiré. Veuillez vous reconnecter.")

        return redirect("users:login")

    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    if request.method == "POST":

        form = AvanceForm(request.POST, role=role)

        if form.is_valid():

            avance = form.save(commit=False)

            # -------------------------------------------------
            # SÃ‰CURITÃ‰ : VÃ‰RIFIER LE PERSONNEL
            # -------------------------------------------------

            personnel = avance.personnel

            personnel_queryset = get_personnel_queryset_for_role(role)

            if not personnel_queryset.filter(id=personnel.id).exists():

                messages.error(
                    request,
                    "Vous n'étes pas autorisé à enregistrer "
                    "une avance pour ce personnel.",
                )

                return redirect("avances:avance_list")

            # -------------------------------------------------
            # UTILISATEUR CONNECTÃ‰
            # -------------------------------------------------

            user_id = request.session.get("user_id")

            if user_id:

                try:

                    avance.enregistre_par = AppUser.objects.get(id=user_id)

                except AppUser.DoesNotExist:

                    avance.enregistre_par = None

            # -------------------------------------------------
            # ENREGISTREMENT
            # -------------------------------------------------

            avance.save()

            if avance.personnel:
                recalculer_situation_personnel(avance.personnel)

            # -------------------------------------------------
            # AUDIT
            # -------------------------------------------------

            enregistrer_action(
                request,
                "CREATE",
                "Avance",
                avance.id,
                nouvelle={
                    "personnel": str(avance.personnel),
                    "montant": str(avance.montantAv),
                    "motif": avance.motifAv,
                    "type": avance.typeAv,
                },
                description=("CrÃ©ation d'une avance personnel"),
            )

            # -------------------------------------------------
            # MESSAGE
            # -------------------------------------------------

            messages.success(request, "Avance enregistrÃ©e avec succÃ¨s.")

            return redirect("avances:avance_list")

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    else:

        form = AvanceForm(role=role)

    # -----------------------------------------------------
    # AFFICHAGE
    # -----------------------------------------------------

    return render(request, "avances/form.html", {"form": form, "role": role})


# =========================================================
# LISTE DES AVANCES
# =========================================================
@session_login_required
def avance_list(request):

    # -----------------------------------------------------
    # RÃ”LE DE L'UTILISATEUR
    # -----------------------------------------------------

    role = request.session.get("role")

    # -----------------------------------------------------
    # AVANCES AUTORISÃ‰ES SELON LE RÃ”LE
    # -----------------------------------------------------

    avances = get_avance_queryset_for_role(role)

    # -----------------------------------------------------
    # RÃ‰CUPÃ‰RATION DES FILTRES
    # -----------------------------------------------------

    recherche = request.GET.get("personnel", "").strip()

    date_debut = request.GET.get("date_debut", "").strip()

    date_fin = request.GET.get("date_fin", "").strip()

    # -----------------------------------------------------
    # RECHERCHE PAR NOM OU PRÃ‰NOM
    # -----------------------------------------------------

    if recherche:
        avances = avances.filter(
            Q(personnel__nom__icontains=recherche)
            | Q(personnel__prenom__icontains=recherche)
        )

    # -----------------------------------------------------
    # FILTRE PAR DATE DE DÃ‰BUT
    # DateField : date incluse
    # -----------------------------------------------------

    if date_debut:
        avances = avances.filter(dateAv__gte=date_debut)

    # -----------------------------------------------------
    # FILTRE PAR DATE DE FIN
    # DateField : date incluse
    # -----------------------------------------------------

    if date_fin:
        avances = avances.filter(dateAv__lte=date_fin)

    # -----------------------------------------------------
    # TRI CHRONOLOGIQUE INVERSÃ‰
    # -----------------------------------------------------

    avances = avances.order_by("-dateAv", "-id")

    # -----------------------------------------------------
    # PAGINATION
    # -----------------------------------------------------

    paginator = Paginator(avances, 12)

    page_obj = paginator.get_page(request.GET.get("page"))

    # -----------------------------------------------------
    # PARAMÃˆTRES DE PAGINATION
    # CONSERVATION DES FILTRES
    # -----------------------------------------------------

    query_params = request.GET.copy()

    query_params.pop("page", None)

    # -----------------------------------------------------
    # AFFICHAGE
    # -----------------------------------------------------

    return render(
        request,
        "avances/list.html",
        {
            "avances": page_obj,
            "page_obj": page_obj,
            "personnel": recherche,
            "date_debut": date_debut,
            "date_fin": date_fin,
            "role": role,
            "query_params": query_params.urlencode(),
        },
    )


# =========================================================
# DETAIL
# =========================================================
@session_login_required
def avance_detail(request, id):

    # -----------------------------------------------------
    # RÃ”LE
    # -----------------------------------------------------

    role = request.session.get("role")

    # -----------------------------------------------------
    # SÃ‰CURITÃ‰
    # -----------------------------------------------------

    avance = get_object_or_404(get_avance_queryset_for_role(role), id=id)

    # -----------------------------------------------------
    # AUDIT
    # -----------------------------------------------------

    enregistrer_action(
        request,
        "VIEW",
        "Avance",
        id,
        description=("Consultation détail avance personnel"),
    )

    # -----------------------------------------------------
    # AFFICHAGE
    # -----------------------------------------------------

    return render(request, "avances/detail.html", {"avance": avance, "role": role})


# =========================================================
# MODIFICATION
# =========================================================
@session_login_required
def avance_edit(request, id):

    # -----------------------------------------------------
    # RÃ”LE
    # -----------------------------------------------------

    role = request.session.get("role")

    # -----------------------------------------------------
    # AVANCE AUTORISÃ‰E POUR CE RÃ”LE
    # -----------------------------------------------------

    avance = get_object_or_404(get_avance_queryset_for_role(role), id=id)

    # -----------------------------------------------------
    # UTILISATEUR CONNECTÃ‰
    # -----------------------------------------------------

    user_id = request.session.get("user_id")

    # -----------------------------------------------------
    # VÃ‰RIFICATION PROPRIÃ‰TAIRE
    # -----------------------------------------------------

    if not user_id or avance.enregistre_par_id != int(user_id):

        messages.error(request, "Vous ne pouvez pas modifier cette avance.")

        return redirect("avances:avance_list")

    # -----------------------------------------------------
    # ANCIENNES VALEURS
    # -----------------------------------------------------

    ancienne = {
        "personnel": str(avance.personnel),
        "montant": str(avance.montantAv),
        "motif": avance.motifAv,
        "type": avance.typeAv,
    }

    # -----------------------------------------------------
    # POST
    # -----------------------------------------------------

    if request.method == "POST":

        form = AvanceForm(request.POST, instance=avance, role=role)

        if form.is_valid():

            # ---------------------------------------------
            # VÃ‰RIFICATION PERSONNEL
            # ---------------------------------------------

            personnel = form.cleaned_data.get("personnel")

            personnel_queryset = get_personnel_queryset_for_role(role)

            if not personnel_queryset.filter(id=personnel.id).exists():

                messages.error(
                    request, "Vous n'Ãªtes pas autorisÃ© Ã  sÃ©lectionner " "ce personnel."
                )

                return redirect("avances:avance_list")

            # ---------------------------------------------
            # ENREGISTRER
            # ---------------------------------------------

            avance_modifiee = form.save()

            # ---------------------------------------------
            # NOUVELLES VALEURS
            # ---------------------------------------------

            nouvelle = {
                "personnel": str(avance_modifiee.personnel),
                "montant": str(avance_modifiee.montantAv),
                "motif": avance_modifiee.motifAv,
                "type": avance_modifiee.typeAv,
            }

            # ---------------------------------------------
            # AUDIT
            # ---------------------------------------------

            enregistrer_action(
                request,
                "UPDATE",
                "Avance",
                id,
                ancienne=ancienne,
                nouvelle=nouvelle,
                description=("Modification d'une avance personnel"),
            )

            # ---------------------------------------------
            # MESSAGE
            # ---------------------------------------------

            messages.success(request, "Avance modifiÃ©e avec succÃ¨s.")

            return redirect("avances:avance_list")

    # -----------------------------------------------------
    # GET
    # -----------------------------------------------------

    else:

        form = AvanceForm(instance=avance, role=role)

    # -----------------------------------------------------
    # AFFICHAGE
    # -----------------------------------------------------

    return render(
        request, "avances/form.html", {"form": form, "role": role, "avance": avance}
    )


# =========================================================
# SUPPRESSION
# =========================================================
@session_login_required
def avance_delete(request, id):

    # -----------------------------------------------------
    # RÃ”LE
    # -----------------------------------------------------

    role = request.session.get("role")

    # -----------------------------------------------------
    # AVANCE AUTORISÃ‰E POUR CE RÃ”LE
    # -----------------------------------------------------

    avance = get_object_or_404(get_avance_queryset_for_role(role), id=id)

    # -----------------------------------------------------
    # UTILISATEUR CONNECTÃ‰
    # -----------------------------------------------------

    user_id = request.session.get("user_id")

    # -----------------------------------------------------
    # VÃ‰RIFICATION PROPRIÃ‰TAIRE
    # -----------------------------------------------------

    if not user_id or avance.enregistre_par_id != int(user_id):

        messages.error(request, "Vous ne pouvez pas supprimer cette avance.")

        return redirect("avances:avance_list")

    # -----------------------------------------------------
    # ANCIENNES VALEURS
    # -----------------------------------------------------

    ancienne = {
        "personnel": str(avance.personnel),
        "montant": str(avance.montantAv),
        "motif": avance.motifAv,
        "type": avance.typeAv,
    }

    # -----------------------------------------------------
    # SUPPRESSION
    # -----------------------------------------------------

    if request.method == "POST":

        enregistrer_action(
            request,
            "DELETE",
            "Avance",
            id,
            ancienne=ancienne,
            description=("Suppression d'une avance personnel"),
        )

        avance.delete()

        messages.success(request, "Avance supprimÃ©e avec succÃ¨s.")

    # -----------------------------------------------------
    # RETOUR
    # -----------------------------------------------------

    return redirect("avances:avance_list")


# =============================================================
# MCCR / ENTREPRISE H â€” SALAIRES SÃ‰PARÃ‰S DE GALAXY
# =============================================================
@session_login_required
def _h_salaire_utilisateur(request):
    """Récupére exclusivement l'utilisateur de la session MCCR."""
    if request.session.get("h_role") not in ("Dir", "Compta"):
        return None

    h_user_id = request.session.get("h_user_id")

    if not h_user_id:
        return None

    return H_AppUser.objects.filter(pk=h_user_id).first()



@session_login_required
def h_salaire_list(request):
    utilisateur = _h_salaire_utilisateur(request)

    if not utilisateur:
        messages.error(request, "Accés MCCR non autorisé.")
        return redirect("users:login")

    salaires = H_Salaire.objects.select_related(
        "personnel",
        "enregistreur",
    ).all()

    personnel_recherche = request.GET.get("personnel", "").strip()
    montant = request.GET.get("montant", "").strip()
    date = request.GET.get("date", "").strip()

    if personnel_recherche:
        salaires = salaires.filter(
            Q(personnel__nom__icontains=personnel_recherche)
            | Q(personnel__prenom__icontains=personnel_recherche)
        )

    if montant:
        salaires = salaires.filter(montant=montant)

    if date:
        salaires = salaires.filter(date_paiement=date)

    total_salaires = salaires.aggregate(total=Sum("montant"))["total"] or 0

    total_reste = salaires.aggregate(total=Sum("reste"))["total"] or 0

    total_trop_percu = salaires.aggregate(total=Sum("trop_percu"))["total"] or 0

    paginator = Paginator(salaires, 10)
    page_obj = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)

    personnels = H_Personnel.objects.all().order_by("nom", "prenom")

    return render(
        request,
        "salaire/h_list.html",
        {
            "salaires": page_obj,
            "page_obj": page_obj,
            "personnels": personnels,
            "total_salaires": total_salaires,
            "total_reste": total_reste,
            "total_trop_percu": total_trop_percu,
            "utilisateur": utilisateur,
            "role": request.session.get("h_role"),
            "h_role": request.session.get("h_role"),
            "personnel": personnel_recherche,
            "montant": montant,
            "date": date,
            "query_params": query_params.urlencode(),
        },
    )

@session_login_required
def h_salaire_add(request):
    utilisateur = _h_salaire_utilisateur(request)

    if not utilisateur:
        messages.error(request, "AccÃ¨s MCCR non autorisÃ©.")
        return redirect("users:login")

    role = request.session.get("h_role")

    if request.method == "POST":
        form = H_SalaireForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                salaire = form.save(commit=False)
                salaire.enregistreur = utilisateur
                salaire.save()

                if salaire.personnel:
                    h_recalculer_situation_personnel(salaire.personnel)

            messages.success(
                request,
                "Le salaire MCCR a Ã©tÃ© enregistrÃ© avec succÃ¨s.",
            )
            return redirect("salaire:h_salaire_list")
    else:
        form = H_SalaireForm()

    return render(
        request,
        "salaire/h_form.html",
        {
            "form": form,
            "action": "Ajouter",
            "role": role,
            "h_role": role,
        },
    )

@session_login_required
def h_salaire_edit(request, id=None, pk=None):
    utilisateur = _h_salaire_utilisateur(request)

    if not utilisateur:
        messages.error(request, "AccÃ¨s MCCR non autorisÃ©.")
        return redirect("users:login")

    salaire_id = id if id is not None else pk

    if salaire_id is None:
        messages.error(request, "Identifiant du salaire manquant.")
        return redirect("salaire:h_salaire_list")

    salaire = get_object_or_404(
        H_Salaire.objects.select_related("personnel", "enregistreur"),
        pk=salaire_id,
    )

    if salaire.enregistreur_id != utilisateur.pk:
        messages.error(
            request,
            "Vous n'étes pas autorisé à  modifier ce salaire MCCR.",
        )
        return redirect("salaire:h_salaire_list")

    ancien_personnel = salaire.personnel
    role = request.session.get("h_role")

    if request.method == "POST":
        form = H_SalaireForm(request.POST, instance=salaire)

        if form.is_valid():
            with transaction.atomic():
                salaire_modifie = form.save(commit=False)

                # L'enregistreur initial reste inchangÃ©.
                salaire_modifie.enregistreur = utilisateur
                salaire_modifie.save()

                nouveau_personnel = salaire_modifie.personnel

                if ancien_personnel:
                    h_recalculer_situation_personnel(ancien_personnel)

                if nouveau_personnel and (
                    ancien_personnel is None
                    or ancien_personnel.pk != nouveau_personnel.pk
                ):
                    h_recalculer_situation_personnel(nouveau_personnel)

                elif nouveau_personnel:
                    # Recalcul du personnel inchangÃ©.
                    h_recalculer_situation_personnel(nouveau_personnel)

            messages.success(
                request,
                "Le salaire MCCR a étés modifié avec succées.",
            )
            return redirect("salaire:h_salaire_list")
    else:
        form = H_SalaireForm(instance=salaire)

    return render(
        request,
        "salaire/h_form.html",
        {
            "form": form,
            "action": "Modifier",
            "salaire": salaire,
            "role": role,
            "h_role": role,
        },
    )


@session_login_required
def h_salaire_delete(request, id=None, pk=None):
    utilisateur = _h_salaire_utilisateur(request)

    if not utilisateur:
        messages.error(request, "Accées MCCR non autorisé.")
        return redirect("users:login")

    salaire_id = id if id is not None else pk

    if salaire_id is None:
        messages.error(request, "Identifiant du salaire manquant.")
        return redirect("salaire:h_salaire_list")

    salaire = get_object_or_404(
        H_Salaire.objects.select_related("personnel", "enregistreur"),
        pk=salaire_id,
    )

    if salaire.enregistreur_id != utilisateur.pk:
        messages.error(
            request,
            "Vous n'Ãªtes pas autorisé à  supprimer ce salaire MCCR.",
        )
        return redirect("salaire:h_salaire_list")

    if request.method == "POST":
        personnel = salaire.personnel

        with transaction.atomic():
            salaire.delete()

            if personnel:
                h_recalculer_situation_personnel(personnel)

        messages.success(
            request,
            "Le salaire MCCR a été supprimé avec succÃ¨s.",
        )
        return redirect("salaire:h_salaire_list")

    return render(
        request,
        "salaire/h_confirm_delete.html",
        {
            "salaire": salaire,
            "role": request.session.get("h_role"),
            "h_role": request.session.get("h_role"),
        },
    )


@session_login_required
def recalculer_reste(self):
    reste, trop_percu = self.calculer_situation()

    H_Salaire.objects.filter(pk=self.pk).update(
        reste=reste,
        trop_percu=trop_percu,
    )

    self.reste = reste
    self.trop_percu = trop_percu

    return reste


# =============================================================
# MCCR / ENTREPRISE H â€” AVANCES
# =============================================================
@session_login_required
def _h_avance_utilisateur(request):
    """Vérifie la session et l'utilisateur MCCR."""
    if request.session.get("h_role") not in ("Dir", "Compta"):
        return None

    h_user_id = request.session.get("h_user_id")
    if not h_user_id:
        return None

    return H_AppUser.objects.filter(pk=h_user_id).first()

@session_login_required
def h_avance_list(request):
    utilisateur = _h_avance_utilisateur(request)

    if not utilisateur:
        messages.error(request, "Accès MCCR non autorisé.")
        return redirect("users:login")

    h_avances = H_Avance.objects.select_related(
        "personnel",
        "enregistre_par",
    ).order_by("-dateAv", "-pk")

    recherche = request.GET.get("personnel", "").strip()
    date_debut = request.GET.get("date_debut", "").strip()
    date_fin = request.GET.get("date_fin", "").strip()

    if recherche:
        h_avances = h_avances.filter(
            Q(personnel__nom__icontains=recherche)
            | Q(personnel__prenom__icontains=recherche)
        )

    if date_debut:
        h_avances = h_avances.filter(dateAv__gte=date_debut)

    if date_fin:
        h_avances = h_avances.filter(dateAv__lte=date_fin)

    paginator = Paginator(h_avances, 12)
    page_obj = paginator.get_page(request.GET.get("page"))

    query_params = request.GET.copy()
    query_params.pop("page", None)

    return render(
        request,
        "avances/h_list.html",
        {
            "h_avances": page_obj,
            "page_obj": page_obj,
            "h_personnel": recherche,
            "date_debut": date_debut,
            "date_fin": date_fin,
            "h_role": request.session.get("h_role"),
            "role": request.session.get("h_role"),
            "utilisateur": utilisateur,
            "query_params": query_params.urlencode(),
        },
    )

@session_login_required
def h_avance_add(request):
    utilisateur = _h_avance_utilisateur(request)

    if not utilisateur:
        messages.error(request, "Accés MCCR non autorisé.")
        return redirect("users:login")

    if request.method == "POST":
        form = H_AvanceForm(request.POST)

        if form.is_valid():
            with transaction.atomic():
                avance = form.save(commit=False)
                avance.enregistre_par = utilisateur
                avance.save()

            enregistrer_action(
                request,
                "CREATE",
                "H_Avance",
                avance.pk,
                nouvelle={
                    "personnel": str(avance.personnel),
                    "montant": str(avance.montantAv),
                    "motif": avance.motifAv,
                    "type": avance.typeAv,
                },
                description="CrÃ©ation d'une avance MCCR",
            )

            messages.success(
                request, "Avance MCCR enregistrée avec succés."
            )
            return redirect("avances:h_avance_list")
    else:
        form = H_AvanceForm()

    return render(
        request,
        "avances/h_form.html",
        {
            "form": form,
            "action": "Ajouter",
            "h_role": request.session.get("h_role"),
            "role": request.session.get("h_role"),
        },
    )

@session_login_required
def h_avance_edit(request, id):
    utilisateur = _h_avance_utilisateur(request)

    if not utilisateur:
        messages.error(request, "Accès MCCR non autorisé.")
        return redirect("users:login")

    avance = get_object_or_404(
        H_Avance.objects.select_related("personnel", "enregistre_par"),
        pk=id,
    )

    if avance.enregistre_par_id != utilisateur.pk:
        messages.error(
            request,
            "Vous ne pouvez modifier que les avances que vous avez enregistrées.",
        )
        return redirect("avances:h_avance_list")

    if request.method == "POST":
        form = H_AvanceForm(request.POST, instance=avance)

        if form.is_valid():
            ancienne_valeur = {
                "personnel": str(avance.personnel),
                "montant": str(avance.montantAv),
                "motif": avance.motifAv,
                "type": avance.typeAv,
                "date": str(avance.dateAv),
            }

            with transaction.atomic():
                avance_modifiee = form.save(commit=False)

                # Conserver l'enregistreur initial.
                avance_modifiee.enregistre_par = utilisateur
                avance_modifiee.save()

            enregistrer_action(
                request,
                "UPDATE",
                "H_Avance",
                avance_modifiee.pk,
                ancienne=ancienne_valeur,
                nouvelle={
                    "personnel": str(avance_modifiee.personnel),
                    "montant": str(avance_modifiee.montantAv),
                    "motif": avance_modifiee.motifAv,
                    "type": avance_modifiee.typeAv,
                    "date": str(avance_modifiee.dateAv),
                },
                description="Modification d'une avance MCCR",
            )

            messages.success(
                request,
                "Avance MCCR modifiée avec succès.",
            )
            return redirect("avances:h_avance_list")

    else:
        form = H_AvanceForm(instance=avance)

    return render(
        request,
        "avances/h_form.html",
        {
            "form": form,
            "action": "Modifier",
            "h_role": request.session.get("h_role"),
            "role": request.session.get("h_role"),
            "utilisateur": utilisateur,
        },
    )

@session_login_required
def h_avance_delete(request, id):
    utilisateur = _h_avance_utilisateur(request)

    if not utilisateur:
        messages.error(request, "Accés MCCR non autorisé.")
        return redirect("users:login")

    if request.method != "POST":
        messages.error(
            request,
            "La suppression doit Ãªtre effectuée depuis le formulaire.",
        )
        return redirect("avances:h_avance_list")

    avance = get_object_or_404(H_Avance, pk=id)

    if avance.enregistre_par_id != utilisateur.pk:
        messages.error(
            request,
            "Vous n'Ãªtes pas autorisÃ© Ã  supprimer cette avance MCCR.",
        )
        return redirect("avances:h_avance_list")

    ancienne = {
        "personnel": str(avance.personnel),
        "montant": str(avance.montantAv),
        "motif": avance.motifAv,
        "type": avance.typeAv,
    }

    with transaction.atomic():
        enregistrer_action(
            request,
            "DELETE",
            "H_Avance",
            avance.pk,
            ancienne=ancienne,
            description="Suppression d'une avance MCCR",
        )
        avance.delete()

    messages.success(request, "Avance MCCR supprimée avec succés.")
    return redirect("avances:h_avance_list")
