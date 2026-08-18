"""
Corrige la fecha de vencimiento de las BustaCards ya emitidas: deben vencer el
31 de diciembre del año de emision (antes, por un bug, se ponia +365 dias).

Afecta TarjetaCiudadana (app) y BustaCardVentanilla (ventanilla). No borra
nada: solo normaliza la fecha.

    python manage.py corregir_vencimientos          # aplica
    python manage.py corregir_vencimientos --dry-run # solo muestra
"""
from __future__ import annotations

import datetime

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.tarjetas.models import BustaCardVentanilla, TarjetaCiudadana


class Command(BaseCommand):
    help = "Normaliza fecha_vencimiento de las BustaCards al 31/dic de su año."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **opts):
        dry = opts["dry_run"]
        cambios_app = 0
        cambios_vent = 0

        # --- TarjetaCiudadana (app) ---
        for t in TarjetaCiudadana.objects.all():
            anio = timezone.localtime(t.fecha_emision).year
            correcta = datetime.date(anio, 12, 31)
            if t.fecha_vencimiento != correcta:
                self.stdout.write(
                    f"  Tarjeta {t.codigo} ({t.ciudadano_id}): "
                    f"{t.fecha_vencimiento} -> {correcta}"
                )
                if not dry:
                    t.fecha_vencimiento = correcta
                    t.save(update_fields=["fecha_vencimiento"])
                cambios_app += 1

        # --- BustaCardVentanilla (ventanilla) ---
        for b in BustaCardVentanilla.objects.all():
            correcta = datetime.date(b.anio, 12, 31)
            if b.fecha_vencimiento != correcta:
                self.stdout.write(
                    f"  Ventanilla {b.codigo} (DNI {b.dni}): "
                    f"{b.fecha_vencimiento} -> {correcta}"
                )
                if not dry:
                    b.fecha_vencimiento = correcta
                    b.save(update_fields=["fecha_vencimiento"])
                cambios_vent += 1

        modo = "(dry-run) " if dry else ""
        self.stdout.write(
            self.style.SUCCESS(
                f"\n{modo}Corregidas: {cambios_app} del app, "
                f"{cambios_vent} de ventanilla."
            )
        )
