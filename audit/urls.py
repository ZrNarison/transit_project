from django.urls import path

from . import views

app_name = "audit"

urlpatterns = [
    # GALAXY
    path("", views.audit_list, name="audit_list"),

    # MCCR
    path("mccr/", views.h_audit_list, name="h_audit_list"),
]
