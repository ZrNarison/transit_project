from .models import Log, H_Log


def enregistrer_log(
    message,
    level="INFO",
    module="",
    ip_address=None
):

    Log.objects.create(
        message=message,
        level=level,
        module=module,
        ip_address=ip_address
    )


def h_enregistrer_log(
    message,
    level="INFO",
    module="",
    ip_address=None
):

    Log.objects.create(
        message=message,
        level=level,
        module=module,
        ip_address=ip_address
    )