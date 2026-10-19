from django.shortcuts import render

from .models import Audit, H_Audit
from users.decorators import login_required_projet, h_role_required


# ============================================================
# AUDIT GALAXY
# ============================================================
@login_required_projet
def audit_list(request):
    audits = Audit.objects.order_by("-date_action")

    action = request.GET.get("action", "").strip()
    table = request.GET.get("table", "").strip()

    if action:
        audits = audits.filter(action=action)

    if table:
        audits = audits.filter(table__icontains=table)

    return render(
        request,
        "audit/list.html",
        {
            "audits": audits,
            "action": action,
            "table": table,
        },
    )


# ============================================================
# AUDIT MCCR
# ============================================================
@h_role_required("Dir", "Compta")
def h_audit_list(request):
    audits = H_Audit.objects.order_by("-date_action")

    action = request.GET.get("action", "").strip()
    table = request.GET.get("table", "").strip()

    if action:
        audits = audits.filter(action=action)

    if table:
        audits = audits.filter(table__icontains=table)

    return render(
        request,
        "audit/list.html",
        {
            "audits": audits,
            "action": action,
            "table": table,
        },
    )
