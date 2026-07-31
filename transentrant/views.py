from django.shortcuts import render, get_object_or_404, redirect
from .models import Transentrant
from .forms import TransentrantForm


def t_transentrant_list(request):
    queryset = Transentrant.objects.all()
    chauffeur = request.GET.get('chauffeur', '').strip()
    num_vehicule = request.GET.get('num_vehicule', '').strip()
    telephone = request.GET.get('telephone', '').strip()

    if chauffeur:
        queryset = queryset.filter(chauffeur__icontains=chauffeur)
    if num_vehicule:
        queryset = queryset.filter(num_vehicule__icontains=num_vehicule)
    if telephone:
        queryset = queryset.filter(telephone__icontains=telephone)

    return render(request, 'transentrant/list.html', {
        'transentrants': queryset,
        'chauffeur': chauffeur,
        'num_vehicule': num_vehicule,
        'telephone': telephone,
    })


def t_transentrant_add(request):
    if request.method == "POST":
        form = TransentrantForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return redirect("transentrant:t_transentrant_liste")
    else:
        form = TransentrantForm()

    return render(request, "transentrant/form.html", {"form": form})


def t_transentrant_detail(request, id):
    client = get_object_or_404(Transentrant, id=id)
    return render(request, 'transentrant/detail.html', {'client': client})


def t_transentrant_edit(request, id):
    client = get_object_or_404(Transentrant, id=id)

    if request.method == "POST":
        form = TransentrantForm(request.POST, request.FILES, instance=client)
        if form.is_valid():
            form.save()
            return redirect('transentrant:t_transentrant_liste')
    else:
        form = TransentrantForm(instance=client)

    return render(request, 'transentrant/form.html', {'form': form})


def t_transentrant_delete(request, id):
    client = get_object_or_404(Transentrant, id=id)

    if request.method == "POST":
        client.delete()
        return redirect('transentrant:t_transentrant_liste')

    return render(request, 'transentrant/confirm_delete.html', {'client': client})