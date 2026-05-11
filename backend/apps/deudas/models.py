from decimal import Decimal

from django.conf import settings
from django.db import models


class TipoDeuda(models.TextChoices):
    PREDIAL = "PREDIAL", "Impuesto predial"
    ARBITRIOS = "ARBITRIOS", "Arbitrios municipales"
    MULTA = "MULTA", "Multa administrativa"
    PAPELETA = "PAPELETA", "Papeleta de transito"
    OTRO = "OTRO", "Otro concepto"


class EstadoDeuda(models.TextChoices):
    PENDIENTE = "PENDIENTE", "Pendiente"
    VENCIDA = "VENCIDA", "Vencida"
    PAGADA = "PAGADA", "Pagada"
    FRACCIONADA = "FRACCIONADA", "Fraccionada"


class Deuda(models.Model):
    ciudadano = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="deudas",
    )
    tipo = models.CharField(max_length=20, choices=TipoDeuda.choices)
    concepto = models.CharField(max_length=200)
    anio = models.PositiveSmallIntegerField("Anio fiscal")
    periodo = models.CharField(
        max_length=20,
        blank=True,
        help_text="Ej: 'Trimestre 1', 'Enero', vacio para anual.",
    )
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    interes = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    descuento = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    fecha_emision = models.DateField()
    fecha_vencimiento = models.DateField()
    estado = models.CharField(
        max_length=20,
        choices=EstadoDeuda.choices,
        default=EstadoDeuda.PENDIENTE,
    )
    codigo_referencia = models.CharField(max_length=60, unique=True)

    class Meta:
        ordering = ["-anio", "tipo", "periodo"]
        verbose_name = "Deuda"
        verbose_name_plural = "Deudas"

    def __str__(self):
        return f"{self.get_tipo_display()} {self.anio} - {self.ciudadano.dni}"

    @property
    def total(self) -> Decimal:
        return (self.monto + self.interes - self.descuento).quantize(Decimal("0.01"))


class Pago(models.Model):
    MEDIO_CHOICES = [
        ("CAJA", "Caja municipal"),
        ("BANCO", "Pago en banco"),
        ("APP", "Aplicativo movil"),
        ("WEB", "Portal web"),
    ]

    deuda = models.ForeignKey(Deuda, on_delete=models.CASCADE, related_name="pagos")
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateTimeField(auto_now_add=True)
    medio = models.CharField(max_length=10, choices=MEDIO_CHOICES, default="APP")
    numero_operacion = models.CharField(max_length=60, blank=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "Pago"
        verbose_name_plural = "Pagos"

    def __str__(self):
        return f"Pago {self.monto} - {self.deuda.codigo_referencia}"
