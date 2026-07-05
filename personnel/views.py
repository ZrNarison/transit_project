from django.shortcuts import render, get_object_or_404, redirect
from .models import Personnel
from .forms import PersonnelForm


def personnel_list(request):
    personnels = Personnel.objects.all()
    return render(request, 'personnel/list.html', {
        'personnels': personnels
    })


def personnel_add(request):
    form = PersonnelForm(request.POST or None, request.FILES or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect("personnel:personnel_list")

    return render(request, "personnel/form.html", {"form": form})


def personnel_detail(request, id):
    personnel = get_object_or_404(Personnel, id=id)
    return render(request, 'personnel/detail.html', {'personnel': personnel})


def personnel_edit(request, id):
    personnel = get_object_or_404(Personnel, id=id)
    form = PersonnelForm(request.POST or None, request.FILES or None, instance=personnel)

    if request.method == "POST" and form.is_valid():
        form.save()
        return redirect('personnel:personnel_list')

    return render(request, 'personnel/form.html', {'form': form})


def personnel_delete(request, id):
    personnel = get_object_or_404(Personnel, id=id)

    if request.method == "POST":
        personnel.delete()
        return redirect('personnel:personnel_list')

    return render(request, 'personnel/confirm_delete.html', {'personnel': personnel})