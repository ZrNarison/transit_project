from django.shortcuts import render, get_object_or_404, redirect
from .models import Client
from .forms import ClientForm


def client_list(request):
    clients = Client.objects.all()
    return render(request, 'clients/list.html', {'clients': clients})


def client_add(request):
    if request.method == "POST":
        form = ClientForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            return redirect("clients:client_list")
        else:
            print(form.errors)  # Affiche les erreurs dans le terminal
    else:
        form = ClientForm()

    return render(request, "clients/form.html", {
        "form": form
    })

def client_detail(request, id):
    client = get_object_or_404(Client, id=id)
    return render(request, 'clients/detail.html', {'client': client})


def client_edit(request, id):
    client = get_object_or_404(Client, id=id)

    if request.method == "POST":
        form = ClientForm(request.POST, request.FILES, instance=client)
        if form.is_valid():
            form.save()
            return redirect('clients:client_list')

    else:
        form = ClientForm(instance=client)

    return render(request, 'clients/form.html', {'form': form})


def client_delete(request, id):
    client = get_object_or_404(Client, id=id)

    if request.method == "POST":
        client.delete()
        return redirect('clients:client_list')

    return render(request, 'clients/confirm_delete.html', {'client': client})