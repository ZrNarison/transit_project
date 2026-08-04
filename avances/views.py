from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from .forms import AvanceForm
from .models import Avance
from django.contrib import messages
from users.models import AppUser
from django.core.paginator import Paginator


def avance_add(request):

    if request.method == "POST":

        form = AvanceForm(request.POST)
        if form.is_valid():
            avance = form.save(commit=False)
            user_id = request.session.get(
                "user_id"
            )
            if user_id:
                try:
                    avance.enregistre_par = AppUser.objects.get(
                        id=user_id
                    )
                except AppUser.DoesNotExist:
                    avance.enregistre_par = None
            avance.save()
            messages.success(request, "Avance enregistrée avec succès.")
            return redirect("avances:avance_list")
    else:
        form = AvanceForm()
    return render(request,"avances/form.html",
        {
            "form": form
        }
    )


def avance_list(request):

    avances = Avance.objects.select_related(
        "personnel",
        "client"
    ).all()


    recherche = request.GET.get(
        "personnel",
        ""
    ).strip()
    date = request.GET.get(
        "date",
        ""
    ).strip()

    if recherche:
        avances = avances.filter(

            Q(personnel__nom__icontains=recherche) |

            Q(personnel__prenom__icontains=recherche) |

            Q(client__nom__icontains=recherche) |

            Q(client__prenom__icontains=recherche)

        )



    # Filtre date

    if date:

        avances = avances.filter(
            dateAv__date=date
        )



    context = {

        "avances": avances,

        "personnel": recherche,

        "date": date,

    }


    return render(
        request,
        "avances/list.html",
        context
    )


def avance_detail(request, id):

    avance = get_object_or_404(Avance,id=id)
    return render(
        request,
        "avances/detail.html",
        {
            "avance": avance
        }
    )



def avance_edit(request, id):
    avance = get_object_or_404(
        Avance,
        id=id
    )


    user_id = request.session.get(
        "user_id"
    )


    if not user_id or avance.enregistre_par_id != int(user_id):

        messages.error(
            request,
            "Vous ne pouvez pas modifier cette avance."
        )

        return redirect(
            "avances:avance_list"
        )


    if request.method == "POST":

        form = AvanceForm(
            request.POST,
            instance=avance
        )


        if form.is_valid():

            form.save()

            messages.success(
                request,
                "Avance modifiée avec succès."
            )

            return redirect(
                "avances:avance_list"
            )


    else:

        form = AvanceForm(
            instance=avance
        )


    return render(
        request,
        "avances/form.html",
        {
            "form": form
        }
    )


def avance_delete(request, id):

    avance = get_object_or_404(
        Avance,
        id=id
    )


    user_id = request.session.get(
        "user_id"
    )

    if not user_id or avance.enregistre_par_id != int(user_id):

        messages.error(
            request,
            "Vous ne pouvez pas supprimer cette avance."
        )

        return redirect(
            "avances:avance_list"
        )



    if request.method == "POST":

        avance.delete()


        messages.success(
            request,
            "Avance supprimée avec succès."
        )


    return redirect(
        "avances:avance_list"
    )

    avance = get_object_or_404(
        Avance,
        id=id
    )


    if request.method == "POST":

        avance.delete()

        return redirect(
            "avances:avance_list"
        )



    return render(
        request,
        "avances/confirm_delete.html",
        {
            "avance": avance
        }
    )


