"""
Login y perfil de ciudadanos.

Flujo de login en 3 endpoints:

  1. POST /check-dni/   -> chequea Propietarios y dice si pide password,
                           si hay que crear cuenta o si hay que mandar a MPV.
  2. POST /login/       -> { dni, password }, valida contra Ciudadano local.
  3. POST /register/    -> { dni, password }, primer set-up de password.

En todos los casos, tras autenticar:
  - Sincroniza email/celular/direccion desde Propietarios -> Ciudadano (la
    fuente de verdad es Mesa de Partes Virtual).
  - Resuelve cntr_cod desde CONTRIBUYENTES por DNI.
  - Emite JWT.

Si Propietarios no tiene email o id_aspnetusers, el ciudadano NO puede
operar el app: lo mandamos a registrarse en MPV.
"""
from __future__ import annotations

from django.contrib.auth import authenticate
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken

from apps.externos_muni.models import Contribuyentes
from apps.externos_tramites.models import Propietarios

from .models import Ciudadano


LINK_REGISTRO_MPV = (
    "http://mesa-partes-virtual.munibustamante.gob.pe:9090/Account/Register"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _split_nombres(prop: Propietarios) -> tuple[str, str, str]:
    """Devuelve (nombres, apellido_paterno, apellido_materno)."""
    nombres = (prop.pnom_pro or "").strip()
    pat = (prop.pat_pro or "").strip()
    mat = (prop.mat_pro or "").strip()
    if not nombres or not pat:
        partes = (prop.nom_pro or "").strip().split()
        if len(partes) >= 3:
            nombres = nombres or " ".join(partes[:-2])
            pat = pat or partes[-2]
            mat = mat or partes[-1]
        elif len(partes) == 2:
            nombres = nombres or partes[0]
            pat = pat or partes[1]
        elif len(partes) == 1:
            nombres = nombres or partes[0]
    return nombres, pat, mat


def _enmascarar_email(email: str) -> str:
    if not email or "@" not in email:
        return ""
    user, dom = email.split("@", 1)
    if len(user) <= 2:
        prefix = user[0] + "*"
    else:
        prefix = user[0] + "*" * (len(user) - 2) + user[-1]
    return f"{prefix}@{dom}"


def _propietario_por_dni(dni: str) -> Propietarios | None:
    """
    Busca un Propietarios por DNI. Casos a manejar:
      1) Un mismo DNI puede tener N filas en Propietarios (varios predios,
         duplicados, etc.). Si existe alguna con email + id_aspnetusers
         (la cuenta MPV activa), la preferimos sobre cualquier otra.
      2) SQL Server a veces guarda DNI con padding o espacios; usamos
         strip y comparamos exact + iexact.
    """
    if not dni:
        return None
    dni = dni.strip()

    qs = Propietarios.objects.using("tramites_db").filter(dni_pro=dni)

    # Preferimos la fila con email + aspnet (cuenta MPV activa).
    mejor = (
        qs.exclude(email_pro__isnull=True)
        .exclude(email_pro__exact="")
        .exclude(id_aspnetusers__isnull=True)
        .exclude(id_aspnetusers__exact="")
        .first()
    )
    if mejor:
        return mejor

    # Fallback: cualquier fila con ese DNI (aunque le falten datos).
    return qs.first()


def _registrado_en_mpv(prop: Propietarios) -> bool:
    """Tiene email + id_aspnetusers => puede operar."""
    email = (prop.email_pro or "").strip()
    aspnet = (prop.id_aspnetusers or "").strip()
    return bool(email and aspnet)


def _sync_propietario_a_ciudadano(
    prop: Propietarios, ciudadano: Ciudadano
) -> Ciudadano:
    """
    Trae los datos canonicos desde Propietarios (MPV es la fuente de verdad)
    y los pisa en el Ciudadano local. Tambien resuelve cntr_cod.
    """
    nombres, pat, mat = _split_nombres(prop)
    contribuyente = (
        Contribuyentes.objects.using("muni_db")
        .filter(cntrnumdoc=ciudadano.dni, cntranu=" ")
        .only("cntrcod")
        .first()
    )

    cambios = {
        "nombres": nombres or prop.nom_pro or ciudadano.dni,
        "apellido_paterno": pat,
        "apellido_materno": mat,
        "email": (prop.email_pro or "").strip().lower(),
        "celular": (prop.tel_pro or "").strip()[:9],
        "direccion": (prop.dir_rep or prop.cal_pro or "").strip()[:200],
        "cod_pro": prop.cod_pro,
        "cntr_cod": contribuyente.cntrcod if contribuyente else None,
        "verificado": True,
        "fecha_ultima_sync": timezone.now(),
    }
    for k, v in cambios.items():
        setattr(ciudadano, k, v)
    ciudadano.save(update_fields=list(cambios.keys()))
    return ciudadano


def _emitir_tokens(ciudadano: Ciudadano) -> dict:
    refresh = RefreshToken.for_user(ciudadano)
    return {
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "ciudadano": CiudadanoSerializer(ciudadano).data,
    }


# ---------------------------------------------------------------------------
# Serializers expuestos
# ---------------------------------------------------------------------------


class CiudadanoSerializer(serializers.ModelSerializer):
    nombre_completo = serializers.ReadOnlyField()

    class Meta:
        model = Ciudadano
        fields = [
            "id",
            "dni",
            "nombres",
            "apellido_paterno",
            "apellido_materno",
            "nombre_completo",
            "email",
            "celular",
            "direccion",
            "fecha_nacimiento",
            "cod_pro",
            "cntr_cod",
            "es_propietario",
            "verificado",
            "fecha_registro",
        ]
        read_only_fields = [
            "id",
            "cod_pro",
            "cntr_cod",
            "es_propietario",
            "verificado",
            "fecha_registro",
        ]


class CheckDniSerializer(serializers.Serializer):
    """Decide que paso debe mostrar el front segun el estado del DNI."""

    dni = serializers.CharField(min_length=8, max_length=15)

    def validate(self, attrs):
        dni = attrs["dni"].strip()

        prop = _propietario_por_dni(dni)
        if not prop:
            print(f"[check-dni] DNI {dni!r} no encontrado en Propietarios.")
            return {
                "paso": "BLOQUEADO",
                "razon": "no_propietario",
                "mensaje": (
                    "No encontramos tu DNI en el padron de propietarios. "
                    "Para usar el app primero registrate en la Mesa de Partes "
                    "Virtual de la Municipalidad."
                ),
                "link_registro": LINK_REGISTRO_MPV,
            }

        if not _registrado_en_mpv(prop):
            falta_email = not (prop.email_pro or "").strip()
            falta_aspnet = not (prop.id_aspnetusers or "").strip()
            print(
                f"[check-dni] DNI {dni!r} bloqueado. cod_pro={prop.cod_pro!r} "
                f"email_pro={(prop.email_pro or '')!r} "
                f"id_aspnetusers={(prop.id_aspnetusers or '')!r} "
                f"id_usuaext={prop.id_usuaext!r}"
            )
            if falta_email and falta_aspnet:
                razon = "sin_registro_mpv"
                mensaje = (
                    "Estas en el padron pero aun no te has registrado en la "
                    "Mesa de Partes Virtual. Registrate alli para activar tu "
                    "cuenta y poder iniciar tramites desde el app."
                )
            elif falta_email:
                razon = "sin_email"
                mensaje = (
                    "Tu registro municipal no tiene un correo asociado. "
                    "Ingresa a la Mesa de Partes Virtual para completar tu "
                    "perfil."
                )
            else:
                razon = "sin_aspnet"
                mensaje = (
                    "Tu cuenta de Mesa de Partes Virtual no esta activada. "
                    "Termina el registro alli antes de continuar."
                )
            return {
                "paso": "BLOQUEADO",
                "razon": razon,
                "mensaje": mensaje,
                "link_registro": LINK_REGISTRO_MPV,
            }

        print(
            f"[check-dni] DNI {dni!r} OK. cod_pro={prop.cod_pro!r} "
            f"id_aspnetusers={prop.id_aspnetusers!r}"
        )

        # Tiene email + aspnet. Vemos si ya creo password en nuestra app.
        ciudadano = Ciudadano.objects.filter(dni=dni).first()
        nombres, pat, _ = _split_nombres(prop)
        nombre_corto = (nombres.split()[0] if nombres else "").strip()
        email_visible = _enmascarar_email((prop.email_pro or "").strip().lower())

        # Cuidado: Django considera password="" como "usable" (solo checa que
        # no empiece con "!"). Validamos ademas que tenga formato hash real.
        tiene_password_real = (
            ciudadano is not None
            and bool(ciudadano.password)
            and not ciudadano.password.startswith("!")
            and "$" in ciudadano.password
        )

        if tiene_password_real:
            paso = "PASSWORD_LOGIN"
            mensaje = "Ingresa tu contraseña."
        else:
            paso = "PASSWORD_NUEVO"
            mensaje = (
                "Es tu primera vez en el app. Crea una contraseña para tu "
                "cuenta. Tu correo de Mesa de Partes Virtual seguira siendo "
                "el mismo."
            )

        return {
            "paso": paso,
            "razon": "",
            "mensaje": mensaje,
            "nombre": nombre_corto or "ciudadano",
            "apellido_paterno": pat,
            "email_enmascarado": email_visible,
            "link_registro": LINK_REGISTRO_MPV,
        }


class LoginSerializer(serializers.Serializer):
    """Login por DNI + password ya creado en la app."""

    dni = serializers.CharField(min_length=8, max_length=15)
    password = serializers.CharField(write_only=True, min_length=1)

    def validate(self, attrs):
        dni = attrs["dni"].strip()
        password = attrs["password"]

        prop = _propietario_por_dni(dni)
        if not prop or not _registrado_en_mpv(prop):
            raise serializers.ValidationError(
                "Tu cuenta no esta habilitada en Mesa de Partes Virtual. "
                f"Registrate primero en {LINK_REGISTRO_MPV}."
            )

        ciudadano = authenticate(
            request=self.context.get("request"), dni=dni, password=password
        )
        if not ciudadano:
            raise serializers.ValidationError(
                "DNI o contraseña incorrectos."
            )
        if not ciudadano.is_active:
            raise serializers.ValidationError(
                "Cuenta inactiva. Contacta a la municipalidad."
            )

        # Sync de Propietarios -> Ciudadano (email, etc.)
        with transaction.atomic(using="default"):
            _sync_propietario_a_ciudadano(prop, ciudadano)

        return _emitir_tokens(ciudadano)


class RegisterSerializer(serializers.Serializer):
    """
    Primer set-up de password en la app. Solo permitido si el DNI esta en
    Propietarios con email + aspnet, y o bien no existe Ciudadano todavia
    o existe pero no tiene contraseña usable.
    """

    dni = serializers.CharField(min_length=8, max_length=15)
    password = serializers.CharField(write_only=True, min_length=6, max_length=64)

    def validate_password(self, value: str) -> str:
        if value.strip() != value:
            raise serializers.ValidationError(
                "La contraseña no puede empezar o terminar con espacios."
            )
        return value

    def validate(self, attrs):
        dni = attrs["dni"].strip()
        password = attrs["password"]

        prop = _propietario_por_dni(dni)
        if not prop:
            raise serializers.ValidationError(
                "Tu DNI no figura en el padron municipal."
            )
        if not _registrado_en_mpv(prop):
            raise serializers.ValidationError(
                "Debes registrarte primero en Mesa de Partes Virtual: "
                f"{LINK_REGISTRO_MPV}"
            )

        with transaction.atomic(using="default"):
            ciudadano, created = Ciudadano.objects.get_or_create(
                dni=dni,
                defaults={
                    "nombres": (prop.pnom_pro or prop.nom_pro or dni).strip(),
                    "apellido_paterno": (prop.pat_pro or "").strip(),
                    "apellido_materno": (prop.mat_pro or "").strip(),
                    "email": (prop.email_pro or "").strip().lower(),
                },
            )

            # Recien creado o legacy sin password real -> marcar inusable
            # antes de validar. Django considera "" como usable por defecto
            # (solo chequea que no empiece con "!"), asi que normalizamos.
            if created or not (ciudadano.password or "").strip():
                ciudadano.set_unusable_password()
                ciudadano.save(update_fields=["password"])

            if ciudadano.has_usable_password():
                raise serializers.ValidationError(
                    "Esta cuenta ya tiene contraseña. Usa la opcion 'Ingresar'."
                )

            ciudadano.set_password(password)
            ciudadano.save(update_fields=["password"])
            _sync_propietario_a_ciudadano(prop, ciudadano)

        return _emitir_tokens(ciudadano)
