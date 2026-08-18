"""
Logica del gestor de turnos. Toda transicion de estado vive aqui (no en las
vistas) para mantener un solo lugar como fuente de verdad.

Principios:
  - El estado de la ventanilla cambia SOLO por acciones del ventanillero.
  - La numeracion del turno es atomica por (servicio, dia) — reintenta si hay
    colision (dos kioskos al mismo tiempo).
  - El "siguiente" se elige: preferentes primero, luego orden de llegada.
"""
from __future__ import annotations

from django.db import IntegrityError, transaction
from django.db.models.functions import Coalesce
from django.utils import timezone

from .models import Servicio, Turno, Ventanilla


# ---------------------------------------------------------------------------
# Emision de turnos
# ---------------------------------------------------------------------------


def _enriquecer_por_dni(dni: str) -> tuple[str, int | None]:
    """Si el DNI esta en CONTRIBUYENTES, devuelve (nombre, cntr_cod)."""
    dni = (dni or "").strip()
    if not dni:
        return "", None
    try:
        from apps.deudas.services import buscar_contribuyentes

        for c in buscar_contribuyentes(dni, limite=5):
            if c.get("dni") == dni:
                return c.get("nombre", ""), c.get("cntrcod")
    except Exception as exc:  # pragma: no cover
        print(f"[colas] enriquecer dni {dni!r} fallo: {exc!r}")
    return "", None


def emitir_turno(
    servicio: Servicio,
    *,
    prioritario: bool = False,
    dni: str = "",
    nombre: str = "",
    canal: str = Turno.Canal.KIOSKO,
    ciudadano=None,
    en_cola: bool = True,
) -> Turno:
    """
    Crea un turno con numeracion correlativa por (servicio, dia). El DNI es
    OPCIONAL; si esta y se ubica al contribuyente, toma el nombre del padron.
    Si no, usa el `nombre` que el vecino escribio (para verse en la TV).

    `en_cola=True`  -> entra de una a la fila activa (kiosko, ventanilla).
    `en_cola=False` -> queda RESERVADO (reserva del app "en camino"); recien
                       entra a la fila cuando hace check-in (`check_in`).
    """
    hoy = timezone.localdate()
    dni = (dni or "").strip()
    nombre_padron, cntr_cod = _enriquecer_por_dni(dni) if dni else ("", None)
    # El padron manda; si no hay, usamos el nombre digitado.
    nombre = nombre_padron or (nombre or "").strip()
    ahora = timezone.now()

    estado = Turno.Estado.EN_ESPERA if en_cola else Turno.Estado.RESERVADO
    en_cola_desde = ahora if en_cola else None

    # Reintento ante colision de numero (dos kioskos simultaneos).
    for _ in range(6):
        ultimo = (
            Turno.objects.filter(servicio=servicio, fecha=hoy)
            .order_by("-numero")
            .first()
        )
        numero = (ultimo.numero + 1) if ultimo else 1
        codigo = f"{servicio.prefijo}-{numero:03d}"
        try:
            with transaction.atomic():
                return Turno.objects.create(
                    servicio=servicio,
                    fecha=hoy,
                    numero=numero,
                    codigo=codigo,
                    estado=estado,
                    prioritario=prioritario,
                    canal=canal,
                    dni=dni,
                    nombre=nombre,
                    cntr_cod=cntr_cod,
                    ciudadano=ciudadano,
                    en_cola_desde=en_cola_desde,
                )
        except IntegrityError:
            continue
    raise RuntimeError("No se pudo asignar el numero de turno. Reintenta.")


def check_in(turno: Turno) -> Turno:
    """
    "Ya llegué": una reserva del app entra a la fila ACTIVA. Su posicion se
    fija por la hora de llegada (en_cola_desde = ahora), no por la reserva,
    para no pasarle por encima a quien ya estaba esperando.
    """
    if turno.estado != Turno.Estado.RESERVADO:
        return turno
    turno.estado = Turno.Estado.EN_ESPERA
    turno.en_cola_desde = timezone.now()
    turno.save(update_fields=["estado", "en_cola_desde"])
    return turno


