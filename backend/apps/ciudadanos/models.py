from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.validators import RegexValidator
from django.db import models


dni_validator = RegexValidator(r"^\d{8}$", "El DNI debe tener exactamente 8 digitos.")
celular_validator = RegexValidator(r"^\d{9}$", "El celular debe tener 9 digitos.")


class CiudadanoManager(BaseUserManager):
    """
    Manager del modelo Ciudadano.

    - `create_user(dni, ...)`: ciudadano normal. El DNI es obligatorio.
    - `create_superuser(dni, ...)`: superusuario para el admin de Django.
      Django llama esto pasando el USERNAME_FIELD (dni) como primer arg.
      Como los superusuarios del admin no son ciudadanos reales, el `dni`
      acepta cualquier string corto (ej. "admin"); el `username` aparte
      se setea explicitamente con `--username` o desde el shell.
    """

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
        # Nombres por default para no obligar a tipearlos en el prompt:
        extra_fields.setdefault("nombres", extra_fields.get("username") or "Admin")
        extra_fields.setdefault("apellido_paterno", "Sistema")
        if extra_fields.get("is_staff") is not True:
            raise ValueError("Un superusuario debe tener is_staff=True")
        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Un superusuario debe tener is_superuser=True")
        # Si el caller no paso username explicito, lo derivamos del dni (que
        # tipicamente sera el mismo: "admin") para que tambien pueda loguear
        # via el campo username.
        if "username" not in extra_fields:
            extra_fields["username"] = dni
        return self.create_user(dni, password, **extra_fields)


class Ciudadano(AbstractBaseUser, PermissionsMixin):
    # Nota: el `dni` se relaja a 15 chars para admitir el DNI placeholder
    # de superusuarios admin ("ADM..." de 8+ chars). El validator solo se
    # aplica a usuarios reales via forms — el ORM no lo valida en update.
    dni = models.CharField("DNI", max_length=15, unique=True, validators=[dni_validator])
    username = models.CharField(
        "Usuario admin",
        max_length=150,
        blank=True,
        null=True,
        unique=True,
        help_text=(
            "Nombre de usuario para acceder al admin de Django. Vacio para "
            "ciudadanos normales — solo lo usan los superusuarios."
        ),
    )
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

    # USERNAME_FIELD = dni para el app movil (login ciudadano por DNI).
    # Para superusuarios del admin, el campo `username` se usa via el
    # backend custom `UsernameOrDniBackend` y `createsuperuser` lo recibe
    # como prompt en lugar del DNI (ver CiudadanoManager.create_superuser).
    USERNAME_FIELD = "dni"
    REQUIRED_FIELDS: list[str] = []

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
