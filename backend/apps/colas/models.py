"""
Gestor de colas / turnos para las ventanillas de la municipalidad.

Idea central: el TURNO es universal (cualquiera que entra por la puerta recibe
uno, este o no registrado en nuestros sistemas). El DNI es opcional y solo
sirve para "enriquecer" el turno con datos del contribuyente si existe.

El ESTADO de cada ventanilla NO depende del tiempo: lo manejan los EVENTOS que
dispara el ventanillero desde su modulo (llamar, iniciar, finalizar, pausar...).
Los timestamps del turno se guardan solo para METRICAS (espera, atencion), nunca
para controlar el flujo.

Entidades:
  - Servicio   : una cola / tipo de tramite (Pagos, Fraccionamiento, ...).
  - Ventanilla : una ventanilla fisica (1..7) con su estado y su operador.
  - Turno      : el ticket emitido, con su ciclo de vida y timestamps.
"""
from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class Servicio(models.Model):
    """
    Una cola / tipo de atencion. El prefijo arma el codigo del turno
    (ej. prefijo 'P' -> 'P-045'). Una ventanilla puede atender varios.
    """

    nombre = models.CharField(max_length=120)
    prefijo = models.CharField(
        max_length=3,
        help_text="Letra(s) para el codigo del turno. Ej: 'P' -> P-045.",
    )
    descripcion = models.TextField(blank=True)
    color = models.CharField(
        max_length=7,
        blank=True,
        help_text="Color hex para la TV (opcional). Ej: #0B3D91.",
    )
    activo = models.BooleanField(default=True)
    orden = models.IntegerField(default=0)

    class Meta:
        db_table = "colas_servicio"
        ordering = ["orden", "nombre"]
        verbose_name = "Servicio (cola)"
        verbose_name_plural = "Servicios (colas)"

    def __str__(self) -> str:
        return f"{self.nombre} ({self.prefijo})"


class Ventanilla(models.Model):
    """
    Una ventanilla fisica. Su `estado` es un espejo de lo que hace el
    ventanillero: cambia SOLO por sus acciones (no por tiempo).
    """

    class Estado(models.TextChoices):
        CERRADA = "CERRADA", "Cerrada"     # sin operador / fuera de servicio
        LIBRE = "LIBRE", "Libre"           # operador disponible, sin turno
        LLAMANDO = "LLAMANDO", "Llamando"  # llamo un turno, espera que llegue
        OCUPADA = "OCUPADA", "Ocupada"     # atendiendo a alguien
        PAUSA = "PAUSA", "En pausa"        # almuerzo/break: no le caen turnos

    numero = models.IntegerField(unique=True)
    nombre = models.CharField(
        max_length=80, blank=True, help_text="Etiqueta opcional (ej. 'Caja 1')."
    )
    servicios = models.ManyToManyField(
        Servicio, related_name="ventanillas", blank=True,
        help_text="Que colas atiende esta ventanilla.",
    )
    estado = models.CharField(
        max_length=10, choices=Estado.choices, default=Estado.CERRADA
    )
    operador_actual = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="ventanilla_operada",
        help_text="Usuario (ventanillero) que tiene abierta esta ventanilla.",
    )
    turno_actual = models.ForeignKey(
        "Turno",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
        help_text="Turno que esta llamando / atendiendo ahora.",
    )
    activa = models.BooleanField(
        default=True, help_text="Si esta inactiva no aparece en el sistema."
    )
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "colas_ventanilla"
        ordering = ["numero"]
        verbose_name = "Ventanilla"
        verbose_name_plural = "Ventanillas"

    def __str__(self) -> str:
        return self.nombre or f"Ventanilla {self.numero}"

    @property
    def disponible_para_llamar(self) -> bool:
        """Puede tomar el siguiente turno (operador libre, sin turno en curso)."""
        return self.estado == self.Estado.LIBRE


