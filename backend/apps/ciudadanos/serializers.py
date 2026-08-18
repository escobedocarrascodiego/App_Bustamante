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


def _existe_en_contribuyentes(dni: str) -> bool:
    """
    Chequea si el DNI tiene fila vigente en CONTRIBUYENTES (muni_db). Lo usamos
    para diferenciar entre:
      - DNI que esta en algun sistema (padron de tramites o de tributos) → ya
        tenemos sus datos basicos, podemos pre-llenar el Ciudadano.
      - DNI que no esta en ningun sistema → el ciudadano nunca fue cliente de
        la municipalidad; necesitamos que escriba sus datos a mano.
    """
    if not dni:
        return False
    return (
        Contribuyentes.objects.using("muni_db")
        .filter(cntrnumdoc=dni.strip(), cntranu=" ")
        .exists()
    )


def _datos_desde_contribuyentes(dni: str) -> dict | None:
    """
    Datos canonicos del padron TRIBUTARIO (CONTRIBUYENTES). Se usa para
    enriquecer el registro cuando el DNI NO esta en Propietarios (MPV) pero SI
    es contribuyente. Sin esto, esa persona quedaba registrada con el DNI como
    nombre. Devuelve None si el DNI no esta en CONTRIBUYENTES.
    """
    if not dni:
        return None
    c = (
        Contribuyentes.objects.using("muni_db")
        .filter(cntrnumdoc=dni.strip(), cntranu=" ")
        .first()
    )
    if not c:
        return None
    nombres = " ".join(
        p for p in [(c.cntrprinom or "").strip(), (c.cntrsegnon or "").strip()] if p
    )
    # Fallback: si no hay nombres estructurados, parteamos el nombre completo
    # (CntrNom suele venir "APELLIDOS NOMBRES").
    if not nombres and (c.cntrnom or "").strip():
        nombres = (c.cntrnom or "").strip()
    return {
        "nombres": nombres or dni,
        "apellido_paterno": (c.cntrapepat or "").strip(),
        "apellido_materno": (c.cntrapemat or "").strip(),
        "email": (c.cntrmail or "").strip().lower(),
        "celular": (c.cntrcelnum or "").strip()[:9],
        "direccion": (c.cntrdireclar or c.cntrdirec or "").strip()[:200],
        "cntr_cod": c.cntrcod,
    }


