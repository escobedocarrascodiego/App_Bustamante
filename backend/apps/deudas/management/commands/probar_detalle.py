"""
Simula la respuesta del endpoint /api/v1/deudas/detalle/ para un DNI.

Construye un usuario "falso" con el DNI y llama la logica de la view
directamente, asi vemos que devuelve `condiciones[]` (chips del front) y
los totales por condicion sin tener que armar request HTTP.

Uso:
  python manage.py probar_detalle --dni 02008230
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import connections

from apps.deudas.services import listar_condiciones_por_dni, listar_deudas_detalle


class Command(BaseCommand):
    help = "Simula /deudas/detalle/ contra muni_db sin pasar por HTTP."

    def add_arguments(self, parser):
        parser.add_argument("--dni", required=True)

    def handle(self, *args, **opts):
        dni = opts["dni"].strip()
        condiciones_dni = listar_condiciones_por_dni(dni)
        if not condiciones_dni:
            raise CommandError(f"DNI {dni!r} sin filas en CONTRIBUYENTES.")

        self.stdout.write(f"\nDNI {dni!r} -> {len(condiciones_dni)} CntrCod(s):")
        for c in condiciones_dni:
            self.stdout.write(f"  cntrcod={c['cntrcod']} nombre={c['nombre']!r}")

        # Acumular items por cntrcod
        items_full: list[dict] = []
        for cond in condiciones_dni:
            self.stdout.write(f"\n--- Llamando listar_deudas_detalle({cond['cntrcod']}) ---")
            items = listar_deudas_detalle(cond["cntrcod"])
            items_full.extend(items)
            sub_total = sum(i["saldo_pendiente"] for i in items)
            self.stdout.write(f"  -> {len(items)} item(s), subtotal={sub_total:.2f}")

        # Reconstruir condiciones a partir de los items (igual que la view)
        cond_map: dict[int, dict] = {}
        for it in items_full:
            cod = it.get("prd_con_cod")
            if cod is None:
                continue
            entry = cond_map.setdefault(cod, {
                "prd_con_cod": cod,
                "nombre": it.get("condicion_nombre") or f"Condicion {cod}",
                "deuda_total": 0.0,
            })
            entry["deuda_total"] += float(it.get("saldo_pendiente") or 0)
        for e in cond_map.values():
            e["deuda_total"] = round(e["deuda_total"], 2)

        total = round(sum(i["saldo_pendiente"] for i in items_full), 2)
        self.stdout.write(f"\n=== Resultado simulado de /deudas/detalle/ ===")
        self.stdout.write(f"  total: S/ {total:.2f}")
        self.stdout.write(f"  condiciones (chips del frontend):")
        for c in sorted(cond_map.values(), key=lambda x: x["prd_con_cod"]):
            self.stdout.write(
                f"    [{c['prd_con_cod']}] {c['nombre']:<30} S/ {c['deuda_total']:>9.2f}"
            )

        # Direcciones unicas por predio
        self.stdout.write(f"\n  direcciones de predios involucrados:")
        vistos = set()
        for it in items_full:
            pc = it.get("predio_cod")
            if not pc or pc in vistos:
                continue
            vistos.add(pc)
            self.stdout.write(
                f"    predio_cod={pc} direccion={it.get('predio_direccion')!r}"
            )