class Turno(models.Model):
    """
    Un ticket. Nace EN_ESPERA y recorre su ciclo segun las acciones del
    ventanillero. Los timestamps alimentan las metricas (no controlan nada).
    """

    class Estado(models.TextChoices):
        RESERVADO = "RESERVADO", "Reservado (en camino)"  # app, aun no presente
        EN_ESPERA = "EN_ESPERA", "En espera"
        LLAMADO = "LLAMADO", "Llamado"
        EN_ATENCION = "EN_ATENCION", "En atención"
        ATENDIDO = "ATENDIDO", "Atendido"
        AUSENTE = "AUSENTE", "Ausente (no se presentó)"
        DERIVADO = "DERIVADO", "Derivado"
        CANCELADO = "CANCELADO", "Cancelado"

    class Canal(models.TextChoices):
        KIOSKO = "KIOSKO", "Kiosko (pantalla táctil)"
        APP = "APP", "App móvil"
        MANUAL = "MANUAL", "Manual (asistente)"

    servicio = models.ForeignKey(
        Servicio, on_delete=models.PROTECT, related_name="turnos"
    )
    fecha = models.DateField(
        default=timezone.localdate,
        help_text="Dia del turno. La numeracion se reinicia cada dia por servicio.",
    )
    numero = models.IntegerField(help_text="Correlativo por servicio y dia.")
    codigo = models.CharField(
        max_length=12, help_text="Codigo visible. Ej: P-045."
    )

    estado = models.CharField(
        max_length=12, choices=Estado.choices, default=Estado.EN_ESPERA
    )
    prioritario = models.BooleanField(
        default=False,
        help_text="Atención preferente (gestante, adulto mayor, discapacidad).",
    )
    canal = models.CharField(
        max_length=8, choices=Canal.choices, default=Canal.KIOSKO
    )

    # --- Datos del contribuyente (OPCIONALES — enriquecimiento) ---
    dni = models.CharField(max_length=15, blank=True)
    nombre = models.CharField(max_length=200, blank=True)
    cntr_cod = models.IntegerField(
        null=True, blank=True, help_text="CntrCod si se ubico en CONTRIBUYENTES."
    )
    ciudadano = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="turnos_colas",
        help_text="Usuario del app que saco el turno (si vino por el app).",
    )

    # --- Atención ---
    ventanilla = models.ForeignKey(
        Ventanilla,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="turnos",
    )
    operador = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="turnos_atendidos",
    )

    # --- Timestamps (solo para metricas) ---
    creado_en = models.DateTimeField(default=timezone.now)       # emitido / reservado
    en_cola_desde = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "Momento en que entro a la fila ACTIVA. Para walk-in es = creado_en; "
            "para reservas del app es el 'Ya llegué'. Se ordena por esto para que "
            "la posicion sea justa por llegada, no por hora de reserva."
        ),
    )
    llamado_en = models.DateTimeField(null=True, blank=True)     # primera llamada
    inicio_atencion_en = models.DateTimeField(null=True, blank=True)
    fin_atencion_en = models.DateTimeField(null=True, blank=True)
    veces_llamado = models.IntegerField(default=0)

    # --- Derivación ---
    derivado_de = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="derivaciones",
        help_text="Turno original del que provino esta derivacion.",
    )

    class Meta:
        db_table = "colas_turno"
        ordering = ["fecha", "servicio", "numero"]
        constraints = [
            models.UniqueConstraint(
                fields=["servicio", "fecha", "numero"],
                name="uniq_turno_servicio_fecha_numero",
            )
        ]
        indexes = [
            models.Index(fields=["fecha", "estado"]),
            models.Index(fields=["dni"]),
        ]
        verbose_name = "Turno"
        verbose_name_plural = "Turnos"

    def __str__(self) -> str:
        return f"{self.codigo} ({self.get_estado_display()})"

    # --- Metricas (derivadas, no se almacenan) ---
    @property
    def espera_segundos(self) -> int | None:
        """Segundos desde que se emitio hasta que fue llamado."""
        if not self.llamado_en:
            return None
        return int((self.llamado_en - self.creado_en).total_seconds())

    @property
    def atencion_segundos(self) -> int | None:
        """Segundos que duro la atencion."""
        if not (self.inicio_atencion_en and self.fin_atencion_en):
            return None
        return int((self.fin_atencion_en - self.inicio_atencion_en).total_seconds())
