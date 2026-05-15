"""
Modelos del chatbot rule-based de la Municipalidad.

Catalogo de Gerencias + Faq (preguntas frecuentes) cargado desde admin.
Cada conversacion del ciudadano se guarda como ConversacionSesion con
sus MensajeChat asociados (usuario / bot).

----------------------------------------------------------------------
SQL para Full-Text Search (correr UNA SOLA VEZ en SQL Server)
----------------------------------------------------------------------

El endpoint POST /api/chatbot/mensaje/ usa CONTAINS() sobre las columnas
`pregunta` y `keywords` de `chatbot_faq`. CONTAINS() requiere un indice
Full-Text creado previamente. Despues de correr `migrate`, ejecutar en
SSMS (apuntando a la BD `dbbusta_app`):

    -- 1. Crear el catalogo si no existe
    IF NOT EXISTS (SELECT 1 FROM sys.fulltext_catalogs WHERE name = 'chatbot_catalog')
    BEGIN
        CREATE FULLTEXT CATALOG chatbot_catalog AS DEFAULT;
    END;

    -- 2. Encontrar el nombre del PK que Django genero para chatbot_faq
    --    (suele ser algo como PK__chatbot___3213E83F...). Si querias un
    --    nombre fijo, usar el SELECT siguiente para descubrirlo:
    SELECT name
    FROM sys.indexes
    WHERE object_id = OBJECT_ID('chatbot_faq') AND is_primary_key = 1;

    -- 3. Crear el indice Full-Text. Reemplazar <NOMBRE_PK> por el de arriba.
    CREATE FULLTEXT INDEX ON chatbot_faq(pregunta, keywords)
    KEY INDEX <NOMBRE_PK>
    ON chatbot_catalog
    WITH STOPLIST = SYSTEM;

Si el server no tiene Full-Text habilitado, el endpoint de mensaje
captura el error y devuelve la respuesta "no encontre informacion".
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class Gerencia(models.Model):
    """Gerencia / area municipal a la que pertenecen las FAQs."""

    nombre = models.CharField(max_length=200)
    descripcion = models.TextField(blank=True)
    activo = models.BooleanField(default=True)
    orden = models.IntegerField(default=0)

    class Meta:
        app_label = "chatbot"
        db_table = "chatbot_gerencia"
        ordering = ["orden", "nombre"]
        verbose_name = "Gerencia"
        verbose_name_plural = "Gerencias"

    def __str__(self) -> str:
        return self.nombre


class Faq(models.Model):
    """Pregunta frecuente con su respuesta canonica."""

    gerencia = models.ForeignKey(
        Gerencia,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="faqs",
    )
    pregunta = models.TextField()
    respuesta = models.TextField()
    keywords = models.CharField(
        max_length=500,
        blank=True,
        help_text=(
            "Palabras clave separadas por comas (sinonimos, terminos comunes) "
            "para mejorar el match en la busqueda."
        ),
    )
    activo = models.BooleanField(default=True)
    veces_consultada = models.IntegerField(default=0)
    creado_en = models.DateTimeField(auto_now_add=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "chatbot"
        db_table = "chatbot_faq"
        ordering = ["-veces_consultada", "id"]
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"

    def __str__(self) -> str:
        texto = (self.pregunta or "").strip()
        return texto[:60] + ("..." if len(texto) > 60 else "")


class ConversacionSesion(models.Model):
    """
    Una sesion de chat. Puede ser anonima (ciudadano = NULL) o asociada a
    un ciudadano logueado. Se identifica externamente por `sesion_id` (UUID)
    para no exponer el PK numerico.
    """

    ciudadano = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="conversaciones_chat",
    )
    sesion_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    iniciado_en = models.DateTimeField(auto_now_add=True)
    ultimo_mensaje_en = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "chatbot"
        db_table = "chatbot_conversacionsesion"
        ordering = ["-iniciado_en"]
        verbose_name = "Sesion de conversacion"
        verbose_name_plural = "Sesiones de conversacion"

    def __str__(self) -> str:
        return f"Sesion {self.sesion_id} ({self.iniciado_en:%Y-%m-%d %H:%M})"


class MensajeChat(models.Model):
    """Un mensaje individual dentro de una sesion."""

    class Rol(models.TextChoices):
        USUARIO = "usuario", "Usuario"
        BOT = "bot", "Bot"

    sesion = models.ForeignKey(
        ConversacionSesion,
        on_delete=models.CASCADE,
        related_name="mensajes",
    )
    rol = models.CharField(max_length=10, choices=Rol.choices)
    contenido = models.TextField()
    faq_origen = models.ForeignKey(
        Faq,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mensajes",
    )
    creado_en = models.DateTimeField(auto_now_add=True)

    class Meta:
        app_label = "chatbot"
        db_table = "chatbot_mensajechat"
        ordering = ["creado_en"]
        verbose_name = "Mensaje de chat"
        verbose_name_plural = "Mensajes de chat"

    def __str__(self) -> str:
        snippet = (self.contenido or "").strip()[:60]
        return f"[{self.rol}] {snippet}"
