from django.apps import AppConfig


class CiudadanosConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.ciudadanos"
    verbose_name = "Ciudadanos"

    def ready(self) -> None:
        """
        En el startup pisamos el label del campo `username` del admin login
        para que diga "Usuario o DNI" en vez de "DNI" (que es el label por
        default heredado del USERNAME_FIELD del modelo). El field del form
        sigue llamandose `username` y recibe el valor tipeado; nuestro
        backend `UsernameOrDniBackend` se encarga de buscarlo en ambos
        campos del modelo.
        """
        from django.contrib.admin.forms import AdminAuthenticationForm

        original_init = AdminAuthenticationForm.__init__

        def patched_init(self, *args, **kwargs):  # type: ignore[no-untyped-def]
            original_init(self, *args, **kwargs)
            field = self.fields.get("username")
            if field is not None:
                field.label = "Usuario o DNI"

        AdminAuthenticationForm.__init__ = patched_init  # type: ignore[method-assign]