def personas_adelante(turno: Turno) -> int:
    """Cuantos turnos EN_ESPERA del mismo servicio se atienden antes que este."""
    ref = turno.en_cola_desde or turno.creado_en
    qs = (
        Turno.objects.filter(
            servicio=turno.servicio,
            fecha=turno.fecha,
            estado=Turno.Estado.EN_ESPERA,
        )
        .exclude(pk=turno.pk)
        .annotate(orden=Coalesce("en_cola_desde", "creado_en"))
    )
    # Preferentes siempre antes; entre iguales, orden de llegada (en_cola_desde).
    if turno.prioritario:
        return qs.filter(prioritario=True, orden__lt=ref).count()
    adelante_pref = qs.filter(prioritario=True).count()
    adelante_norm = qs.filter(prioritario=False, orden__lt=ref).count()
    return adelante_pref + adelante_norm


# ---------------------------------------------------------------------------
# Ventanilla: abrir / cerrar / pausar
# ---------------------------------------------------------------------------


def ventanilla_de(usuario) -> Ventanilla | None:
    """La ventanilla que el usuario tiene abierta (o None)."""
    return Ventanilla.objects.filter(operador_actual=usuario).first()


def abrir_ventanilla(usuario, numero: int) -> Ventanilla:
    """
    El operador toma una ventanilla. Si ya operaba otra, la libera. Falla si la
    ventanilla la tiene OTRO operador.
    """
    ventanilla = Ventanilla.objects.get(numero=numero, activa=True)
    if (
        ventanilla.operador_actual_id
        and ventanilla.operador_actual_id != usuario.id
        and ventanilla.estado != Ventanilla.Estado.CERRADA
    ):
        raise ValueError(
            f"La ventanilla {numero} ya esta operada por otro usuario."
        )

    # Liberar cualquier otra ventanilla del mismo operador.
    for otra in Ventanilla.objects.filter(operador_actual=usuario).exclude(pk=ventanilla.pk):
        otra.operador_actual = None
        otra.estado = Ventanilla.Estado.CERRADA
        otra.turno_actual = None
        otra.save(update_fields=["operador_actual", "estado", "turno_actual"])

    ventanilla.operador_actual = usuario
    ventanilla.estado = Ventanilla.Estado.LIBRE
    ventanilla.turno_actual = None
    ventanilla.save(update_fields=["operador_actual", "estado", "turno_actual"])
    return ventanilla


def cerrar_ventanilla(ventanilla: Ventanilla) -> None:
    ventanilla.estado = Ventanilla.Estado.CERRADA
    ventanilla.operador_actual = None
    ventanilla.turno_actual = None
    ventanilla.save(update_fields=["estado", "operador_actual", "turno_actual"])


def pausar_ventanilla(ventanilla: Ventanilla) -> None:
    ventanilla.estado = Ventanilla.Estado.PAUSA
    ventanilla.save(update_fields=["estado"])


def reanudar_ventanilla(ventanilla: Ventanilla) -> None:
    ventanilla.estado = Ventanilla.Estado.LIBRE
    ventanilla.save(update_fields=["estado"])


# ---------------------------------------------------------------------------
# Ciclo de atencion de un turno
# ---------------------------------------------------------------------------


