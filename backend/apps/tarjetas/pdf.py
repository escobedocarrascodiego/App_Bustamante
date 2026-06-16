"""
Generacion de la BustaCard en PDF (reportlab) para descargar / enviar por
WhatsApp. Dibuja la tarjeta con el mismo diseño que la version impresa:
header azul, logo, datos, codigo de barras Code128-C (igual al app) y los
beneficios.
"""
from __future__ import annotations

import datetime
import io
from pathlib import Path

from reportlab.lib.colors import HexColor, white
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase.pdfmetrics import stringWidth
from reportlab.pdfgen import canvas

from apps.tarjetas import barcode128

PRIMARY = HexColor("#0B3D91")
ACCENT = HexColor("#F5B800")
SILVER = HexColor("#EEF0F3")
SILVER_BORDER = HexColor("#9AA0A6")
TEXT = HexColor("#1F2937")
MUTED = HexColor("#6B7280")
BORDER = HexColor("#E2E8F0")

_LOGO_PATH = Path(__file__).resolve().parent / "static" / "ventanilla" / "logo.png"

CARD_W = 384.0
PAD = 16.0
MARGIN = 24.0


def _wrap(text: str, font: str, size: float, max_w: float, max_lines: int = 2) -> list[str]:
    """Corta `text` en lineas que caben en `max_w` (max `max_lines`)."""
    text = (text or "").strip()
    if not text:
        return []
    palabras = text.split()
    lineas: list[str] = []
    actual = ""
    for p in palabras:
        prueba = f"{actual} {p}".strip()
        if stringWidth(prueba, font, size) <= max_w:
            actual = prueba
        else:
            if actual:
                lineas.append(actual)
            actual = p
            if len(lineas) >= max_lines:
                break
    if actual and len(lineas) < max_lines:
        lineas.append(actual)
    # Si quedo texto sin entrar, marcar con elipsis en la ultima linea.
    if len(lineas) == max_lines:
        ultima = lineas[-1]
        while stringWidth(ultima + "…", font, size) > max_w and len(ultima) > 1:
            ultima = ultima[:-1]
        if stringWidth(text, font, size) > max_w * max_lines:
            lineas[-1] = ultima + "…"
    return lineas


def generar_bustacard_pdf(
    *,
    nombre: str,
    dni: str,
    direccion: str,
    codigo: str,
    anio: int,
    fecha_vencimiento: datetime.date,
) -> bytes:
    """Devuelve los bytes del PDF de la BustaCard."""
    dir_lineas = _wrap(direccion, "Helvetica", 9.5, CARD_W - 2 * PAD - 60, max_lines=2)
    n_info = 3 + max(1, len(dir_lineas)) if direccion else 3

    # Altura de la tarjeta (header + cuerpo).
    header_h = 26.0
    cuerpo_h = (
        PAD + 56          # brand row (logo)
        + 12 + n_info * 15  # info
        + 14 + 52 + 16    # barcode + texto
        + 6 + 14          # F.V.
        + PAD
    )
    card_h = header_h + cuerpo_h

    benef_h = 184.0
    page_w = CARD_W + 2 * MARGIN
    page_h = MARGIN + card_h + 14 + benef_h + MARGIN

    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(page_w, page_h))

    card_x = MARGIN
    card_top = page_h - MARGIN  # y del borde superior de la tarjeta

    _dibujar_tarjeta(
        c, card_x, card_top, card_h, header_h,
        nombre=nombre, dni=dni, dir_lineas=dir_lineas,
        codigo=codigo, anio=anio, fecha_vencimiento=fecha_vencimiento,
    )

    benef_top = card_top - card_h - 14
    _dibujar_beneficios(c, card_x, benef_top, benef_h)

    c.showPage()
    c.save()
    return buf.getvalue()


