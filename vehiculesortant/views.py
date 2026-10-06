from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import VehiculeSortant
from .forms import VehiculeSortantForm
from users.models import AppUser
from audit.utils import enregistrer_action


def vehicule_sortant_list(request):
    queryset = VehiculeSortant.objects.all()
    chauffeur = request.GET.get('chauffeur', '').strip()
    num_vehicule = request.GET.get('num_vehicule', '').strip()
    telephone = request.GET.get('telephone', '').strip()

    if chauffeur:
        queryset = queryset.filter(chauffeur__icontains=chauffeur)
    if num_vehicule:
        queryset = queryset.filter(num_vehicule__icontains=num_vehicule)
    if telephone:
        queryset = queryset.filter(telephone__icontains=telephone)

    return render(request, 'vehiculesortant/list.html', {
        'vehicules': queryset,
        'chauffeur': chauffeur,
        'num_vehicule': num_vehicule,
        'telephone': telephone,
        'user_id': request.session.get('user_id'),
    })


def vehicule_sortant_add(request):
    if not request.session.get('user_id'):
        return redirect('users:login')

    if request.method == 'POST':
        form = VehiculeSortantForm(request.POST, request.FILES)
        if form.is_valid():
            vehicule = form.save(commit=False)
            user = AppUser.objects.get(id=request.session.get('user_id'))
            vehicule.created_by = user
            vehicule.save()
            enregistrer_action(
                request,
                'CREATE',
                'VehiculeSortant',
                vehicule.id,
                nouvelle={
                    'chauffeur': vehicule.chauffeur,
                    'num_vehicule': vehicule.num_vehicule,
                    'telephone': vehicule.telephone,
                    'remorque': vehicule.remorque,
                    'ticket': vehicule.ticket,
                },
                description='Création d’un véhicule sortant'
            )
            messages.success(request, 'Véhicule sortant ajouté.')
            return redirect('vehiculesortant:vehicule_sortant_list')
    else:
        form = VehiculeSortantForm()

    return render(request, 'vehiculesortant/form.html', {'form': form})


def vehicule_sortant_detail(request, id):
    vehicule = get_object_or_404(VehiculeSortant, id=id)
    return render(request, 'vehiculesortant/detail.html', {'vehicule': vehicule})


def vehicule_sortant_edit(request, id):
    if not request.session.get('user_id'):
        return redirect('users:login')

    vehicule = get_object_or_404(VehiculeSortant, id=id)
    if vehicule.created_by_id != request.session.get('user_id'):
        messages.error(request, 'Vous ne pouvez pas modifier cet enregistrement.')
        return redirect('vehiculesortant:vehicule_sortant_list')

    if request.method == 'POST':
        form = VehiculeSortantForm(request.POST, request.FILES, instance=vehicule)
        if form.is_valid():
            vehicule = form.save()
            messages.success(request, 'Modification réussie.')
            return redirect('vehiculesortant:vehicule_sortant_list')
    else:
        form = VehiculeSortantForm(instance=vehicule)

    return render(request, 'vehiculesortant/form.html', {'form': form})


def vehicule_sortant_delete(request, id):
    if not request.session.get('user_id'):
        return redirect('users:login')

    vehicule = get_object_or_404(VehiculeSortant, id=id)
    if vehicule.created_by_id != request.session.get('user_id'):
        messages.error(request, 'Suppression interdite.')
        return redirect('vehiculesortant:vehicule_sortant_list')

    if request.method == 'POST':
        vehicule.delete()
        messages.success(request, 'Suppression réussie.')
        return redirect('vehiculesortant:vehicule_sortant_list')

    return render(request, 'vehiculesortant/confirm_delete.html', {'vehicule': vehicule})