def llamar_siguiente(ventanilla: Ventanilla) -> Turno | None:
    """
    Toma atomicamente el proximo turno EN_ESPERA de los servicios que atiende
    la ventanilla (preferentes primero, luego orden de llegada) y lo asigna.
    """
    servicios_ids = list(ventanilla.servicios.values_list("id", flat=True))
    if not servicios_ids:
        return None
    hoy = timezone.localdate()

    with transaction.atomic():
        siguiente = (
            Turno.objects.select_for_update()
            .filter(
                fecha=hoy,
                estado=Turno.Estado.EN_ESPERA,
                servicio_id__in=servicios_ids,
            )
            .annotate(orden=Coalesce("en_cola_desde", "creado_en"))
            .order_by("-prioritario", "orden")
            .first()
        )
        if not siguiente:
            return None

        ahora = timezone.now()
        siguiente.estado = Turno.Estado.LLAMADO
        siguiente.llamado_en = ahora
        siguiente.ventanilla = ventanilla
        siguiente.operador = ventanilla.operador_actual
        siguiente.veces_llamado = 1
        siguiente.save(
            update_fields=[
                "estado", "llamado_en", "ventanilla", "operador", "veces_llamado",
            ]
        )

        ventanilla.estado = Ventanilla.Estado.LLAMANDO
        ventanilla.turno_actual = siguiente
        # Incluimos actualizado_en para que la TV detecte la llamada (y para
        # ordenar bien la lista de "llamando" por mas reciente).
        ventanilla.save(update_fields=["estado", "turno_actual", "actualizado_en"])

    return siguiente


def rellamar(ventanilla: Ventanilla) -> Turno | None:
    """Vuelve a anunciar el turno actual (no cambia de estado, solo cuenta)."""
    turno = ventanilla.turno_actual
    if not turno:
        return None
    turno.veces_llamado = (turno.veces_llamado or 0) + 1
    turno.llamado_en = timezone.now()
    turno.save(update_fields=["veces_llamado", "llamado_en"])
    # "tocar" la ventanilla para que la TV detecte el cambio.
    ventanilla.save(update_fields=["actualizado_en"])
    return turno


def iniciar_atencion(ventanilla: Ventanilla) -> Turno | None:
    turno = ventanilla.turno_actual
    if not turno:
        return None
    turno.estado = Turno.Estado.EN_ATENCION
    turno.inicio_atencion_en = timezone.now()
    turno.save(update_fields=["estado", "inicio_atencion_en"])
    ventanilla.estado = Ventanilla.Estado.OCUPADA
    ventanilla.save(update_fields=["estado"])
    return turno


def finalizar(ventanilla: Ventanilla) -> None:
    turno = ventanilla.turno_actual
    if turno:
        turno.estado = Turno.Estado.ATENDIDO
        if not turno.inicio_atencion_en:
            turno.inicio_atencion_en = timezone.now()
        turno.fin_atencion_en = timezone.now()
        turno.save(update_fields=["estado", "inicio_atencion_en", "fin_atencion_en"])
    ventanilla.estado = Ventanilla.Estado.LIBRE
    ventanilla.turno_actual = None
    ventanilla.save(update_fields=["estado", "turno_actual"])


def marcar_ausente(ventanilla: Ventanilla) -> None:
    turno = ventanilla.turno_actual
    if turno:
        turno.estado = Turno.Estado.AUSENTE
        turno.fin_atencion_en = timezone.now()
        turno.save(update_fields=["estado", "fin_atencion_en"])
    ventanilla.estado = Ventanilla.Estado.LIBRE
    ventanilla.turno_actual = None
    ventanilla.save(update_fields=["estado", "turno_actual"])


def derivar(ventanilla: Ventanilla, servicio_destino: Servicio) -> Turno | None:
    """
    Cierra el turno actual como DERIVADO y crea uno nuevo en el servicio destino
    (preferente, para que el vecino no espere desde cero). Libera la ventanilla.
    """
    turno = ventanilla.turno_actual
    if not turno:
        return None
    turno.estado = Turno.Estado.DERIVADO
    turno.fin_atencion_en = timezone.now()
    turno.save(update_fields=["estado", "fin_atencion_en"])

    nuevo = emitir_turno(
        servicio_destino,
        prioritario=True,
        dni=turno.dni,
        canal=Turno.Canal.MANUAL,
    )
    nuevo.derivado_de = turno
    nuevo.nombre = turno.nombre
    nuevo.cntr_cod = turno.cntr_cod
    nuevo.save(update_fields=["derivado_de", "nombre", "cntr_cod"])

    ventanilla.estado = Ventanilla.Estado.LIBRE
    ventanilla.turno_actual = None
    ventanilla.save(update_fields=["estado", "turno_actual"])
    return nuevo
