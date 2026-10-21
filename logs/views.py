from django.core.paginator import Paginator
from django.shortcuts import render

from users.decorators import h_role_required, login_required_projet

from .models import H_Log, Log


# Nombre de lignes par page
LIGNES_PAR_PAGE = 25


# ============================================================
# LOGS SYSTÈME GALAXY
# ============================================================
@login_required_projet
def logs_list(request):
    logs = Log.objects.order_by("-date_log", "-pk")

    level = request.GET.get("level", "").strip()

    if level:
        logs = logs.filter(level=level)

    paginator = Paginator(logs, LIGNES_PAR_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "logs/list.html",
        {
            "logs": page_obj,
            "page_obj": page_obj,
            "paginator": paginator,
            "level": level,
        },
    )


# ============================================================
# LOGS SYSTÈME MCCR
# ============================================================
@h_role_required("Admin", "Dir", "Compta")
def h_logs_list(request):
    logs = H_Log.objects.order_by("-date_log", "-pk")

    level = request.GET.get("level", "").strip()

    if level:
        logs = logs.filter(level=level)

    paginator = Paginator(logs, LIGNES_PAR_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "logs/list.html",
        {
            "logs": page_obj,
            "page_obj": page_obj,
            "paginator": paginator,
            "level": level,
        },
    )
