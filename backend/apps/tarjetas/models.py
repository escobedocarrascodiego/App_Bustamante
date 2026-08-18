import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


def generar_codigo_tarjeta():
    return f"JLBR-{secrets.token_hex(4).upper()}"


class Beneficio(models.Model):
    CATEGORIAS = [
        ("CULTURA", "Cultura"),
        ("DEPORTE", "Deporte"),
        ("SALUD", "Salud"),
        ("EDUCACION", "Educacion"),
        ("RECREO", "Recreacion"),
        ("OTRO", "Otro"),
    ]

    nombre = models.CharField(max_length=150)
    descripcion = models.TextField(blank=True)
    categoria = models.CharField(max_length=20, choices=CATEGORIAS, default="OTRO")
    lugar = models.CharField(max_length=150, blank=True)
    direccion = models.CharField(max_length=200, blank=True)
    activo = models.BooleanField(default=True)
    gratuito = models.BooleanField(default=True)
    horario = models.CharField(max_length=120, blank=True)
    imagen = models.ImageField(upload_to="beneficios/", blank=True, null=True)

    class Meta:
        ordering = ["categoria", "nombre"]
        verbose_name = "Beneficio"
        verbose_name_plural = "Beneficios"

    def __str__(self):
        return self.nombre


class TarjetaCiudadana(models.Model):
    codigo = models.CharField(max_length=20, unique=True, default=generar_codigo_tarjeta)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    ciudadano = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="tarjeta",
    )
    fecha_emision = models.DateTimeField(auto_now_add=True)
    fecha_vencimiento = models.DateField()
    activa = models.BooleanField(default=True)
    bloqueada = models.BooleanField(default=False)
    motivo_bloqueo = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "Tarjeta ciudadana"
        verbose_name_plural = "Tarjetas ciudadanas"

    def save(self, *args, **kwargs):
        if not self.pk and not self.fecha_vencimiento:
            # La BustaCard vence el ULTIMO DIA del año en que se emite, no un
            # año exacto. Si se saca el 30/12/2026, igual vence 31/12/2026.
            self.fecha_vencimiento = timezone.localdate().replace(month=12, day=31)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.codigo} ({self.ciudadano.dni})"

    @property
    def vigente(self) -> bool:
        return (
            self.activa
            and not self.bloqueada
            and self.fecha_vencimiento >= timezone.now().date()
        )


class BustaCardVentanilla(models.Model):
    """
    Registro de BustaCards emitidas manualmente desde la VENTANILLA
    (modulo /genera_bustacard, uso interno). A diferencia de TarjetaCiudadana,
    NO requiere que el contribuyente tenga cuenta en el app: guarda los datos
    del contribuyente directamente (desde CONTRIBUYENTES). Sirve para llevar
    el historial de quien recibio su tarjeta impresa.

    Un registro por (contribuyente, ejercicio/año): re-imprimir la misma card
    el mismo año no genera duplicados.
    """
    cntrcod = models.IntegerField(db_index=True)
    dni = models.CharField(max_length=15, db_index=True)
    nombre = models.CharField(max_length=200)
    codigo = models.CharField(max_length=30)
    anio = models.IntegerField(help_text="Ejercicio de la tarjeta")
    fecha_emision = models.DateTimeField(default=timezone.now)
    fecha_vencimiento = models.DateField()
    emitido_por = models.CharField(
        max_length=150, blank=True, help_text="Usuario administrador que la emitio"
    )

    class Meta:
        verbose_name = "BustaCard de ventanilla"
        verbose_name_plural = "BustaCards de ventanilla"
        ordering = ["-fecha_emision"]
        constraints = [
            models.UniqueConstraint(
                fields=["cntrcod", "anio"], name="uniq_bustacard_ventanilla_cntrcod_anio"
            )
        ]

    def __str__(self):
        return f"{self.codigo} - {self.dni} ({self.anio})"

    @property
    def vigente(self) -> bool:
        return self.fecha_vencimiento >= timezone.now().date()


class UsoBeneficio(models.Model):
    tarjeta = models.ForeignKey(
        TarjetaCiudadana, on_delete=models.CASCADE, related_name="usos"
    )
    beneficio = models.ForeignKey(
        Beneficio, on_delete=models.PROTECT, related_name="usos"
    )
    fecha = models.DateTimeField(auto_now_add=True)
    observacion = models.CharField(max_length=200, blank=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Uso de beneficio"
        verbose_name_plural = "Usos de beneficios"

    def __str__(self):
        return f"{self.tarjeta.codigo} - {self.beneficio.nombre}"
