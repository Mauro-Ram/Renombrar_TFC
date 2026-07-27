"""Utilidades de texto compartidas por el parser, el índice y config."""

import re
import unicodedata


def strip_accents(text: str) -> str:
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(c for c in normalized if not unicodedata.combining(c))


def sanitize_token(text: str) -> str:
    """Convierte texto libre en un token seguro para nombre de archivo."""
    text = strip_accents(text).upper()
    text = re.sub(r"[^A-Z0-9 ._-]", "", text)
    text = re.sub(r"\s+", "_", text.strip())
    text = re.sub(r"_+", "_", text)
    return text


def normalize_key(text: str) -> str:
    """Normaliza texto para comparar/emparejar: sin acentos, mayúsculas,
    sin puntuación y con espacios colapsados.

    'Julio César Pérez Velázquez ' -> 'JULIO CESAR PEREZ VELAZQUEZ'
    """
    if not text:
        return ""
    text = strip_accents(str(text)).upper()
    text = re.sub(r"[^A-Z0-9]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def name_tokens(text: str) -> set[str]:
    """Palabras significativas de un nombre, para comparar sin importar el
    orden ni las partículas ('DE', 'LA', ...)."""
    stopwords = {"DE", "DEL", "LA", "LAS", "LOS", "Y", "SA", "CV", "SC", "SAPI"}
    return {t for t in normalize_key(text).split() if t and t not in stopwords}
