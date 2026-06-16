"""
Codigo de barras Code 128 (subset C) — replica EXACTA del componente
`MuniBarcode` del app movil, para que la BustaCard impresa/PDF use el mismo
formato que la digital. Codifica el DNI en pares de digitos.

Expone:
  - barras(dni)      -> lista de (weight:int, filled:bool)
  - svg(dni, ...)    -> SVG inline (para el HTML)
  - texto_humano(dni)-> los digitos legibles bajo el codigo
"""
from __future__ import annotations

# Tabla oficial Code 128 (valores 0..106). 0..102 data, 103/104/105 START
# A/B/C, 106 STOP (7 widths). Identica a la del app (muni-barcode.tsx).
CODE128_PATTERNS: list[list[int]] = [
    [2, 1, 2, 2, 2, 2], [2, 2, 2, 1, 2, 2], [2, 2, 2, 2, 2, 1], [1, 2, 1, 2, 2, 3],
    [1, 2, 1, 3, 2, 2], [1, 3, 1, 2, 2, 2], [1, 2, 2, 2, 1, 3], [1, 2, 2, 3, 1, 2],
    [1, 3, 2, 2, 1, 2], [2, 2, 1, 2, 1, 3], [2, 2, 1, 3, 1, 2], [2, 3, 1, 2, 1, 2],
    [1, 1, 2, 2, 3, 2], [1, 2, 2, 1, 3, 2], [1, 2, 2, 2, 3, 1], [1, 1, 3, 2, 2, 2],
    [1, 2, 3, 1, 2, 2], [1, 2, 3, 2, 2, 1], [2, 2, 3, 2, 1, 1], [2, 2, 1, 1, 3, 2],
    [2, 2, 1, 2, 3, 1], [2, 1, 3, 2, 1, 2], [2, 2, 3, 1, 1, 2], [3, 1, 2, 1, 3, 1],
    [3, 1, 1, 2, 2, 2], [3, 2, 1, 1, 2, 2], [3, 2, 1, 2, 2, 1], [3, 1, 2, 2, 1, 2],
    [3, 2, 2, 1, 1, 2], [3, 2, 2, 2, 1, 1], [2, 1, 2, 1, 2, 3], [2, 1, 2, 3, 2, 1],
    [2, 3, 2, 1, 2, 1], [1, 1, 1, 3, 2, 3], [1, 3, 1, 1, 2, 3], [1, 3, 1, 3, 2, 1],
    [1, 1, 2, 3, 1, 3], [1, 3, 2, 1, 1, 3], [1, 3, 2, 3, 1, 1], [2, 1, 1, 3, 1, 3],
    [2, 3, 1, 1, 1, 3], [2, 3, 1, 3, 1, 1], [1, 1, 2, 1, 3, 3], [1, 1, 2, 3, 3, 1],
    [1, 3, 2, 1, 3, 1], [1, 1, 3, 1, 2, 3], [1, 1, 3, 3, 2, 1], [1, 3, 3, 1, 2, 1],
    [3, 1, 3, 1, 2, 1], [2, 1, 1, 3, 3, 1], [2, 3, 1, 1, 3, 1], [2, 1, 3, 1, 1, 3],
    [2, 1, 3, 3, 1, 1], [2, 1, 3, 1, 3, 1], [3, 1, 1, 1, 2, 3], [3, 1, 1, 3, 2, 1],
    [3, 3, 1, 1, 2, 1], [3, 1, 2, 1, 1, 3], [3, 1, 2, 3, 1, 1], [3, 3, 2, 1, 1, 1],
    [3, 1, 4, 1, 1, 1], [2, 2, 1, 4, 1, 1], [4, 3, 1, 1, 1, 1], [1, 1, 1, 2, 2, 4],
    [1, 1, 1, 4, 2, 2], [1, 2, 1, 1, 2, 4], [1, 2, 1, 4, 2, 1], [1, 4, 1, 1, 2, 2],
    [1, 4, 1, 2, 2, 1], [1, 1, 2, 2, 1, 4], [1, 1, 2, 4, 1, 2], [1, 2, 2, 1, 1, 4],
    [1, 2, 2, 4, 1, 1], [1, 4, 2, 1, 1, 2], [1, 4, 2, 2, 1, 1], [2, 4, 1, 2, 1, 1],
    [2, 2, 1, 1, 1, 4], [4, 1, 3, 1, 1, 1], [2, 4, 1, 1, 1, 2], [1, 3, 4, 1, 1, 1],
    [1, 1, 1, 2, 4, 2], [1, 2, 1, 1, 4, 2], [1, 2, 1, 2, 4, 1], [1, 1, 4, 2, 1, 2],
    [1, 2, 4, 1, 1, 2], [1, 2, 4, 2, 1, 1], [4, 1, 1, 2, 1, 2], [4, 2, 1, 1, 1, 2],
    [4, 2, 1, 2, 1, 1], [2, 1, 2, 1, 4, 1], [2, 1, 4, 1, 2, 1], [4, 1, 2, 1, 2, 1],
    [1, 1, 1, 1, 4, 3], [1, 1, 1, 3, 4, 1], [1, 3, 1, 1, 4, 1], [1, 1, 4, 1, 1, 3],
    [1, 1, 4, 3, 1, 1], [4, 1, 1, 1, 1, 3], [4, 1, 1, 3, 1, 1], [1, 1, 3, 1, 4, 1],
    [1, 1, 4, 1, 3, 1], [3, 1, 1, 1, 4, 1], [4, 1, 1, 1, 3, 1], [2, 1, 1, 4, 1, 2],
    [2, 1, 1, 2, 1, 4], [2, 1, 1, 2, 3, 2], [2, 3, 3, 1, 1, 1, 2],
]


def texto_humano(raw: str) -> str:
    digits = "".join(ch for ch in (raw or "") if ch.isdigit())
    if not digits:
        return ""
    return digits if len(digits) % 2 == 0 else "0" + digits


def barras(raw: str) -> list[tuple[int, bool]]:
    """Devuelve [(weight, filled)] del Code 128-C para `raw` (DNI)."""
    digits = "".join(ch for ch in (raw or "") if ch.isdigit())
    if not digits:
        return []
    padded = digits if len(digits) % 2 == 0 else "0" + digits

    values: list[int] = [105]  # START C
    for i in range(0, len(padded), 2):
        values.append(int(padded[i:i + 2]))

    # Checksum = (start + sum(pos * value)) % 103
    suma = values[0]
    for i in range(1, len(values)):
        suma += values[i] * i
    values.append(suma % 103)

    values.append(106)  # STOP

    bars: list[tuple[int, bool]] = [(10, False)]  # quiet zone
    for v in values:
        pattern = CODE128_PATTERNS[v]
        for i, w in enumerate(pattern):
            bars.append((w, i % 2 == 0))
    bars.append((10, False))  # quiet zone final
    return bars


def svg(raw: str, height: int = 64, bar_color: str = "#111111") -> str:
    """SVG inline (escala al 100% del ancho del contenedor)."""
    bars = barras(raw)
    if not bars:
        return ""
    total = sum(w for w, _ in bars)
    rects: list[str] = []
    x = 0
    for w, filled in bars:
        if filled:
            rects.append(
                f'<rect x="{x}" y="0" width="{w}" height="{height}" fill="{bar_color}"/>'
            )
        x += w
    return (
        f'<svg viewBox="0 0 {total} {height}" width="100%" height="{height}" '
        f'preserveAspectRatio="none" xmlns="http://www.w3.org/2000/svg">'
        f'{"".join(rects)}</svg>'
    )
