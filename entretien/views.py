from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages

from .models import Entretien
from .forms import EntretienForm

from users.models import AppUser

from audit.models import Audit
from logs.models import Log



def get_client_ip(request):

    x_forwarded_for = request.META.get(
        "HTTP_X_FORWARDED_FOR"
    )

    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0]

    else:
        ip = request.META.get(
            "REMOTE_ADDR"
        )

    return ip




def get_user(request):

    user_id = request.session.get(
        "user_id"
    )

    if user_id:

        return AppUser.objects.filter(
            id=user_id
        ).first()

    return None




def entretien_list(request):

    entretiens = Entretien.objects.all().order_by(
        "-date_cree"
    )


    return render(
        request,
        "entretien/list.html",
        {
            "entretiens": entretiens
        }
    )




def entretien_create(request):

    utilisateur = get_user(request)


    if request.method == "POST":

        form = EntretienForm(
            request.POST
        )


        if form.is_valid():

            entretien = form.save(
                commit=False
            )


            entretien.enregistrer_par = utilisateur

            entretien.save()



            # ======================
            # AUDIT CREATE
            # ======================

            Audit.objects.create(

                utilisateur=utilisateur,

                action="CREATE",

                table="Entretien",

                objet_id=entretien.id,

                nouvelle_valeur={
                    "vehicule": entretien.num_vehicule,
                    "piece": entretien.piece_acheter,
                    "nombre": entretien.nombre,
                    "prix": str(entretien.prix_du_piece)
                },

                description=
                f"Création entretien véhicule {entretien.num_vehicule}"
            )



            # ======================
            # LOG SYSTEME
            # ======================

            Log.objects.create(

                level="INFO",

                module="entretien",

                message=
                f"Nouvel entretien créé : {entretien}"
                ,

                ip_address=get_client_ip(request)

            )



            messages.success(
                request,
                "Entretien enregistré avec succès."
            )


            return redirect(
                "entretien:list"
            )


    else:

        form = EntretienForm()



    return render(
        request,
        "entretien/form.html",
        {
            "form": form
        }
    )





def entretien_update(request, id):

    entretien = get_object_or_404(
        Entretien,
        id=id
    )


    utilisateur = get_user(request)


    ancienne = {

        "vehicule": entretien.num_vehicule,

        "piece": entretien.piece_acheter,

        "nombre": entretien.nombre,

        "prix": str(entretien.prix_du_piece)

    }



    if request.method == "POST":


        form = EntretienForm(
            request.POST,
            instance=entretien
        )


        if form.is_valid():

            entretien_modifie = form.save()



            nouvelle = {

                "vehicule": entretien_modifie.num_vehicule,

                "piece": entretien_modifie.piece_acheter,

                "nombre": entretien_modifie.nombre,

                "prix": str(entretien_modifie.prix_du_piece)

            }



            Audit.objects.create(

                utilisateur=utilisateur,

                action="UPDATE",

                table="Entretien",

                objet_id=entretien.id,

                ancienne_valeur=ancienne,

                nouvelle_valeur=nouvelle,

                description=
                f"Modification entretien {entretien.id}"

            )



            Log.objects.create(

                level="INFO",

                module="entretien",

                message=
                f"Modification entretien ID {entretien.id}",

                ip_address=get_client_ip(request)

            )



            messages.success(
                request,
                "Entretien modifié avec succès."
            )


            return redirect(
                "entretien:list"
            )


    else:

        form = EntretienForm(
            instance=entretien
        )



    return render(
        request,
        "entretien/form.html",
        {
            "form": form
        }
    )






def entretien_delete(request, id):

    entretien = get_object_or_404(
        Entretien,
        id=id
    )


    utilisateur = get_user(request)



    ancienne = {

        "vehicule": entretien.num_vehicule,

        "piece": entretien.piece_acheter,

        "nombre": entretien.nombre,

        "prix": str(entretien.prix_du_piece)

    }



    if request.method == "POST":


        entretien.delete()



        Audit.objects.create(

            utilisateur=utilisateur,

            action="DELETE",

            table="Entretien",

            objet_id=id,

            ancienne_valeur=ancienne,

            description=
            f"Suppression entretien ID {id}"

        )



        Log.objects.create(

            level="WARNING",

            module="entretien",

            message=
            f"Suppression entretien ID {id}",

            ip_address=get_client_ip(request)

        )



        messages.success(
            request,
            "Entretien supprimé."
        )


        return redirect(
            "entretien:list"
        )



    return render(

        request,

        "entretien/confirm_delete.html",

        {
            "entretien": entretien
        }

    )