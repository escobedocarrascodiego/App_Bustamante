from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models


dni_validator = RegexValidator(r"^\d{8}$", "El DNI debe tener exactamente 8 digitos.")
celular_validator = RegexValidator(r"^\d{9}$", "El celular debe tener 9 digitos.")


class CiudadanoManager(BaseUserManager):
    def create_user(self, dni, password=None, **extra_fields):
        if not dni:
            raise ValueError("El DNI es obligatorio")
        extra_fields.setdefault("is_active", True)
        user = self.model(dni=dni, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, dni, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Un superusuario debe tener is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Un superusuario debe tener is_superuser=True")
        return self.create_user(dni, password, **extra_fields)


class Ciudadano(AbstractBaseUser, PermissionsMixin):
    dni = models.CharField("DNI", max_length=8, unique=True, validators=[dni_validator])
    nombres = models.CharField(max_length=120)
    apellido_paterno = models.CharField(max_length=80)
    apellido_materno = models.CharField(max_length=80, blank=True)
    email = models.EmailField(blank=True)
    celular = models.CharField(max_length=9, blank=True, validators=[celular_validator])
    direccion = models.CharField(max_length=200, blank=True)
    fecha_nacimiento = models.DateField(null=True, blank=True)

    cod_pro = models.CharField(
        max_length=10,
        blank=True,
        null=True,
        db_index=True,
        help_text="Codigo del Propietario en dbControl.Propietarios (tramites_db).",
    )
    cntr_cod = models.IntegerField(
        null=True,
        blank=True,
        db_index=True,
        help_text="CntrCod del contribuyente en MuniJLByR.CONTRIBUYENTES. Null si no es contribuyente.",
    )
    es_propietario = models.BooleanField(
        default=False,
        help_text="Tiene predios vigentes en el año actual. Habilita BustaCard y pagos.",
    )

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    verificado = models.BooleanField(
        default=False,
        help_text="Indica si el DNI fue validado contra padron municipal.",
    )
    fecha_registro = models.DateTimeField(auto_now_add=True)
    fecha_ultima_sync = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Ultima vez que se sincronizaron datos desde Propietarios/Contribuyentes.",
    )

    objects = CiudadanoManager()

    USERNAME_FIELD = "dni"
    REQUIRED_FIELDS = ["nombres", "apellido_paterno"]

    class Meta:
        verbose_name = "Ciudadano"
        verbose_name_plural = "Ciudadanos"
        ordering = ["apellido_paterno", "apellido_materno", "nombres"]

    def __str__(self):
        return f"{self.dni} - {self.nombre_completo}"

    @property
    def nombre_completo(self):
        partes = [self.nombres, self.apellido_paterno, self.apellido_materno]
        return " ".join(p for p in partes if p)

    def get_short_name(self):
        return self.nombres.split()[0] if self.nombres else self.dni

    def get_full_name(self):
        return self.nombre_completo
