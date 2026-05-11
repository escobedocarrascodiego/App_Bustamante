import uuid

from django.conf import settings
from django.db import models


class AreaMunicipal(models.Model):
    nombre = models.CharField(max_length=120, unique=True)
    siglas = models.CharField(max_length=20, blank=True)
    responsable = models.CharField(max_length=120, blank=True)

    class Meta:
        verbose_name = "Area municipal"
        verbose_name_plural = "Areas municipales"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class TipoTramite(models.Model):
    """Entrada del TUPA: tramites que el ciudadano puede iniciar."""

    codigo = models.CharField(max_length=20, unique=True)
    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    area = models.ForeignKey(
        AreaMunicipal,
        on_delete=models.PROTECT,
        related_name="tipos_tramite",
    )
    requisitos = models.TextField(
        blank=True,
        default="",
        help_text="Un requisito por linea.",
    )
    costo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    dias_habiles = models.PositiveSmallIntegerField(
        default=15,
        help_text="Plazo maximo segun TUPA.",
    )
    activo = models.BooleanField(default=True)

    class Meta:
        ordering = ["area", "nombre"]
        verbose_name = "Tipo de tramite (TUPA)"
        verbose_name_plural = "Tipos de tramite (TUPA)"

    def __str__(self):
        return f"{self.codigo} - {self.nombre}"

    @property
    def requisitos_list(self) -> list[str]:
        return [r.strip() for r in (self.requisitos or "").splitlines() if r.strip()]


class EstadoExpediente(models.TextChoices):
    INGRESADO = "INGRESADO", "Ingresado"
    EN_REVISION = "EN_REVISION", "En revision"
    OBSERVADO = "OBSERVADO", "Observado"
    APROBADO = "APROBADO", "Aprobado"
    RECHAZADO = "RECHAZADO", "Rechazado"
    ARCHIVADO = "ARCHIVADO", "Archivado"


class Expediente(models.Model):
    numero = models.CharField(max_length=30, unique=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    tipo = models.ForeignKey(
        TipoTramite,
        on_delete=models.PROTECT,
        related_name="expedientes",
    )
    ciudadano = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="expedientes",
    )
    asunto = models.CharField(max_length=200)
    detalle = models.TextField(blank=True)
    estado = models.CharField(
        max_length=20,
        choices=EstadoExpediente.choices,
        default=EstadoExpediente.INGRESADO,
    )
    fecha_ingreso = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)
    fecha_estimada = models.DateField(null=True, blank=True)

    class Meta:
        ordering = ["-fecha_ingreso"]
        verbose_name = "Expediente"
        verbose_name_plural = "Expedientes"

    def __str__(self):
        return f"Exp. {self.numero} ({self.get_estado_display()})"


class SeguimientoExpediente(models.Model):
    expediente = models.ForeignKey(
        Expediente, on_delete=models.CASCADE, related_name="seguimientos"
    )
    estado = models.CharField(max_length=20, choices=EstadoExpediente.choices)
    comentario = models.TextField(blank=True)
    area = models.ForeignKey(
        AreaMunicipal,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="seguimientos",
    )
    fecha = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Seguimiento"
        verbose_name_plural = "Seguimientos"

    def __str__(self):
        return f"{self.expediente.numero} - {self.get_estado_display()}"
