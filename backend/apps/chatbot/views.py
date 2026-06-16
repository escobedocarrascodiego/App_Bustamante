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

from django.db import models
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.authentication import JWTAuthentication

from .matching import buscar_faq
from .models import ConversacionSesion, Faq, Gerencia, MensajeChat
from .serializers import FaqMiniSerializer, GerenciaSerializer

RESPUESTA_NO_ENCONTRADA = (
    "No encontré una respuesta exacta para eso. Intenta con otras palabras "
    "(por ejemplo el nombre del trámite) o elige una de las preguntas "
    "frecuentes del menú. También puedes llamar a nuestra central en horario "
    "de lunes a viernes de 8:00 a 16:30."
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


# La busqueda de FAQs vive en apps.chatbot.matching (scoring por tokens).
# `buscar_faq` se importa arriba.


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


class GerenciaFaqsView(APIView):
    """
    GET /api/chatbot/gerencias/<id>/faqs/ — preguntas frecuentes de una
    gerencia (id + pregunta). El frontend las muestra como BOTONES de menu de
    segundo nivel: al presionar uno, llama a /mensaje/ con `faq_id` y recibe la
    respuesta directa (sin que el vecino tenga que escribir).
    """

    permission_classes = [AllowAny]
    authentication_classes: list = []

    def get(self, request, gerencia_id: int):
        if not Gerencia.objects.filter(id=gerencia_id, activo=True).exists():
            return Response(
                {"detail": "Gerencia no encontrada o inactiva."},
                status=status.HTTP_404_NOT_FOUND,
            )
        faqs = (
            Faq.objects.filter(gerencia_id=gerencia_id, activo=True)
            .order_by("-veces_consultada", "id")
        )
        data = FaqMiniSerializer(faqs, many=True).data
        return Response({"gerencia_id": gerencia_id, "faqs": data},
                        status=status.HTTP_200_OK)


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

        # 2. Resolver la FAQ:
        #    a) Si viene `faq_id` (el usuario presiono un boton del menu de
        #       segundo nivel) respondemos esa FAQ directamente — cero error.
        #    b) Si no, usamos el scoring por tokens sobre la gerencia.
        faq = None
        faq_id_raw = request.data.get("faq_id")
        if faq_id_raw is not None:
            try:
                faq_id = int(faq_id_raw)
            except (TypeError, ValueError):
                faq_id = None
            if faq_id is not None:
                qs = Faq.objects.filter(id=faq_id, activo=True)
                if gerencia_id is not None:
                    qs = qs.filter(gerencia_id=gerencia_id)
                faq = qs.first()

        if faq is None:
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
