"""
Endpoints del chatbot.

  GET  /api/chatbot/gerencias/         — lista gerencias activas (publico)
  POST /api/chatbot/sesion/nueva/      — crea sesion (publico, opcional JWT)
  POST /api/chatbot/mensaje/           — manda pregunta, devuelve respuesta (publico)
  GET  /api/chatbot/sesion/historial/  — lista mensajes de una sesion (publico)

Diseño:
- Endpoints publicos (AllowAny) porque un vecino sin cuenta tambien puede
  consultar FAQs. Si el request trae JWT valido, asociamos el ciudadano
  a la sesion para reportes/admin.
- Busqueda: SQL Server Full-Text con CONTAINS() sobre (pregunta, keywords).
  Requiere indice Full-Text creado manualmente (ver comentario en models.py).
  Acepta `gerencia_id` opcional para restringir la busqueda a una gerencia.
- Si CONTAINS() falla (Full-Text no instalado, sin indice, etc.) caemos a
  un fallback LIKE simple para no devolver siempre "no encontre informacion".
"""
from __future__ import annotations

import re

from django.db import connection, models
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from .models import ConversacionSesion, Faq, Gerencia, MensajeChat
from .serializers import GerenciaSerializer

RESPUESTA_NO_ENCONTRADA = (
    "No encontré información sobre eso. Te recomiendo comunicarte con la "
    "Gerencia correspondiente o llamar a nuestra central telefónica en "
    "horario de lunes a viernes de 8:00 a 16:30."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _user_si_autenticado(request):
    """
    Como los endpoints son AllowAny, DRF no autentica automaticamente. Hacemos
    un intento manual con JWT: si hay header valido devolvemos el user, si no
    devolvemos None (sesion anonima).
    """
    auth = JWTAuthentication()
    try:
        result = auth.authenticate(request)
    except Exception:
        return None
    if not result:
        return None
    user, _token = result
    return user if getattr(user, "is_authenticated", False) else None


# Caracteres permitidos en cada palabra de la query Full-Text: letras
# (incluyendo acentos), digitos, guion. Cualquier otra cosa se descarta.
_PALABRA_RE = re.compile(r"[\wáéíóúñÁÉÍÓÚÑ\-]+", re.UNICODE)


def _palabras_clave(texto: str, min_len: int = 3, max_palabras: int = 12) -> list[str]:
    """Extrae palabras "buscables" del mensaje del usuario."""
    if not texto:
        return []
    crudas = _PALABRA_RE.findall(texto.lower())
    # Sanea comillas y dedupe preservando orden
    vistas: set[str] = set()
    resultado: list[str] = []
    for w in crudas:
        if len(w) < min_len:
            continue
        if w in vistas:
            continue
        vistas.add(w)
        resultado.append(w)
        if len(resultado) >= max_palabras:
            break
    return resultado


def _buscar_faq_fulltext(
    palabras: list[str], gerencia_id: int | None = None
) -> Faq | None:
    """
    Busqueda principal: CONTAINS() de SQL Server sobre (pregunta, keywords).
    Construye la expresion '"palabra1" OR "palabra2" OR ...' y ordena por
    veces_consultada DESC para priorizar las preguntas mas populares. Si
    `gerencia_id` esta seteado, restringe la busqueda a esa gerencia.
    Devuelve None si falla por cualquier motivo (sin Full-Text, sintaxis, etc).
    """
    if not palabras:
        return None
    expr = " OR ".join(f'"{w}"' for w in palabras)

    if gerencia_id is not None:
        sql = (
            "SELECT TOP 1 id FROM chatbot_faq "
            "WHERE activo = 1 "
            "  AND gerencia_id = %s "
            "  AND CONTAINS((pregunta, keywords), %s) "
            "ORDER BY veces_consultada DESC, id ASC"
        )
        params: list = [gerencia_id, expr]
    else:
        sql = (
            "SELECT TOP 1 id FROM chatbot_faq "
            "WHERE activo = 1 "
            "  AND CONTAINS((pregunta, keywords), %s) "
            "ORDER BY veces_consultada DESC, id ASC"
        )
        params = [expr]

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            row = cursor.fetchone()
    except Exception as exc:  # pragma: no cover
        print(f"[chatbot] CONTAINS() fallo: {exc!r} — caemos al fallback LIKE.")
        return None
    if not row:
        return None
    return Faq.objects.filter(id=row[0]).first()


def _buscar_faq_like(
    palabras: list[str], gerencia_id: int | None = None
) -> Faq | None:
    """
    Fallback cuando Full-Text no esta disponible. Hace OR de LIKE sobre
    pregunta y keywords. Menos eficiente pero funciona sin indice. Si
    `gerencia_id` esta seteado, restringe la busqueda a esa gerencia.
    """
    if not palabras:
        return None
    qs = Faq.objects.filter(activo=True)
    if gerencia_id is not None:
        qs = qs.filter(gerencia_id=gerencia_id)
    cond = models.Q()
    for w in palabras:
        cond |= models.Q(pregunta__icontains=w) | models.Q(keywords__icontains=w)
    return (
        qs.filter(cond)
        .order_by("-veces_consultada", "id")
        .first()
    )


def buscar_faq(texto_usuario: str, gerencia_id: int | None = None) -> Faq | None:
    """
    API publica de busqueda: intenta Full-Text, cae a LIKE.
    Si `gerencia_id` esta seteado, filtra a esa gerencia.
    """
    palabras = _palabras_clave(texto_usuario)
    if not palabras:
        return None
    faq = _buscar_faq_fulltext(palabras, gerencia_id=gerencia_id)
    if faq:
        return faq
    return _buscar_faq_like(palabras, gerencia_id=gerencia_id)


# ---------------------------------------------------------------------------
# Views
# ---------------------------------------------------------------------------


class GerenciasView(APIView):
    """GET /api/chatbot/gerencias/ — lista gerencias activas para el selector."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        gerencias = Gerencia.objects.filter(activo=True).order_by("orden", "nombre")
        data = GerenciaSerializer(gerencias, many=True).data
        return Response(data, status=status.HTTP_200_OK)


class NuevaSesionView(APIView):
    """POST /api/chatbot/sesion/nueva/ — crea una sesion (anonima u asociada)."""

    permission_classes = [AllowAny]
    authentication_classes: list = []  # no falla si el JWT esta vencido

    def post(self, request):
        usuario = _user_si_autenticado(request)
        sesion = ConversacionSesion.objects.create(ciudadano=usuario)
        return Response(
            {"sesion_id": str(sesion.sesion_id)},
            status=status.HTTP_201_CREATED,
        )


class MensajeView(APIView):
    """POST /api/chatbot/mensaje/ — recibe pregunta, devuelve respuesta."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def post(self, request):
        sesion_id = request.data.get("sesion_id")
        mensaje = (request.data.get("mensaje") or "").strip()

        # gerencia_id es opcional. Si viene, debe ser un int valido y existir.
        gerencia_id_raw = request.data.get("gerencia_id")
        gerencia_id: int | None = None
        if gerencia_id_raw is not None:
            try:
                gerencia_id = int(gerencia_id_raw)
            except (TypeError, ValueError):
                return Response(
                    {"detail": "gerencia_id debe ser entero."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if not Gerencia.objects.filter(id=gerencia_id, activo=True).exists():
                return Response(
                    {"detail": "Gerencia no encontrada o inactiva."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        if not sesion_id or not mensaje:
            return Response(
                {"detail": "sesion_id y mensaje son requeridos."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sesion = ConversacionSesion.objects.filter(sesion_id=sesion_id).first()
        if not sesion:
            return Response(
                {"detail": "Sesion no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # 1. Guardar mensaje del usuario
        MensajeChat.objects.create(
            sesion=sesion,
            rol=MensajeChat.Rol.USUARIO,
            contenido=mensaje,
        )

        # 2. Buscar respuesta (con filtro de gerencia si llego)
        faq = buscar_faq(mensaje, gerencia_id=gerencia_id)

        if faq is not None:
            respuesta = faq.respuesta
            encontrado = True
            # Incremento atomico con F() evita race conditions
            Faq.objects.filter(pk=faq.pk).update(
                veces_consultada=models.F("veces_consultada") + 1
            )
        else:
            respuesta = RESPUESTA_NO_ENCONTRADA
            encontrado = False

        # 3. Guardar mensaje del bot
        MensajeChat.objects.create(
            sesion=sesion,
            rol=MensajeChat.Rol.BOT,
            contenido=respuesta,
            faq_origen=faq,
        )

        # 4. Tocar ultimo_mensaje_en (auto_now se dispara con save())
        sesion.save(update_fields=["ultimo_mensaje_en"])

        return Response(
            {
                "respuesta": respuesta,
                "encontrado": encontrado,
                "sesion_id": str(sesion.sesion_id),
            },
            status=status.HTTP_200_OK,
        )


class HistorialView(APIView):
    """GET /api/chatbot/sesion/historial/?sesion_id=<uuid> — mensajes de la sesion."""

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request):
        sesion_id = request.query_params.get("sesion_id")
        if not sesion_id:
            return Response(
                {"detail": "sesion_id es requerido."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        sesion = ConversacionSesion.objects.filter(sesion_id=sesion_id).first()
        if not sesion:
            return Response(
                {"detail": "Sesion no encontrada."},
                status=status.HTTP_404_NOT_FOUND,
            )

        mensajes = list(
            sesion.mensajes.order_by("creado_en").values(
                "rol", "contenido", "creado_en"
            )
        )
        return Response({"mensajes": mensajes}, status=status.HTTP_200_OK)