def _sync_propietario_a_ciudadano(
    prop: Propietarios, ciudadano: Ciudadano
) -> Ciudadano:
    """
    Trae los datos canonicos desde Propietarios (MPV es la fuente de verdad)
    y los pisa en el Ciudadano local. Tambien resuelve cntr_cod.
    """
    nombres, pat, mat = _split_nombres(prop)
    # Segunda fuente: padron TRIBUTARIO (CONTRIBUYENTES). Doble verificacion:
    # la usamos para resolver el cntr_cod Y para rellenar lo que Propietarios
    # no traiga (nombre, apellidos, direccion). Propietarios sigue mandando
    # cuando tiene dato; CONTRIBUYENTES solo cubre los huecos.
    contrib = _datos_desde_contribuyentes(ciudadano.dni) or {}

    prop_email = (prop.email_pro or "").strip().lower()
    prop_celular = (prop.tel_pro or "").strip()[:9]
    prop_direccion = (prop.dir_rep or prop.cal_pro or "").strip()[:200]
    prop_nombres = nombres or (prop.nom_pro or "").strip()

    # `verificado` refleja el estado real de MPV: True solo si el ciudadano
    # esta correctamente registrado en Mesa de Partes Virtual. Asi el banner
    # del frontend (que se muestra cuando verificado=False) sigue apareciendo
    # despues de cada login para usuarios que omitieron MPV, y desaparece
    # automaticamente cuando completan el registro.
    #
    # Para los campos editables por el ciudadano (nombres, apellidos, email,
    # celular, direccion) preferimos el valor de Propietarios SOLO si trae
    # contenido. Si esta vacio conservamos lo que el ciudadano ya escribio.
    # Asi un usuario que entro via "Continuar sin registrarme" y tipeo sus
    # datos a mano no los pierde en cada login.
    #
    # Cuando el ciudadano se registre en MPV, prop.email_pro vendra con su
    # nuevo correo y este si sobreescribira al que el ciudadano habia escrito
    # localmente — que es justo lo que queremos: la fuente de verdad es MPV.
    cambios = {
        "nombres": (
            prop_nombres
            or contrib.get("nombres")
            or ciudadano.nombres
            or ciudadano.dni
        ),
        "apellido_paterno": (
            pat or contrib.get("apellido_paterno") or ciudadano.apellido_paterno
        ),
        "apellido_materno": (
            mat or contrib.get("apellido_materno") or ciudadano.apellido_materno
        ),
        "email": prop_email or contrib.get("email") or ciudadano.email,
        "celular": prop_celular or contrib.get("celular") or ciudadano.celular,
        "direccion": (
            prop_direccion or contrib.get("direccion") or ciudadano.direccion
        ),
        "cod_pro": prop.cod_pro,
        "cntr_cod": contrib.get("cntr_cod") or ciudadano.cntr_cod,
        "verificado": _registrado_en_mpv(prop),
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
        ciudadano = Ciudadano.objects.filter(dni=dni).first()

        # Cuidado: Django considera password="" como "usable" (solo checa que
        # no empiece con "!"). Validamos ademas que tenga formato hash real.
        tiene_password_real = (
            ciudadano is not None
            and bool(ciudadano.password)
            and not ciudadano.password.startswith("!")
            and "$" in ciudadano.password
        )

        # CASO 1: Ya tiene cuenta en el app con password real.
        # No importa si esta o no en MPV — la contraseña del app es de una sola
        # vez. Devolvemos PASSWORD_LOGIN para que solo ingrese su contraseña.
        # Si despues quiere registrarse en MPV, lo hace desde el banner dentro
        # del app (verificar-mpv).
        if tiene_password_real:
            if prop:
                nombres, pat, _ = _split_nombres(prop)
                nombre_corto = (nombres.split()[0] if nombres else "").strip()
                email_visible = _enmascarar_email(
                    (prop.email_pro or "").strip().lower()
                )
            else:
                nombre_corto = (
                    (ciudadano.nombres or "").split()[0]
                    if ciudadano.nombres
                    else ""
                ).strip()
                pat = ciudadano.apellido_paterno or ""
                email_visible = _enmascarar_email(
                    (ciudadano.email or "").strip().lower()
                )
            print(
                f"[check-dni] DNI {dni!r} tiene cuenta en el app -> "
                f"PASSWORD_LOGIN (mpv={'si' if prop and _registrado_en_mpv(prop) else 'no'})"
            )
            return {
                "paso": "PASSWORD_LOGIN",
                "razon": "",
                "mensaje": "Ingresa tu contraseña.",
                "nombre": nombre_corto or "ciudadano",
                "apellido_paterno": pat,
                "email_enmascarado": email_visible,
                "link_registro": LINK_REGISTRO_MPV,
                "requiere_datos_personales": False,
            }

        # CASO 2: No tiene cuenta en el app. Evaluamos el estado en MPV para
        # decidir si lo bloqueamos (DNI no propietario, MPV incompleto) o si
        # lo dejamos crear contraseña directo (PASSWORD_NUEVO).
        if not prop:
            # Si tampoco esta en Contribuyentes, es un ciudadano que nunca
            # tuvo relacion con la municipalidad. Cuando elija "Continuar
            # sin registrarme" el frontend debe pedirle sus datos personales.
            en_contribuyentes = _existe_en_contribuyentes(dni)
            requiere_datos = not en_contribuyentes
            print(
                f"[check-dni] DNI {dni!r} no encontrado en Propietarios. "
                f"contribuyentes={en_contribuyentes!r} requiere_datos={requiere_datos!r}"
            )
            return {
                "paso": "BLOQUEADO",
                "razon": "no_propietario",
                "mensaje": (
                    "No encontramos tu DNI en el padron de propietarios. "
                    "Para usar el app primero registrate en la Mesa de Partes "
                    "Virtual de la Municipalidad."
                ),
                "link_registro": LINK_REGISTRO_MPV,
                "requiere_datos_personales": requiere_datos,
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
            # Aqui esta en Propietarios pero le falta MPV. Ya tenemos sus
            # datos basicos del padron, asi que NO necesitamos pedirlos.
            return {
                "paso": "BLOQUEADO",
                "razon": razon,
                "mensaje": mensaje,
                "link_registro": LINK_REGISTRO_MPV,
                "requiere_datos_personales": False,
            }

        # CASO 3: Tiene email + aspnet en MPV pero todavia no creo password
        # en el app. Lo mandamos a PASSWORD_NUEVO.
        print(
            f"[check-dni] DNI {dni!r} OK. cod_pro={prop.cod_pro!r} "
            f"id_aspnetusers={prop.id_aspnetusers!r}"
        )
        nombres, pat, _ = _split_nombres(prop)
        nombre_corto = (nombres.split()[0] if nombres else "").strip()
        email_visible = _enmascarar_email((prop.email_pro or "").strip().lower())

        return {
            "paso": "PASSWORD_NUEVO",
            "razon": "",
            "mensaje": (
                "Es tu primera vez en el app. Crea una contraseña para tu "
                "cuenta. Tu correo de Mesa de Partes Virtual seguira siendo "
                "el mismo."
            ),
            "nombre": nombre_corto or "ciudadano",
            "apellido_paterno": pat,
            "email_enmascarado": email_visible,
            "link_registro": LINK_REGISTRO_MPV,
            "requiere_datos_personales": False,
        }


class LoginSerializer(serializers.Serializer):
    """Login por DNI + password ya creado en la app."""

    dni = serializers.CharField(min_length=8, max_length=15)
    password = serializers.CharField(write_only=True, min_length=1)

    def validate(self, attrs):
        dni = attrs["dni"].strip()
        password = attrs["password"]

        # No bloqueamos por MPV: el usuario pudo haberse registrado con
        # "Continuar sin registrarme" (RegisterOmitidoSerializer). Su cuenta
        # ya existe en nuestro DB y debe poder loguearse. El sync que sigue
        # marcara `verificado=False` si todavia no se registro en MPV.
        prop = _propietario_por_dni(dni)

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

        # Sync de Propietarios -> Ciudadano (email, cod_pro, verificado, etc.)
        # Solo si encontramos al ciudadano en el padron. Si no esta (DNI
        # no propietario), conservamos los datos actuales del Ciudadano.
        if prop:
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


class RegisterOmitidoSerializer(serializers.Serializer):
    """
    Set-up de password SIN exigir registro en Mesa de Partes Virtual.

    Permite a un ciudadano entrar al app aunque todavia no tenga cuenta MPV,
    para que pueda ver predios, deudas, tarjeta, etc. Marca `verificado=False`
    para que el frontend muestre el banner de "completa tu registro en MPV".

    Tres casos:
      1) DNI en Propietarios → enlaza cod_pro, cntr_cod, nombres del padron.
         Ignora los campos personales que mande el frontend (la fuente de
         verdad es Propietarios).
      2) DNI en Contribuyentes (no en Propietarios) → crea Ciudadano con
         datos genericos; el sync via cntr_cod sucede mas adelante.
      3) DNI en NINGUN sistema → el frontend mando nombres/apellidos/email/
         celular/direccion; los usamos para crear el Ciudadano. Cuando se
         registre en MPV, `_sync_propietario_a_ciudadano` sobreescribe estos
         datos con la fuente canonica.
    """

    dni = serializers.CharField(min_length=8, max_length=15)
    password = serializers.CharField(write_only=True, min_length=6, max_length=64)
    nombres = serializers.CharField(
        required=False, allow_blank=True, max_length=120
    )
    apellido_paterno = serializers.CharField(
        required=False, allow_blank=True, max_length=80
    )
    apellido_materno = serializers.CharField(
        required=False, allow_blank=True, max_length=80
    )
    email = serializers.EmailField(required=False, allow_blank=True)
    celular = serializers.CharField(
        required=False, allow_blank=True, max_length=15
    )
    direccion = serializers.CharField(
        required=False, allow_blank=True, max_length=200
    )

    def validate_password(self, value: str) -> str:
        if value.strip() != value:
            raise serializers.ValidationError(
                "La contraseña no puede empezar o terminar con espacios."
            )
        return value

    def validate(self, attrs):
        dni = attrs["dni"].strip()
        password = attrs["password"]

        prop = _propietario_por_dni(dni)  # puede ser None
        en_contribuyentes = _existe_en_contribuyentes(dni)
        # Cuando el DNI no esta en ningun sistema, exigimos que el frontend
        # haya mandado al menos nombres, apellido_paterno y email.
        sin_padron = not prop and not en_contribuyentes
        if sin_padron:
            faltantes = []
            if not (attrs.get("nombres") or "").strip():
                faltantes.append("nombres")
            if not (attrs.get("apellido_paterno") or "").strip():
                faltantes.append("apellido_paterno")
            if not (attrs.get("email") or "").strip():
                faltantes.append("email")
            if faltantes:
                raise serializers.ValidationError(
                    "Faltan datos obligatorios para crear tu cuenta: "
                    + ", ".join(faltantes)
                    + "."
                )

        # Datos por defecto para el get_or_create. Si tenemos prop usamos su
        # informacion, si no usamos lo que mando el frontend (puede venir
        # vacio si el ciudadano si estaba en Contribuyentes).
        datos_contrib = None
        if prop:
            nombres, pat, mat = _split_nombres(prop)
            nombres_default = nombres or prop.nom_pro or dni
            ap_paterno = pat
            ap_materno = mat
            email = (prop.email_pro or "").strip().lower()
            celular = (prop.tel_pro or "").strip()[:9]
            direccion = (prop.dir_rep or prop.cal_pro or "").strip()[:200]
        else:
            # No esta en Propietarios. Antes de caer a lo que mando el frontend
            # (que puede venir VACIO si el DNI estaba en Contribuyentes y por eso
            # no se pidio el formulario), consultamos el padron TRIBUTARIO. Asi
            # no se registra a un contribuyente con su DNI como nombre.
            datos_contrib = _datos_desde_contribuyentes(dni)
            if datos_contrib:
                nombres_default = datos_contrib["nombres"] or dni
                ap_paterno = datos_contrib["apellido_paterno"]
                ap_materno = datos_contrib["apellido_materno"]
                email = (
                    datos_contrib["email"]
                    or (attrs.get("email") or "").strip().lower()
                )
                celular = (
                    datos_contrib["celular"]
                    or (attrs.get("celular") or "").strip()[:9]
                )
                direccion = (
                    datos_contrib["direccion"]
                    or (attrs.get("direccion") or "").strip()[:200]
                )
            else:
                # Datos escritos a mano. Los nombres SIEMPRE en MAYUSCULAS para
                # mantener el padron uniforme (igual que Propietarios/CONTRIB).
                nombres_default = (attrs.get("nombres") or "").strip().upper() or dni
                ap_paterno = (attrs.get("apellido_paterno") or "").strip().upper()
                ap_materno = (attrs.get("apellido_materno") or "").strip().upper()
                email = (attrs.get("email") or "").strip().lower()
                celular = (attrs.get("celular") or "").strip()[:9]
                direccion = (attrs.get("direccion") or "").strip().upper()[:200]

        with transaction.atomic(using="default"):
            ciudadano, created = Ciudadano.objects.get_or_create(
                dni=dni,
                defaults={
                    "nombres": nombres_default,
                    "apellido_paterno": ap_paterno,
                    "apellido_materno": ap_materno,
                    "email": email,
                    "celular": celular,
                    "direccion": direccion,
                },
            )

            # Si la cuenta ya existia pero le faltaban datos, los completamos
            # con lo que mando el frontend (caso: usuario abandono el flujo
            # a medio camino y vuelve a intentar).
            if not created and not prop:
                cambios_perfil = {}
                # "nombre vacio" o "nombre == DNI" (sintoma del bug previo) se
                # consideran faltantes y se corrigen con el dato del padron.
                nombre_actual = (ciudadano.nombres or "").strip()
                if (not nombre_actual or nombre_actual == dni) and nombres_default:
                    cambios_perfil["nombres"] = nombres_default
                if not (ciudadano.apellido_paterno or "").strip() and ap_paterno:
                    cambios_perfil["apellido_paterno"] = ap_paterno
                if not (ciudadano.apellido_materno or "").strip() and ap_materno:
                    cambios_perfil["apellido_materno"] = ap_materno
                if not (ciudadano.email or "").strip() and email:
                    cambios_perfil["email"] = email
                if not (ciudadano.celular or "").strip() and celular:
                    cambios_perfil["celular"] = celular
                if not (ciudadano.direccion or "").strip() and direccion:
                    cambios_perfil["direccion"] = direccion
                if cambios_perfil:
                    for k, v in cambios_perfil.items():
                        setattr(ciudadano, k, v)
                    ciudadano.save(update_fields=list(cambios_perfil.keys()))

            if created or not (ciudadano.password or "").strip():
                ciudadano.set_unusable_password()
                ciudadano.save(update_fields=["password"])

            if ciudadano.has_usable_password():
                raise serializers.ValidationError(
                    "Esta cuenta ya tiene contraseña. Usa la opcion 'Ingresar'."
                )

            ciudadano.set_password(password)
            ciudadano.save(update_fields=["password"])

            # Si encontramos en Propietarios, sincronizamos pero RE-marcamos
            # verificado=False porque el ciudadano omitio MPV. El banner
            # del frontend pide completar el registro mas tarde.
            if prop:
                _sync_propietario_a_ciudadano(prop, ciudadano)
                ciudadano.verificado = False
                ciudadano.save(update_fields=["verificado"])
            else:
                cambios_finales = ["verificado"]
                ciudadano.verificado = False
                # Si vino del padron tributario, cacheamos su cntr_cod para que
                # deuda/tarjeta lo resuelvan sin depender del fallback por DNI.
                if datos_contrib and datos_contrib.get("cntr_cod"):
                    ciudadano.cntr_cod = datos_contrib["cntr_cod"]
                    cambios_finales.append("cntr_cod")
                ciudadano.save(update_fields=cambios_finales)

        return _emitir_tokens(ciudadano)


class VerificarMpvSerializer(serializers.Serializer):
    """
    Re-chequea si el ciudadano logueado YA se registro en MPV. Si si:
    sincroniza sus datos (email, cod_pro, etc.) y marca verificado=True,
    asi el banner desaparece. Si no: devuelve `mpv_registrado=False` para
    que el frontend muestre "aun no detectamos tu registro".
    """

    def validate(self, attrs):
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            raise serializers.ValidationError("Sesion requerida.")

        ciudadano: Ciudadano = request.user
        prop = _propietario_por_dni(ciudadano.dni)

        if not prop or not _registrado_en_mpv(prop):
            return {
                "mpv_registrado": False,
                "ciudadano": CiudadanoSerializer(ciudadano).data,
                "mensaje": (
                    "Aun no detectamos tu registro en Mesa de Partes Virtual. "
                    "Asegurate de completar el proceso e intenta nuevamente."
                ),
            }

        # MPV ok — sincronizamos y marcamos verificado=True
        with transaction.atomic(using="default"):
            _sync_propietario_a_ciudadano(prop, ciudadano)
            # _sync ya pone verificado=True, pero lo dejamos explicito por claridad
            ciudadano.verificado = True
            ciudadano.save(update_fields=["verificado"])

        ciudadano.refresh_from_db()
        return {
            "mpv_registrado": True,
            "ciudadano": CiudadanoSerializer(ciudadano).data,
            "mensaje": "¡Listo! Tu cuenta esta vinculada con Mesa de Partes Virtual.",
        }
