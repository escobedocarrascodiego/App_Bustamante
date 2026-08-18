"""
Seed inicial: un servicio "Atención general" y las 7 ventanillas.

Es solo un punto de partida para poder probar el sistema. La municipalidad
ajusta luego los servicios reales y que atiende cada ventanilla desde el
Django admin. Idempotente (get_or_create) para no duplicar si se re-corre.
"""
from django.db import migrations


def crear_seed(apps, schema_editor):
    Servicio = apps.get_model("colas", "Servicio")
    Ventanilla = apps.get_model("colas", "Ventanilla")

    servicio, _ = Servicio.objects.get_or_create(
        prefijo="A",
        defaults={
            "nombre": "Atención general",
            "descripcion": "Cola por defecto. Ajustar segun los servicios reales.",
            "color": "#0B3D91",
            "orden": 0,
            "activo": True,
        },
    )

    for n in range(1, 8):  # ventanillas 1..7
        v, creada = Ventanilla.objects.get_or_create(
            numero=n,
            defaults={"estado": "CERRADA", "activa": True},
        )
        if creada:
            v.servicios.add(servicio)


def borrar_seed(apps, schema_editor):
    # Reversa: no borramos datos operativos por seguridad.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("colas", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(crear_seed, borrar_seed),
    ]
