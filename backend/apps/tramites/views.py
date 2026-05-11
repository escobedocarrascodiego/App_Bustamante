import datetime
from datetime import timedelta

from django.utils import timezone
from rest_framework import mixins, permissions, status, viewsets
from rest_framework.decorators import action, api_view, parser_classes, permission_classes
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from .models import AreaMunicipal, EstadoExpediente, Expediente, SeguimientoExpediente, TipoTramite
from .serializers import (
    AreaSerializer,
    CrearExpedienteSerializer,
    ExpedienteSerializer,
    SeguimientoSerializer,
    TipoTramiteSerializer,
)
from apps.externos_tramites.models import Propietarios

from .services import (
    TramiteExternoError,
    cod_pros_de_dni,
    crear_ingreso_externo,
    detalle_expediente_siap,
    listar_expedientes_contribuyente,
    listar_oficinas,
    listar_solicitudes_tupa,
    listar_tramites_contribuyente,
    obtener_documento_expediente,
    obtener_oficina_default,
    verificar_registro_mesa_partes,
)


class AreaViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = AreaMunicipal.objects.all()
    serializer_class = AreaSerializer
    permission_classes = [permissions.AllowAny]


class TipoTramiteViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TipoTramite.objects.filter(activo=True).select_related("area")
    serializer_class = TipoTramiteSerializer
    permission_classes = [permissions.AllowAny]
    filterset_fields = ["area"]
    search_fields = ["nombre", "codigo", "descripcion"]


