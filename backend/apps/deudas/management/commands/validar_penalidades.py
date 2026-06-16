"""
Valida apps.deudas.penalidades contra reportes reales de "Estado de Cuenta".

Casos:
  * CntrCod 10871 (PROPIETARIO UNICO), reporte 01/06/2026: el caso ideal
    porque la fecha del reporte == fecha actual del sistema, asi el reajuste
    del año en curso (2026) ya esta activado (8.37) y se puede comparar.
  * CntrCod 202  (SOCIEDAD CONYUGAL), reporte 14/05/2026: solo se validan
    los AÑOS CERRADOS (<= 2025); el reajuste del año en curso es dinamico y
    cambia con el tiempo (en mayo valia 0, hoy ya esta activado).

El reajuste debe cuadrar (es lo que se cobra bajo amnistia). El interes es el
"real matematico" y se condona, por lo que no se exige coincidencia exacta.
"""
from __future__ import annotations

import datetime
from decimal import Decimal

from django.core.management.base import BaseCommand

from apps.deudas.penalidades import calcular_penalidades_anuales


# (base_anual, reajuste_PDF) — reajuste es lo que validamos estrictamente.
CASOS = {
    "10871 - PROP. UNICO (PDF 01/06/2026)": {
        "fecha": datetime.date(2026, 6, 1),
        "anios": {
            2025: (Decimal("719.08"), Decimal("0.07")),
            2026: (Decimal("732.27"), Decimal("8.37")),  # año en curso activado
        },
    },
    "202 - SOC. CONYUGAL (PDF 14/05/2026, solo años cerrados)": {
        "fecha": datetime.date(2026, 6, 1),
        "anios": {
            2019: (Decimal("863.80"), Decimal("3.44")),
            2020: (Decimal("885.06"), Decimal("2.97")),
            2021: (Decimal("899.97"), Decimal("40.82")),
            2022: (Decimal("926.73"), Decimal("42.79")),
            2023: (Decimal("997.52"), Decimal("0.00")),
            2024: (Decimal("984.44"), Decimal("0.00")),
            2025: (Decimal("1014.48"), Decimal("0.10")),
        },
    },
}

TOLERANCIA = Decimal("0.05")


class Command(BaseCommand):
    help = "Valida el calculo de reajuste contra PDFs reales."

    def handle(self, *args, **opts):
        hubo_fallo = False
        for nombre, caso in CASOS.items():
            fecha = caso["fecha"]
            self.stdout.write(f"\n===== {nombre}  (fecha={fecha}) =====")
            self.stdout.write(
                f"  {'Año':>4} {'Base':>9} {'ReajPDF':>8} {'ReajCalc':>9} "
                f"{'dif':>6} {'IntCalc(ref)':>13}"
            )
            for anio, (base, reaj_pdf) in caso["anios"].items():
                res = calcular_penalidades_anuales(base, anio, fecha)
                dif = res.reajuste - reaj_pdf
                ok = abs(dif) <= TOLERANCIA
                if not ok:
                    hubo_fallo = True
                marca = "" if ok else "  <-- FALLO"
                self.stdout.write(
                    f"  {anio:>4} {base:>9} {reaj_pdf:>8} {res.reajuste:>9} "
                    f"{dif:>6} {res.interes:>13}{marca}"
                )

        self.stdout.write("")
        if hubo_fallo:
            self.stdout.write(self.style.ERROR("VALIDACION CON FALLOS en reajuste."))
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "OK: reajuste dentro de tolerancia en todos los casos."
                )
            )
