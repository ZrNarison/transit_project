from django.apps import AppConfig


class AvanceConfig(AppConfig):
    name = 'avances'

    def ready(self):
        # Import signal handlers to ensure they are registered
        try:
            import avances.signals  # noqa
        except Exception:
            pass
