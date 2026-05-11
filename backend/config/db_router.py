"""
Router multi-BD para el backend de Busta App.

Reglas:
  - Todas las escrituras de Django van a `default` (dbbusta_app).
  - `muni_db` y `tramites_db` son produccion SIAP: solo lectura para las apps
    `externos_muni` y `externos_tramites` respectivamente.
  - `allow_migrate` solo permite migraciones en `default`. Esto evita que
    Django cree auth_user, contenttypes, sessions, etc. en produccion
    cuando se corre `makemigrations`/`migrate`.
"""

READONLY_DBS = {"muni_db", "tramites_db"}

APP_TO_DB = {
    "externos_tramites": "tramites_db",
    "externos_muni": "muni_db",
}


class MultiDBRouter:

    def db_for_read(self, model, **hints):
        return APP_TO_DB.get(model._meta.app_label, "default")

    def db_for_write(self, model, **hints):
        # Jamas escribimos en produccion. Si alguien intenta guardar un
        # modelo de externos_* lanzara error de conexion por read-only.
        if model._meta.app_label in APP_TO_DB:
            return None  # Django fallara explicitamente
        return "default"

    def allow_relation(self, obj1, obj2, **hints):
        # Permitir relaciones dentro de la misma BD logica.
        db1 = APP_TO_DB.get(obj1._meta.app_label, "default")
        db2 = APP_TO_DB.get(obj2._meta.app_label, "default")
        return db1 == db2

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        # Solo migramos contra `default`. Nunca tocamos BDs externas.
        if db in READONLY_DBS:
            return False
        if app_label in APP_TO_DB:
            # Modelos externos nunca se migran (son managed=False igual).
            return False
        return db == "default"
