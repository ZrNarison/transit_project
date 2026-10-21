from django.core.paginator import Paginator
from django.shortcuts import render

from users.decorators import h_role_required, login_required_projet

from .models import Audit, H_Audit


# Nombre de lignes par page
LIGNES_PAR_PAGE = 25


# ============================================================
# AUDIT GALAXY
# ============================================================
@login_required_projet
def audit_list(request):
    audits = Audit.objects.order_by("-date_action", "-pk")

    action = request.GET.get("action", "").strip()
    table = request.GET.get("table", "").strip()

    if action:
        audits = audits.filter(action=action)

    if table:
        audits = audits.filter(table__icontains=table)

    paginator = Paginator(audits, LIGNES_PAR_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "audit/list.html",
        {
            "audits": page_obj,
            "page_obj": page_obj,
            "paginator": paginator,
            "action": action,
            "table": table,
        },
    )


# ============================================================
# AUDIT MCCR
# ============================================================
@h_role_required("Dir", "Compta")
def h_audit_list(request):
    audits = H_Audit.objects.order_by("-date_action", "-pk")

    action = request.GET.get("action", "").strip()
    table = request.GET.get("table", "").strip()

    if action:
        audits = audits.filter(action=action)

    if table:
        audits = audits.filter(table__icontains=table)

    paginator = Paginator(audits, LIGNES_PAR_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))

    return render(
        request,
        "audit/list.html",
        {
            "audits": page_obj,
            "page_obj": page_obj,
            "paginator": paginator,
            "action": action,
            "table": table,
        },
    )
