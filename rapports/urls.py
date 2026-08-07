from django.urls import path

from . import views


app_name = "rapports"


urlpatterns = [

    path(
        "",
        views.rapport_list,
        name="rapport_list"
    ),

    path(
        "print/",
        views.rapport_print,
        name="rapport_print"
    ),

        path(
        "detail/<str:date>/",
        views.rapport_detail,
        name="rapport_detail"
    ),

]