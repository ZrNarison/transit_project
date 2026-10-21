from django.urls import path

from . import views

app_name = "logs"

urlpatterns = [
    # GALAXY
    path("", views.logs_list, name="logs_list"),

    # MCCR
    path("mccr/", views.h_logs_list, name="h_logs_list"),
]
