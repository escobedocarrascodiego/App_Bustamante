from django.apps import AppConfig


class ColasConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.colas"
    label = "colas"
    verbose_name = "Gestión de colas y turnos"
