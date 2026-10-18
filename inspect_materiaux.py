
from django.apps import apps

for model in apps.get_app_config("materiaux").get_models():
    print("\n" + model._meta.label)

    for field in model._meta.local_fields:
        related = field.remote_field.model if field.is_relation else None

        print(
            f"{field.name} | "
            f"type={field.__class__.__name__} | "
            f"null={getattr(field, 'null', None)} | "
            f"relation={related}"
        )
