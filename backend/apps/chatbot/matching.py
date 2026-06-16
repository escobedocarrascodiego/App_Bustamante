"""
Matching de FAQs por SCORING de tokens (sin dependencias externas ni
Full-Text Search).

Problema que resuelve: los usuarios escriben frases completas
("¿Cuáles son los requisitos para casarme?") y el match contra la columna
`keywords` ("matrimonio,civil,casarse,boda") fallaba porque la logica vieja
usaba OR + orden por popularidad (devolvia la FAQ mas popular que coincidiera
con CUALQUIER palabra, no la mas relevante).

Flujo:
  1. Normalizar: minusculas, quitar tildes y signos.
  2. Quitar stop words en español.
  3. Tokenizar (lista de palabras).
  4. Por cada FAQ de la gerencia, calcular un score:
        +3 token == keyword exacto
        +2 token comparte prefijo (4) con un keyword  (plurales/conjugaciones)
        +1 token aparece en la pregunta
  5. Devolver la FAQ con mayor score (>0). Empate -> mas consultada.

Como la UI ya filtra por gerencia_id, el scoring corre sobre pocos registros
en Python: rapido y exacto.
"""
from __future__ import annotations

import re
import unicodedata

from .models import Faq

# Stop words en español (NORMALIZADAS: sin tildes, porque el texto se
# normaliza antes de filtrar). Articulos, preposiciones, pronombres,
# auxiliares y muletillas de pregunta que no aportan al match.
STOP_WORDS: frozenset[str] = frozenset({
    "el", "la", "los", "las", "un", "una", "unos", "unas", "lo", "le", "les",
    "de", "del", "al", "a", "en", "y", "o", "u", "e", "con", "sin", "por",
    "para", "segun", "sobre", "tras", "ante", "bajo", "entre", "hacia", "hasta",
    "que", "qué", "cual", "cuales", "como", "cuando", "donde", "quien", "quienes",
    "cuanto", "cuanta", "cuantos", "cuantas", "cuyo", "cuya",
    "mi", "mis", "tu", "tus", "su", "sus", "me", "te", "se", "nos", "os",
    "yo", "el", "ella", "ellos", "ellas", "usted", "ustedes", "nosotros",
    "es", "son", "esta", "estan", "este", "esta", "esto", "estos", "estas",
    "ser", "estar", "hay", "habia", "fue", "era", "sera",
    "hacer", "hago", "hace", "hacen", "puedo", "puede", "pueden", "quiero",
    "quisiera", "necesito", "deseo", "debo", "debe", "tengo", "tiene", "tener",
    "si", "no", "ya", "muy", "mas", "menos", "tambien", "pero", "porque",
    "aqui", "alli", "ahi", "este", "esa", "ese", "eso", "esas", "esos",
    "mismo", "cada", "todo", "toda", "todos", "todas", "algun", "alguna",
    "del", "uno", "dos",  # numeros sueltos poco utiles
})

# Todo lo que no sea letra/numero/espacio se vuelve espacio.
_NO_ALNUM = re.compile(r"[^a-z0-9ñ ]+")
_PREFIJO = 4  # largo de prefijo para match difuso (plurales/conjugaciones)


def normalizar(texto: str) -> str:
    """minusculas + sin tildes + sin signos. (ñ -> n, consistente en ambos lados)."""
    texto = (texto or "").lower()
    descompuesto = unicodedata.normalize("NFD", texto)
    sin_tildes = "".join(c for c in descompuesto if unicodedata.category(c) != "Mn")
    return _NO_ALNUM.sub(" ", sin_tildes)


def tokenizar(texto: str, min_len: int = 2) -> list[str]:
    """Devuelve tokens utiles: sin stop words, sin duplicados, len >= min_len."""
    salida: list[str] = []
    vistos: set[str] = set()
    for palabra in normalizar(texto).split():
        if len(palabra) < min_len or palabra in STOP_WORDS or palabra in vistos:
            continue
        vistos.add(palabra)
        salida.append(palabra)
    return salida


def _set_tokens(texto: str) -> set[str]:
    return set(tokenizar(texto, min_len=2))


def _prefijo_match(token: str, conjunto: set[str]) -> bool:
    """True si `token` comparte los primeros _PREFIJO chars con algun token del set."""
    if len(token) < _PREFIJO:
        return False
    p = token[:_PREFIJO]
    return any(len(t) >= _PREFIJO and t[:_PREFIJO] == p for t in conjunto)


def _score(user_tokens: list[str], kw_set: set[str], preg_set: set[str]) -> int:
    score = 0
    for t in user_tokens:
        if t in kw_set:
            score += 3
        elif _prefijo_match(t, kw_set):
            score += 2
        elif t in preg_set:
            score += 1
    return score


def buscar_faq(texto_usuario: str, gerencia_id: int | None = None) -> Faq | None:
    """
    Devuelve la FAQ mas relevante para `texto_usuario` dentro de `gerencia_id`
    (o de todas si es None). Empata por veces_consultada. None si nada matchea.
    """
    tokens = tokenizar(texto_usuario)
    if not tokens:
        return None

    qs = Faq.objects.filter(activo=True)
    if gerencia_id is not None:
        qs = qs.filter(gerencia_id=gerencia_id)

    mejor: Faq | None = None
    mejor_key: tuple[int, int] = (0, -1)
    for faq in qs:
        kw_set = _set_tokens((faq.keywords or "").replace(",", " "))
        preg_set = _set_tokens(faq.pregunta or "")
        s = _score(tokens, kw_set, preg_set)
        if s <= 0:
            continue
        key = (s, faq.veces_consultada)
        if key > mejor_key:
            mejor_key = key
            mejor = faq
    return mejor
