from django.shortcuts import render

from users.decorators import h_role_required, login_required_projet

from .models import H_Log, Log


# ============================================================
# LOGS SYSTÈME GALAXY
# ============================================================
@login_required_projet
def logs_list(request):
    logs = Log.objects.order_by("-date_log")

    level = request.GET.get("level", "").strip()

    if level:
        logs = logs.filter(level=level)

    return render(
        request,
        "logs/list.html",
        {
            "logs": logs,
            "level": level,
        },
    )


# ============================================================
# LOGS SYSTÈME MCCR
# ============================================================
@h_role_required("Dir", "Compta")
def h_logs_list(request):
    logs = H_Log.objects.order_by("-date_log")

    level = request.GET.get("level", "").strip()

    if level:
        logs = logs.filter(level=level)

    return render(
        request,
        "logs/list.html",
        {
            "logs": logs,
            "level": level,
        },
    )
