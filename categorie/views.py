from django.shortcuts import render, get_object_or_404, redirect
from .models import Categorie

# LISTE
def categorie_liste(request):
    categories = Categorie.objects.all()
    return render(request, "categorie/liste.html", {"categories": categories})


# AJOUT
def categorie_add(request):
    if request.method == "POST":
        nom = request.POST.get("nom")
        Categorie.objects.create(nom=nom)
        return redirect("categorie:categorie_liste")

    return render(request, "categorie/add.html")


# MODIFIER
def categorie_edit(request, id):
    categorie = get_object_or_404(Categorie, id=id)

    if request.method == "POST":
        categorie.nom = request.POST.get("nom")
        categorie.save()
        return redirect("categorie:categorie_liste")

    return render(request, "categorie/edit.html", {"categorie": categorie})


# SUPPRIMER
def categorie_delete(request, id):
    categorie = get_object_or_404(Categorie, id=id)
    categorie.delete()
    return redirect("categorie:categorie_liste")