from django.shortcuts import render, get_object_or_404, redirect
from .models import Transentrant
from .forms import TransentrantForm


def t_transentrant_list(request):
    data = Transentrant.objects.all()
    return render(request, 'transentrant/list.html', {'transentrants': data})


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