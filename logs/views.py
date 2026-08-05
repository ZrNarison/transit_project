from django.shortcuts import render

from .models import Log



def logs_list(request):

    logs = (
        Log.objects
        .order_by(
            "-date_log"
        )
    )


    level = request.GET.get(
        "level",
        ""
    )


    if level:

        logs = logs.filter(
            level=level
        )


    return render(
        request,
        "logs/list.html",
        {
            "logs": logs,
            "level": level,
        }
    )