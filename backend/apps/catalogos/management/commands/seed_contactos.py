"""
Carga los telefonos directos oficiales de la Municipalidad Distrital de
Jose Luis Bustamante y Rivero. Idempotente: se puede correr varias veces
sin duplicar filas (usa `update_or_create` por `area`).
"""
from django.core.management.base import BaseCommand

from apps.catalogos.models import Contacto


CONTACTOS = [
    # (orden, area, telefono, horario, email, whatsapp)
    (1, "Central Telefonica", "054-430700 / 054-430073", "Lun a Vie 08:00 - 16:30", "", ""),
    (2, "Gerencia de Seguridad Ciudadana", "054-426666", "24 horas", "", ""),
    (
        3,
        "Gerencia de Administracion Tributaria - Orientacion al Contribuyente",
        "054-421414",
        "Lun a Vie 08:00 - 16:30",
        "",
        "",
    ),
    (
        4,
        "Gerencia de Promocion Social y Desarrollo Economico",
        "054-430282",
        "Lun a Vie 08:00 - 16:30",
        "",
        "",
    ),
    (5, "Demuna", "054-422141", "Lun a Vie 08:00 - 16:30", "", ""),
    (
        6,
        "Agencia Municipal de Administracion Tributaria - Simon Bolivar",
        "054-422252",
        "Lun a Vie 08:00 - 16:30",
        "",
        "",
    ),
    (7, "Oficina de Abastecimientos", "054-427195", "Lun a Vie 08:00 - 16:30", "", ""),
    (
        8,
        "Oficina de Imagen Institucional y Relaciones Publicas",
        "054-427194",
        "Lun a Vie 08:00 - 16:30",
        "",
        "",
    ),
    (9, "Organo de Control Institucional - OCI", "054-593307", "Lun a Vie 08:00 - 16:30", "", ""),
]


class Command(BaseCommand):
    help = "Carga los telefonos directos oficiales de la municipalidad."

    def handle(self, *args, **options):
        creados = 0
        actualizados = 0
        for orden, area, telefono, horario, email, whatsapp in CONTACTOS:
            _, creado = Contacto.objects.update_or_create(
                area=area,
                defaults={
                    "telefono": telefono,
                    "horario": horario,
                    "email": email,
                    "whatsapp": whatsapp,
                    "orden": orden,
                    "responsable": "",
                },
            )
            if creado:
                creados += 1
            else:
                actualizados += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Contactos listos: {creados} creados, {actualizados} actualizados."
            )
        )
