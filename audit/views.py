from django.shortcuts import render
from .models import Audit


def audit_list(request):

    audits = (
        Audit.objects
        .select_related(
            "utilisateur"
        )
        .order_by(
            "-date_action"
        )
    )


    action = request.GET.get(
        "action",
        ""
    )


    table = request.GET.get(
        "table",
        ""
    )


    if action:

        audits = audits.filter(
            action=action
        )


    if table:

        audits = audits.filter(
            table__icontains=table
        )


    return render(
        request,
        "audit/list.html",
        {
            "audits": audits,
            "action": action,
            "table": table,
        }
    )