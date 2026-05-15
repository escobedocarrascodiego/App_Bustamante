"""
Diagnostico de la deuda de un contribuyente.

Uso:
  python manage.py diagnostico_deuda --dni 02008230
  python manage.py diagnostico_deuda --cntrcod 202

Muestra:
  1) Filas en CONTRIBUYENTES con ese DNI.
  2) Filas en CTACTE para el CntrCod (anios y rubros).
  3) Filas en IMPPREANU para el CntrCod (anios, calculo y flags).
  4) Saldo por anio segun la logica actual del app.
  5) Comparacion contra cualquier total externo proporcionado.

No modifica nada. Solo lectura con NOLOCK.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError
from django.db import connections


class Command(BaseCommand):
    help = "Diagnostica que datos hay en muni_db para un contribuyente."

    def add_arguments(self, parser):
        parser.add_argument("--dni", help="DNI a buscar en CONTRIBUYENTES.")
        parser.add_argument(
            "--cntrcod",
            type=int,
            help="CntrCod a inspeccionar (alternativa al DNI).",
        )

    def handle(self, *args, **opts):
        dni = (opts.get("dni") or "").strip()
        cntrcod = opts.get("cntrcod")
        if not dni and not cntrcod:
            raise CommandError("Pasa --dni o --cntrcod.")

        with connections["muni_db"].cursor() as cur:
            cntrcods = self._buscar_contribuyentes(cur, dni, cntrcod)
            if not cntrcods:
                self.stdout.write(self.style.WARNING("No se encontro nada."))
                return

            for cc in cntrcods:
                self.stdout.write("")
                self.stdout.write(self.style.HTTP_INFO(f"===== CntrCod={cc} ====="))
                self._mostrar_ctacte(cur, cc)
                self._mostrar_imppreanu(cur, cc)
                self._mostrar_imppreanucntr(cur, cc)
                self._mostrar_resumen_app(cur, cc)

    # ------------------------------------------------------------------
    def _buscar_contribuyentes(self, cur, dni: str, cntrcod: int | None) -> list[int]:
        if cntrcod:
            cur.execute(
                "SELECT CntrCod, CntrNumDoc, CntrNom FROM CONTRIBUYENTES WITH (NOLOCK) "
                "WHERE CntrCod = %s",
                [cntrcod],
            )
        else:
            cur.execute(
                "SELECT CntrCod, CntrNumDoc, CntrNom FROM CONTRIBUYENTES WITH (NOLOCK) "
                "WHERE LTRIM(RTRIM(CntrNumDoc)) = %s ORDER BY CntrCod",
                [dni],
            )
        rows = cur.fetchall()
        if not rows:
            return []
        self.stdout.write(self.style.SUCCESS(f"\n{len(rows)} fila(s) en CONTRIBUYENTES:"))
        for r in rows:
            self.stdout.write(f"  cntrcod={r[0]} dni={r[1]!r} nombre={(r[2] or '').strip()!r}")
        return [int(r[0]) for r in rows]

    # ------------------------------------------------------------------
    def _mostrar_ctacte(self, cur, cntrcod: int) -> None:
        self.stdout.write("\n--- CTACTE (deuda registrada) ---")
        cur.execute(
            """
            SELECT
                c.CtCtAno, c.RubroCod, c.SRubCod, c.CtCtConCod, c.IpaCod, c.CtCtMes,
                CAST(SUM(c.CtCtImpor) AS FLOAT) AS Importe,
                CAST(SUM(ISNULL(d.Cargos, 0)) AS FLOAT) AS Cargos,
                CAST(SUM(ISNULL(d.Pagos, 0)) AS FLOAT) AS Pagos,
                CAST(SUM(c.CtCtImpor - ISNULL(d.Pagos, 0)) AS FLOAT) AS Saldo
            FROM CTACTE c WITH (NOLOCK)
            LEFT JOIN (
                SELECT CtCtCod,
                    SUM(CASE WHEN TranMovDet='+' THEN CtCtDImpor ELSE 0 END) AS Cargos,
                    SUM(CASE WHEN TranMovDet='-' THEN CtCtDImpor ELSE 0 END) AS Pagos
                FROM CTACTEDET WITH (NOLOCK)
                WHERE CtCtDFlgAnu = ' '
                GROUP BY CtCtCod
            ) d ON c.CtCtCod = d.CtCtCod
            WHERE c.CntrCod = %s
              AND c.CtCtFlgAnu = ' '
            GROUP BY c.CtCtAno, c.RubroCod, c.SRubCod, c.CtCtConCod, c.IpaCod, c.CtCtMes
            ORDER BY c.CtCtAno, c.RubroCod, c.CtCtMes
            """,
            [cntrcod],
        )
        rows = cur.fetchall()
        if not rows:
            self.stdout.write("  (sin filas)")
            return
        self.stdout.write(
            f"  {'Año':>4} {'Rub':>3} {'SRub':>4} {'Cond':>4} {'IpaCod':>7} "
            f"{'Mes':>3} {'Importe':>10} {'Cargos':>9} {'Pagos':>9} {'Saldo':>9}"
        )
        for r in rows:
            self.stdout.write(
                f"  {r[0]:>4} {r[1]:>3} {str(r[2]):>4} {str(r[3]):>4} "
                f"{str(r[4]):>7} {str(r[5]):>3} "
                f"{r[6] or 0:>10.2f} {r[7] or 0:>9.2f} "
                f"{r[8] or 0:>9.2f} {r[9] or 0:>9.2f}"
            )

    # ------------------------------------------------------------------
    def _mostrar_imppreanu(self, cur, cntrcod: int) -> None:
        self.stdout.write("\n--- IMPPREANU (predial calculado titular) ---")
        cur.execute(
            """
            SELECT
                IpaAno, IpaCod, PrdConCod,
                CAST(IpaImpAutoCal AS FLOAT) AS Predial,
                CAST(IpaImpARBCal + IpaImpABVCal + IpaImpAPJCal AS FLOAT) AS Arbitrios,
                CAST(IpaSerImpCal AS FLOAT) AS Serenazgo,
                IpaFlgPagado, IpaFlgPagadoArb, IpaSerGeneFlg, IpaFlgAnu
            FROM IMPPREANU WITH (NOLOCK)
            WHERE CntrCod = %s
            ORDER BY IpaAno, IpaCod
            """,
            [cntrcod],
        )
        rows = cur.fetchall()
        if not rows:
            self.stdout.write("  (sin filas)")
            return
        self.stdout.write(
            f"  {'Año':>4} {'IpaCod':>7} {'Cond':>4} "
            f"{'Predial':>9} {'Arbitrios':>9} {'Serenazgo':>9} "
            f"{'FlgPredPag':>10} {'FlgArbPag':>9} {'FlgSerGen':>9} {'FlgAnu':>6}"
        )
        for r in rows:
            self.stdout.write(
                f"  {r[0]:>4} {str(r[1]):>7} {str(r[2]):>4} "
                f"{r[3] or 0:>9.2f} {r[4] or 0:>9.2f} {r[5] or 0:>9.2f} "
                f"{str(r[6]):>10} {str(r[7]):>9} {str(r[8]):>9} {r[9]!r:>6}"
            )

    # ------------------------------------------------------------------
    def _mostrar_imppreanucntr(self, cur, cntrcod: int) -> None:
        self.stdout.write("\n--- IMPPREANUCNTR (predial co-propietario) ---")
        cur.execute(
            """
            SELECT
                IpaAno, IpaCod, IpaPrdConCod,
                CAST(ISNULL(IpaCntrImpuCal, 0) AS FLOAT) AS Predial,
                CAST(ISNULL(IpaCntrRBCal, 0) + ISNULL(IpaCntrBVCal, 0)
                    + ISNULL(IpaCntrPJCal, 0) AS FLOAT) AS Arbitrios,
                CAST(ISNULL(IpaCntrSereCal, 0) AS FLOAT) AS Serenazgo,
                IpaGeneFlg, IpaGeneArbFlg, IpaGeneSereFlg
            FROM IMPPREANUCNTR WITH (NOLOCK)
            WHERE IpaCntrCod = %s
            ORDER BY IpaAno, IpaCod
            """,
            [cntrcod],
        )
        rows = cur.fetchall()
        if not rows:
            self.stdout.write("  (sin filas)")
            return
        self.stdout.write(
            f"  {'Año':>4} {'IpaCod':>7} {'Cond':>4} "
            f"{'Predial':>9} {'Arbitrios':>9} {'Serenazgo':>9} "
            f"{'GenP':>4} {'GenA':>4} {'GenS':>4}"
        )
        for r in rows:
            self.stdout.write(
                f"  {r[0]:>4} {str(r[1]):>7} {str(r[2]):>4} "
                f"{r[3] or 0:>9.2f} {r[4] or 0:>9.2f} {r[5] or 0:>9.2f} "
                f"{str(r[6]):>4} {str(r[7]):>4} {str(r[8]):>4}"
            )

    # ------------------------------------------------------------------
    def _mostrar_resumen_app(self, cur, cntrcod: int) -> None:
        """Llama a la logica real del app y muestra el total que devuelve."""
        from apps.deudas.services import listar_deudas_detalle

        self.stdout.write("\n--- Resumen segun la logica del app ---")
        items = listar_deudas_detalle(cntrcod)
        total = sum(i["saldo_pendiente"] for i in items)
        self.stdout.write(f"  total app: {total:.2f}  ({len(items)} item(s))")

        # Por anio
        por_anio: dict[int | None, float] = {}
        for i in items:
            por_anio[i["anio"]] = por_anio.get(i["anio"], 0.0) + i["saldo_pendiente"]
        self.stdout.write("\n  Total por anio:")
        for anio in sorted(por_anio, key=lambda a: (a is None, a)):
            self.stdout.write(f"    {anio}: {por_anio[anio]:>9.2f}")
