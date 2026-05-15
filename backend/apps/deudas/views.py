from decimal import Decimal

from django.db.models import Sum
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from .models import Deuda, EstadoDeuda, Pago
from .serializers import DeudaSerializer, PagoSerializer
from .services import (
    cntrcod_pertenece_a_dni,
    comprobar_deuda,
    listar_condiciones_por_dni,
    listar_deudas_detalle,
    obtener_cntrcod_usuario,
)


def _filtrar_por_prdconcod(items: list[dict], prdconcod: int | None) -> list[dict]:
    """Si se pidio un prdconcod, deja solo los items con ese codigo."""
    if prdconcod is None:
        return items
    return [it for it in items if it.get("prd_con_cod") == prdconcod]


class DeudaViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = DeudaSerializer
    filterset_fields = ["tipo", "estado", "anio"]
    ordering_fields = ["fecha_vencimiento", "anio", "monto"]
    search_fields = ["concepto", "codigo_referencia"]

    def get_queryset(self):
        return Deuda.objects.filter(ciudadano=self.request.user).prefetch_related("pagos")

    @action(detail=False, methods=["get"], url_path="muni")
    def verificar_muni(self, request):
        """Estado real del contribuyente en muni_db (CTACTE / IMPPREANU / LICENCIAANU)."""
        cntrcod = obtener_cntrcod_usuario(request.user)
        if not cntrcod:
            return Response(
                {
                    "cntrcod": None,
                    "estado_busta_card": "SIN_CONTRIBUYENTE",
                    "tiene_deuda": False,
                    "deuda_total": 0.0,
                    "mensaje": "Tu DNI no figura en el padron de contribuyentes.",
                },
                status=status.HTTP_200_OK,
            )
        return Response(comprobar_deuda(cntrcod), status=status.HTTP_200_OK)

    @action(detail=False, methods=["get"])
    def detalle(self, request):
        """
        Desglose completo de deudas desde muni_db (CTACTE + IMPPREANU).
        Acepta `?prdconcod=Y` para filtrar por una condicion especifica
        (1=Propietario Unico, 4=Sociedad Conyugal, etc - PREDIOCOND).
        Devuelve `condiciones[]` con cada PrdConCod presente en la deuda
        del contribuyente y su monto total — el front muestra el selector.

        IMPORTANTE: un mismo DNI puede tener N filas en CONTRIBUYENTES (varios
        "roles tributarios": una como Propietario Unico, otra como Sociedad
        Conyugal, otra como Sucesion, etc.). Cada CntrCod tiene su propia
        deuda en CTACTE/IMPPREANU. Antes consultabamos solo el primer CntrCod
        y perdiamos las deudas de los demas roles — el selector de condiciones
        solo mostraba uno aunque hubieran varios.
        """
        dni = (getattr(request.user, "dni", None) or "").strip()

        # Resolver TODOS los CntrCods asociados al DNI. Asi acumulamos la
        # deuda de cada rol tributario y el frontend puede mostrar el selector
        # completo de condiciones.
        condiciones_dni = listar_condiciones_por_dni(dni) if dni else []

        # Fallback: si el usuario no tiene DNI valido o no esta en
        # CONTRIBUYENTES, intentamos usar el cntr_cod cacheado en su perfil
        # (camino antiguo). Garantiza retrocompatibilidad sin tocar usuarios
        # que solo tienen 1 cntrcod.
        if not condiciones_dni:
            fallback = obtener_cntrcod_usuario(request.user)
            if fallback:
                condiciones_dni = [{"cntrcod": int(fallback), "nombre": ""}]

        if not condiciones_dni:
            return Response(
                {
                    "items": [],
                    "total": 0.0,
                    "cntrcod": None,
                    "condiciones": [],
                    "prdconcod": None,
                    "mensaje": "Sin contribuyente asociado.",
                },
                status=status.HTTP_200_OK,
            )

        # Consolidar items de todos los CntrCods. Cada item ya trae su propio
        # PrdConCod, asi que el filtrado por condicion sigue siendo correcto
        # independientemente de cuantos cntrcods aporten datos.
        items_full: list[dict] = []
        cntrcods_usados: list[int] = []
        for cond in condiciones_dni:
            cc = cond["cntrcod"]
            cntrcods_usados.append(cc)
            items_full.extend(listar_deudas_detalle(cc))

        # Construimos la lista de condiciones a partir de los PrdConCod
        # realmente presentes en la deuda (no de CONTRIBUYENTES).
        cond_map: dict[int, dict] = {}
        for it in items_full:
            cod = it.get("prd_con_cod")
            if cod is None:
                continue
            entry = cond_map.setdefault(cod, {
                "prd_con_cod": cod,
                "nombre": it.get("condicion_nombre") or f"Condición {cod}",
                "deuda_total": 0.0,
            })
            entry["deuda_total"] += float(it.get("saldo_pendiente") or 0)
        for entry in cond_map.values():
            entry["deuda_total"] = round(entry["deuda_total"], 2)
        condiciones = sorted(cond_map.values(), key=lambda c: c["prd_con_cod"])

        # Filtro por prdconcod si se pidio
        prdconcod_param = request.query_params.get("prdconcod")
        prdconcod: int | None = None
        if prdconcod_param:
            try:
                prdconcod = int(prdconcod_param)
            except (TypeError, ValueError):
                prdconcod = None
            if prdconcod is not None and prdconcod not in cond_map:
                print(
                    f"[deudas] prdconcod={prdconcod_param!r} no esta en la "
                    f"deuda del DNI {dni!r} (cntrcods={cntrcods_usados}); ignorado."
                )
                prdconcod = None

        items = _filtrar_por_prdconcod(items_full, prdconcod)
        total = sum(item["saldo_pendiente"] for item in items)

        # Para el campo `cntrcod` de la respuesta seguimos devolviendo solo
        # uno (el primero) por compatibilidad con clientes antiguos que lo
        # consumen. El frontend no lo usa para nada importante — todo lo que
        # necesita esta en `condiciones[]`.
        cntrcod_principal = cntrcods_usados[0] if cntrcods_usados else None

        print(
            f"[deudas] detalle dni={dni!r} cntrcods={cntrcods_usados} "
            f"prdconcod={prdconcod} items={len(items)}/{len(items_full)} "
            f"total={total:.2f} "
            f"condiciones={[(c['prd_con_cod'], c['nombre'], c['deuda_total']) for c in condiciones]}"
        )

        return Response(
            {
                "items": items,
                "total": round(total, 2),
                "cntrcod": cntrcod_principal,
                "condiciones": condiciones,
                "prdconcod": prdconcod,
                "mensaje": "",
            },
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def resumen(self, request):
        qs = self.get_queryset()
        pendientes = qs.exclude(estado=EstadoDeuda.PAGADA)
        total_pendiente = sum((d.total for d in pendientes), Decimal("0.00"))
        return Response({
            "total_pendiente": total_pendiente,
            "cantidad_pendientes": pendientes.count(),
            "por_tipo": list(
                pendientes.values("tipo").annotate(total=Sum("monto")).order_by("tipo")
            ),
        })

    @action(detail=True, methods=["post"])
    def pagar(self, request, pk=None):
        """Registro simulado de pago desde el app. En produccion se integra pasarela."""
        deuda = self.get_object()
        if deuda.estado == EstadoDeuda.PAGADA:
            return Response(
                {"detail": "Esta deuda ya fue pagada."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        pago = Pago.objects.create(
            deuda=deuda,
            monto=deuda.total,
            medio="APP",
            numero_operacion=request.data.get("numero_operacion", ""),
        )
        deuda.estado = EstadoDeuda.PAGADA
        deuda.save(update_fields=["estado"])
        return Response(PagoSerializer(pago).data, status=status.HTTP_201_CREATED)