class ExpedienteViewSet(
    mixins.CreateModelMixin,
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = ExpedienteSerializer

    def get_queryset(self):
        return (
            Expediente.objects.filter(ciudadano=self.request.user)
            .select_related("tipo")
            .prefetch_related("seguimientos")
        )

    def get_serializer_class(self):
        if self.action == "create":
            return CrearExpedienteSerializer
        return ExpedienteSerializer

    def perform_create(self, serializer):
        tipo = serializer.validated_data["tipo"]
        now = timezone.now()
        numero = f"EXP-{now.year}-{Expediente.objects.count() + 1:06d}"
        fecha_estimada = (now + timedelta(days=tipo.dias_habiles * 2)).date()
        expediente = serializer.save(
            ciudadano=self.request.user,
            numero=numero,
            fecha_estimada=fecha_estimada,
        )
        SeguimientoExpediente.objects.create(
            expediente=expediente,
            estado=EstadoExpediente.INGRESADO,
            comentario="Expediente ingresado desde el app movil.",
            area=tipo.area,
        )

    @action(detail=True, methods=["get"])
    def seguimientos(self, request, pk=None):
        expediente = self.get_object()
        data = SeguimientoSerializer(expediente.seguimientos.all(), many=True).data
        return Response(data)


def _cod_pros_del_user(user) -> list[str]:
    """
    Resuelve TODOS los cod_pro asociados al DNI del usuario (en Propietarios
    suele haber duplicados). Como respaldo incluye el cod_pro guardado en
    Ciudadano por si el sync hubiera capturado uno extra que ya no aparece
    en la consulta por DNI.
    """
    cod_pros: list[str] = []
    dni = getattr(user, "dni", None)
    if dni:
        cod_pros.extend(cod_pros_de_dni(dni))
    cod_pro_local = getattr(user, "cod_pro", None)
    if cod_pro_local and cod_pro_local not in cod_pros:
        cod_pros.append(cod_pro_local)
    print(
        f"[tramites] _cod_pros_del_user: dni={dni!r} "
        f"cod_pro_local={cod_pro_local!r} -> resultado={cod_pros}"
    )
    return cod_pros


def _id_usuaext_del_user(user) -> int | None:
    """
    Busca id_usuaext en Propietarios para el DNI del usuario. Preferimos
    cualquier fila que lo tenga seteado (la cuenta MPV activa). Devuelve
    None si ninguna fila tiene id_usuaext.
    """
    dni = getattr(user, "dni", None)
    if not dni:
        return None
    try:
        prop = (
            Propietarios.objects.using("tramites_db")
            .filter(dni_pro=dni.strip(), id_usuaext__isnull=False)
            .values_list("id_usuaext", flat=True)
            .first()
        )
    except Exception as exc:  # pragma: no cover
        print(f"[mis_expedientes] error resolviendo id_usuaext para {dni}: {exc!r}")
        return None
    return int(prop) if prop else None


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def mis_expedientes_siap(request):
    user = request.user
    cod_pros = _cod_pros_del_user(user)
    id_usuaext = _id_usuaext_del_user(user)
    print(
        f"[mis_expedientes] dni={getattr(user, 'dni', None)} "
        f"cod_pros={cod_pros} id_usuaext={id_usuaext}"
    )
    if not cod_pros and not id_usuaext:
        return Response([])
    data = listar_tramites_contribuyente(cod_pros, id_usuaext=id_usuaext)
    print(f"[mis_expedientes] devolviendo {len(data)} tramite(s).")
    return Response(data)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def detalle_expediente_siap_view(request, cod_ing: int):
    cod_pros = _cod_pros_del_user(request.user)
    id_usuaext = _id_usuaext_del_user(request.user)

    # 1) Buscar primero en Ingresos (con linea de vida)
    if cod_pros:
        data = detalle_expediente_siap(cod_pros, cod_ing)
        if data:
            return Response(data)

    # 2) Si no esta en Ingresos, puede ser un pendiente en IngresosExternos
    #    (creado desde el app y aun no aprobado). En ese caso no hay
    #    proveidos todavia: linea_vida vacia.
    if id_usuaext:
        from apps.externos_tramites.models import IngresosExternos, SolicitudesExternas

        ext = (
            IngresosExternos.objects.using("tramites_db")
            .filter(cod_ingext=cod_ing, id_usuaext=id_usuaext)
            .first()
        )
        if ext:
            sol_nom = ""
            if ext.cod_solext:
                sol = (
                    SolicitudesExternas.objects.using("tramites_db")
                    .filter(cod_solext=ext.cod_solext)
                    .values_list("nom_solext", flat=True)
                    .first()
                )
                sol_nom = (sol or "").strip()
            return Response({
                "id": ext.cod_ingext,
                "numero": (ext.num_docext or "").strip(),
                "asunto": (ext.des_solext or "").strip(),
                "tipo_codigo": ext.cod_solext,
                "tipo_nombre": sol_nom,
                "estado": "EN_TRAMITE",
                "estado_display": "Pendiente de aprobacion",
                "observacion": "",
                "fecha_ingreso": ext.fec_ingext.isoformat() if ext.fec_ingext else None,
                "fecha_vencimiento": ext.fec_venext.isoformat() if ext.fec_venext else None,
                "oficina_actual": (ext.ofi_recext or "").strip(),
                "linea_vida": [],
            })

    return Response(
        {"detail": "Expediente no encontrado."},
        status=status.HTTP_404_NOT_FOUND,
    )


def _parse_fecha_dmy(s: str | None) -> datetime.date | None:
    if not s:
        return None
    s = s.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


@api_view(["POST"])
@permission_classes([permissions.IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def registrar_tramite_externo(request):
    """
    Registra un nuevo tramite en `dbControl.IngresosExternos` desde el app.

    Body (multipart/form-data):
      - cod_solext   (str)  obligatorio
      - des_solext   (str)  obligatorio
      - ofi_recext   (str)  default OFI00046
      - ofi_traext   (str)  default OFI00046
      - fecha        (str)  dd/mm/yyyy o yyyy-mm-dd (default: hoy)
      - adjunto      (File) PDF opcional
    """
    cod_solext = (request.data.get("cod_solext") or "").strip()
    des_solext = (request.data.get("des_solext") or "").strip()
    ofi_recext = (request.data.get("ofi_recext") or "").strip()
    ofi_traext = (request.data.get("ofi_traext") or "").strip()
    fecha = _parse_fecha_dmy(request.data.get("fecha"))

    archivo = request.FILES.get("adjunto")
    archivo_bytes = archivo.read() if archivo else None
    archivo_nombre = archivo.name if archivo else None

    user = request.user
    print(
        "[tramite-externo] payload recibido | "
        f"user.dni={getattr(user, 'dni', None)} cod_pro={getattr(user, 'cod_pro', None)} "
        f"cod_solext={cod_solext!r} ofi_recext={ofi_recext!r} ofi_traext={ofi_traext!r} "
        f"fecha={request.data.get('fecha')!r} -> {fecha} "
        f"archivo={archivo_nombre!r} ({len(archivo_bytes) if archivo_bytes else 0} bytes) "
        f"des_solext={des_solext[:120]!r}"
    )

    try:
        resultado = crear_ingreso_externo(
            user=request.user,
            cod_solext=cod_solext,
            des_solext=des_solext,
            ofi_recext=ofi_recext,
            ofi_traext=ofi_traext,
            fec_solicitud=fecha,
            archivo_nombre=archivo_nombre,
            archivo_bytes=archivo_bytes,
        )
    except TramiteExternoError as exc:
        return Response(
            {"detail": str(exc)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(resultado, status=status.HTTP_201_CREATED)


@api_view(["GET"])
@permission_classes([permissions.IsAuthenticated])
def catalogo_formulario(request):
    """
    Bundle de catalogos para el formulario de Nuevo Tramite:
      - documento expediente (DOC00030)
      - tipos de solicitud TUPA habilitados
      - oficinas activas + oficina default (OFI00046)
    Una sola request, asi el form arranca con todo cacheado.
    """
    return Response(
        {
            "documento": obtener_documento_expediente(),
            "tipos_solicitud": listar_solicitudes_tupa(),
            "oficinas": listar_oficinas(),
            "oficina_default": obtener_oficina_default(),
            "registro_mesa_partes": verificar_registro_mesa_partes(request.user),
        }
    )
