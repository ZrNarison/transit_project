from django.shortcuts import (
    render,
    redirect,
    get_object_or_404
)

from django.contrib import messages
from django.db.models import Q
from django.core.paginator import Paginator

from .models import AvanceClient
from .forms import AvanceClientForm

from users.models import AppUser

from audit.utils import enregistrer_action



# ==========================================
# LISTE DES AVANCES CLIENTS
# ==========================================

def avanceclient_list(request):

    avances = (
        AvanceClient.objects
        .select_related(
            "client",
            "enregistrer_par"
        )
        .order_by(
            "-date",
            "-id"
        )
    )


    recherche = request.GET.get(
        "client",
        ""
    ).strip()



    if recherche:

        avances = avances.filter(

            Q(client__nom__icontains=recherche)

            |

            Q(client__prenom__icontains=recherche)

        )



    paginator = Paginator(
        avances,
        20
    )


    page_obj = paginator.get_page(
        request.GET.get("page")
    )


    query_params = request.GET.copy()

    if "page" in query_params:

        query_params.pop("page")



    return render(
        request,
        "avanceclient/list.html",
        {
            "avances": page_obj,
            "page_obj": page_obj,
            "client": recherche,
            "query_params": query_params.urlencode()
        }
    )





# ==========================================
# AJOUT
# ==========================================

def avanceclient_add(request):


    if request.method == "POST":

        form = AvanceClientForm(
            request.POST
        )


        if form.is_valid():


            avance = form.save(
                commit=False
            )


            user_id = request.session.get(
                "user_id"
            )


            if user_id:

                try:

                    avance.enregistrer_par = (
                        AppUser.objects.get(
                            id=user_id
                        )
                    )

                except AppUser.DoesNotExist:

                    avance.enregistrer_par = None



            avance.save()



            enregistrer_action(
                request,
                "CREATE",
                "AvanceClient",
                avance.id,
                nouvelle={
                    "client": str(avance.client),
                    "montant": str(avance.montant),
                    "type": avance.type_avance
                },
                description="Création d'une avance client"
            )



            messages.success(
                request,
                "Avance client enregistrée."
            )


            return redirect(
                "avanceclient:list"
            )



    else:

        form = AvanceClientForm()



    return render(
        request,
        "avanceclient/form.html",
        {
            "form": form,
            "action": "Ajouter"
        }
    )





# ==========================================
# DETAIL
# ==========================================

def avanceclient_detail(request, id):


    avance = get_object_or_404(
        AvanceClient,
        id=id
    )


    enregistrer_action(
        request,
        "VIEW",
        "AvanceClient",
        id,
        description="Consultation détail avance client"
    )



    return render(
        request,
        "avanceclient/detail.html",
        {
            "avance": avance
        }
    )





# ==========================================
# MODIFICATION
# ==========================================

def avanceclient_edit(request, id):


    avance = get_object_or_404(
        AvanceClient,
        id=id
    )



    user_id = request.session.get(
        "user_id"
    )


    if (
        not user_id
        or avance.enregistrer_par_id != int(user_id)
    ):

        messages.error(
            request,
            "Vous ne pouvez pas modifier cette avance."
        )


        return redirect(
            "avanceclient:list"
        )



    ancienne = {

        "client": str(avance.client),

        "montant": str(avance.montant),

        "type": avance.type_avance

    }



    if request.method == "POST":


        form = AvanceClientForm(
            request.POST,
            instance=avance
        )


        if form.is_valid():


            avance_modifiee = form.save()



            nouvelle = {

                "client": str(avance_modifiee.client),

                "montant": str(avance_modifiee.montant),

                "type": avance_modifiee.type_avance

            }



            enregistrer_action(
                request,
                "UPDATE",
                "AvanceClient",
                id,
                ancienne=ancienne,
                nouvelle=nouvelle,
                description="Modification avance client"
            )



            messages.success(
                request,
                "Avance client modifiée."
            )


            return redirect(
                "avanceclient:list"
            )



    else:

        form = AvanceClientForm(
            instance=avance
        )



    return render(
        request,
        "avanceclient/form.html",
        {
            "form": form,
            "action": "Modifier"
        }
    )





# ==========================================
# SUPPRESSION
# ==========================================

def avanceclient_delete(request, id):


    avance = get_object_or_404(
        AvanceClient,
        id=id
    )


    user_id = request.session.get(
        "user_id"
    )



    if (
        not user_id
        or avance.enregistrer_par_id != int(user_id)
    ):

        messages.error(
            request,
            "Vous ne pouvez pas supprimer cette avance."
        )


        return redirect(
            "avanceclient:list"
        )



    ancienne = {

        "client": str(avance.client),

        "montant": str(avance.montant)

    }



    if request.method == "POST":


        enregistrer_action(
            request,
            "DELETE",
            "AvanceClient",
            id,
            ancienne=ancienne,
            description="Suppression avance client"
        )


        avance.delete()



        messages.success(
            request,
            "Avance client supprimée."
        )



    return redirect(
        "avanceclient:list"
    )