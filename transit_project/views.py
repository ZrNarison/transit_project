from django.http import HttpResponse

def home(request):
    return HttpResponse("<h1>Bienvenue dans Transit ERP</h1>")