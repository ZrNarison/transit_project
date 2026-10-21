from .models import H_Log, Log


def enregistrer_log(message, level="INFO", module="", ip_address=None):
    """Enregistre un événement dans le journal applicatif GALAXY."""
    return Log.objects.create(
        message=message,
        level=level,
        module=module,
        ip_address=ip_address,
    )


def h_enregistrer_log(message, level="INFO", module="", ip_address=None):
    """Enregistre un événement dans le journal applicatif MCCR."""
    return H_Log.objects.create(
        message=message,
        level=level,
        module=module,
        ip_address=ip_address,
    )