def _dibujar_tarjeta(
    c, x, top, card_h, header_h, *,
    nombre, dni, dir_lineas, codigo, anio, fecha_vencimiento,
):
    # Fondo de la tarjeta
    c.setFillColor(SILVER)
    c.setStrokeColor(SILVER_BORDER)
    c.roundRect(x, top - card_h, CARD_W, card_h, 14, stroke=1, fill=1)

    # Header azul (con esquinas superiores redondeadas aproximadas)
    c.setFillColor(PRIMARY)
    c.roundRect(x, top - header_h, CARD_W, header_h, 14, stroke=0, fill=1)
    c.rect(x, top - header_h, CARD_W, header_h - 14, stroke=0, fill=1)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(
        x + CARD_W / 2, top - header_h + 8.5,
        "TARJETA DIGITAL DEL BUEN CONTRIBUYENTE BUSTAMANTINO",
    )

    cuerpo_top = top - header_h
    yc = cuerpo_top - PAD

    # --- Brand row: logo + nombre muni / BUSTACARD + año ---
    logo_size = 50
    try:
        c.drawImage(
            ImageReader(str(_LOGO_PATH)), x + PAD, yc - logo_size,
            logo_size, logo_size, mask="auto", preserveAspectRatio=True,
        )
    except Exception:
        pass

    c.setFillColor(PRIMARY)
    c.setFont("Helvetica-Bold", 10)
    tx = x + PAD + logo_size + 8
    c.drawString(tx, yc - 14, "JOSÉ LUIS")
    c.drawString(tx, yc - 26, "BUSTAMANTE")
    c.drawString(tx, yc - 38, "Y RIVERO")

    c.setFont("Helvetica-Bold", 13)
    c.drawRightString(x + CARD_W - PAD, yc - 14, "BUSTACARD")
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-Bold", 26)
    c.drawRightString(x + CARD_W - PAD, yc - 40, str(anio))

    yc -= 56 + 12

    # --- Info ---
    def info(label, value, y):
        c.setFillColor(TEXT)
        c.setFont("Helvetica-Bold", 9.5)
        c.drawString(x + PAD, y, f"{label}")
        c.setFont("Helvetica", 9.5)
        c.drawString(x + PAD + 64, y, f": {value}")

    info("CÓDIGO", codigo, yc); yc -= 15
    info("NOMBRE", nombre, yc); yc -= 15
    info("DNI", dni, yc); yc -= 15
    if dir_lineas:
        c.setFillColor(TEXT)
        c.setFont("Helvetica-Bold", 9.5)
        c.drawString(x + PAD, yc, "DIRECCIÓN")
        c.setFont("Helvetica", 9.5)
        c.drawString(x + PAD + 64, yc, f": {dir_lineas[0]}")
        yc -= 15
        for extra in dir_lineas[1:]:
            c.drawString(x + PAD + 64 + 4, yc, extra)
            yc -= 15

    # --- Código de barras ---
    yc -= 2
    _dibujar_barcode(c, x + PAD, yc - 52, CARD_W - 2 * PAD, 52, dni)
    yc -= 52
    c.setFillColor(TEXT)
    c.setFont("Courier-Bold", 11)
    c.drawCentredString(x + CARD_W / 2, yc - 12, barcode128.texto_humano(dni))
    yc -= 16

    # --- F.V. ---
    yc -= 6
    c.setFillColor(MUTED)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(
        x + CARD_W / 2, yc - 8,
        f"F. V. {fecha_vencimiento.strftime('%d-%m-%Y')}",
    )


def _dibujar_barcode(c, x, y, w, h, dni):
    bars = barcode128.barras(dni)
    if not bars:
        return
    total = sum(wt for wt, _ in bars)
    if total <= 0:
        return
    escala = w / total
    cursor = x
    c.setFillColor(HexColor("#111111"))
    for wt, filled in bars:
        ancho = wt * escala
        if filled:
            c.rect(cursor, y, ancho, h, stroke=0, fill=1)
        cursor += ancho


def _dibujar_beneficios(c, x, top, h):
    c.setFillColor(white)
    c.setStrokeColor(BORDER)
    c.roundRect(x, top - h, CARD_W, h, 12, stroke=1, fill=1)

    yc = top - 18
    c.setFillColor(PRIMARY)
    c.setFont("Helvetica-Bold", 12)
    c.drawString(x + PAD, yc, "TUS BENEFICIOS")
    yc -= 22

    items = [
        ("Ingreso Libre a Piscina", "(Martes - Viernes)"),
        ("Ingreso Libre a Parque «Ccoritos»", "(Martes - Viernes)"),
    ]
    for nombre, horario in items:
        c.setFillColor(TEXT)
        c.setFont("Helvetica-Bold", 10.5)
        c.drawString(x + PAD, yc, f"•  {nombre}")
        yc -= 13
        c.setFillColor(MUTED)
        c.setFont("Helvetica", 9)
        c.drawString(x + PAD + 12, yc, horario)
        yc -= 18

    c.setFillColor(MUTED)
    c.setFont("Helvetica-Oblique", 9)
    c.drawString(
        x + PAD, yc,
        "Incluye Titular, Cónyuge y 2 menores, o Adulto Mayor con acompañante.",
    )
    yc -= 20

    # Caja "IMPORTANTE"
    c.setFillColor(HexColor("#F5F7FB"))
    c.rect(x + PAD, yc - 6, CARD_W - 2 * PAD, 22, stroke=0, fill=1)
    c.setFillColor(ACCENT)
    c.rect(x + PAD, yc - 6, 3, 22, stroke=0, fill=1)
    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(x + PAD + 10, yc + 2, "IMPORTANTE: Mostrar DNI físico + BustaCard.")
    yc -= 28

    c.setStrokeColor(BORDER)
    c.line(x + PAD, yc + 6, x + CARD_W - PAD, yc + 6)
    c.setFillColor(TEXT)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(x + CARD_W / 2, yc - 6, "Gerencia de Administración Tributaria")
    c.setFillColor(ACCENT)
    c.setFont("Helvetica-BoldOblique", 10)
    c.drawCentredString(x + CARD_W / 2, yc - 20, "¡Gracias por tu contribución!")
