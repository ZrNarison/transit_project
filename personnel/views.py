from django.shortcuts import render, get_object_or_404, redirect
form .models import Personnel
form .forms import PersonnelForm

# Create your views here.
def personnel_list(request):
    Personnel = Personnel.objects.all()
    return render(request, 'personnel/list.html', {'personnel': Personnel})


def personnel_add(request):
    if request.method == "POST":
        form = PersonnelForm(request.POST, request.FILES)

        if form.is_valid():
            form.save()
            return redirect("personnel:personnel_list")
        else:
            print(form.errors)  # Affiche les erreurs dans le terminal
    else:
        form = PersonnelForm()

    return render(request, "personnel/form.html", {
        "form": form
    })

def personnel_detail(request, id):
    Personnel = get_object_or_404(Personnel, id=id)
    return render(request, 'personnel/detail.html', {'personnel': Personnel})


def personnel_edit(request, id):
    Personnel = get_object_or_404(Personnel, id=id)

    if request.method == "POST":
        form = PersonnelForm(request.POST, request.FILES, instance=Personnel)
        if form.is_valid():
            form.save()
            return redirect('personnel:personnel_list')

    else:
        form = PersonnelForm(instance=Personnel)

    return render(request, 'personnel/form.html', {'form': form})


def personnel_delete(request, id):
    Personnel = get_object_or_404(Personnel, id=id)

    if request.method == "POST":
        Personnel.delete()
        return redirect('personnel:personnel_list')

    return render(request, 'personnel/confirm_delete.html', {'personnel': Personnel})