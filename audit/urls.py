from django.urls import path
from . import views


app_name = "audit"


urlpatterns = [

    path(
        "",
        views.audit_list,
        name="audit_list"
    ),

    path(
            "",
            views.h_audit_list,
            name="h_audit_list"
        ),
    
]