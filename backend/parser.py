"""Extracción de datos de comprobantes SPEI en PDF."""

import io
import re
import unicodedata

from pypdf import PdfReader

from config import BANK_PROFILES, EMPRESA_PROFILES

# Etiquetas tal como aparecen (en orden) en un comprobante SPEI tipo BBVA.
# Se usan para delimitar dónde termina el valor de un campo: todo lo que
# hay entre una etiqueta y la siguiente es el valor de la primera.
LABELS = [
    "Tipo de Operación:",
    "Contrato:",
    "Usuario:",
    "Referencia:",
    "Referencia numérica del Emisor:",
    "Referencias del Movimiento:",
    "Estado:",
    "Divisa:",
    "Cuenta CLABE:",
    "Cuenta Cargo:",
    "Cuenta Abono:",
    "Importe:",
    "Concepto:",
    "Fecha y hora de Alta:",
    "Fecha y hora de Liquidación:",
    "Clave de Rastreo:",
    "RFC Beneficiario:",
    "RFC Ordenante:",
    "Importe IVA:",
    "Email del Beneficiario:",
    "Banco Destino:",
]


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _label_pattern(label: str) -> str:
    return r"\s+".join(re.escape(word) for word in label.split())


def _extract_between(text: str, label: str) -> str | None:
    if label not in LABELS:
        raise ValueError(f"Etiqueta desconocida: {label}")
    idx = LABELS.index(label)
    following = LABELS[idx + 1 :]
    lookahead_labels = [_label_pattern(l) for l in following] or [r"$"]
    pattern = _label_pattern(label) + r"\s*(.*?)\s*(?=" + "|".join(lookahead_labels) + r"|$)"
    match = re.search(pattern, text)
    if not match:
        return None
    value = match.group(1).strip()
    return value or None


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


def format_fecha(raw: str) -> str | None:
    """'24/07/2026 17:47:52' -> '240726' (DDMMAA)."""
    match = re.search(r"(\d{2})/(\d{2})/(\d{4})", raw or "")
    if not match:
        return None
    dd, mm, yyyy = match.groups()
    return f"{dd}{mm}{yyyy[-2:]}"


def format_importe(raw: str) -> str | None:
    """'$ 4,350.00 MXN' -> '4350' (o '4350.50' si hay centavos)."""
    match = re.search(r"([\d,]+(?:\.\d{2})?)", raw or "")
    if not match:
        return None
    value = match.group(1).replace(",", "")
    if value.endswith(".00"):
        value = value[:-3]
    return value


def name_after_dash(raw: str) -> str | None:
    """'072700001792124686 - JONATAN CAMPOS CORTEZ' -> 'JONATAN CAMPOS CORTEZ'."""
    if not raw:
        return None
    parts = raw.split(" - ", 1)
    return parts[1].strip() if len(parts) == 2 else raw.strip()


def detect_bank(text: str) -> dict | None:
    for profile in BANK_PROFILES:
        if all(sig in text for sig in profile["signatures"]):
            return profile
    return None


def detect_empresa(cuenta_cargo_text: str) -> dict | None:
    if not cuenta_cargo_text:
        return None
    for profile in EMPRESA_PROFILES:
        if any(sig in cuenta_cargo_text for sig in profile["signatures"]):
            return profile
    return None


def extract_text_from_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def parse_pdf_bytes(filename: str, data: bytes) -> dict:
    warnings: list[str] = []

    try:
        raw_text = extract_text_from_pdf(data)
    except Exception:
        raw_text = ""
        warnings.append("No se pudo leer el contenido del PDF; completa los datos manualmente.")

    text = _normalize_whitespace(raw_text)

    if not text:
        warnings.append("El PDF no contiene texto extraíble (¿es un escaneo/imagen?).")

    bank_profile = detect_bank(text) if text else None
    if not bank_profile:
        warnings.append("No se reconoció el banco/formato del comprobante; selecciónalo manualmente.")

    cuenta_cargo_raw = _extract_between(text, "Cuenta Cargo:") if text else None
    empresa_profile = detect_empresa(cuenta_cargo_raw or "")
    if not empresa_profile:
        warnings.append("No se reconoció la empresa/cuenta origen; selecciónala manualmente.")

    fecha_raw = _extract_between(text, "Fecha y hora de Alta:") if text else None
    concepto_raw = _extract_between(text, "Concepto:") if text else None
    importe_raw = _extract_between(text, "Importe:") if text else None
    cuenta_abono_raw = _extract_between(text, "Cuenta Abono:") if text else None

    fecha = format_fecha(fecha_raw) if fecha_raw else None
    importe = format_importe(importe_raw) if importe_raw else None
    beneficiario = name_after_dash(cuenta_abono_raw) if cuenta_abono_raw else None

    if fecha_raw and not fecha:
        warnings.append("No se pudo interpretar la fecha del comprobante.")
    if not fecha_raw:
        warnings.append("No se encontró la fecha en el comprobante.")
    if importe_raw and not importe:
        warnings.append("No se pudo interpretar el importe del comprobante.")
    if not importe_raw:
        warnings.append("No se encontró el importe en el comprobante.")
    if not concepto_raw:
        warnings.append("No se encontró el concepto en el comprobante.")
    if not beneficiario:
        warnings.append("No se encontró el beneficiario en el comprobante.")

    return {
        "original_filename": filename,
        "fecha": fecha or "",
        "concepto": concepto_raw or "",
        "importe": importe or "",
        "beneficiario": beneficiario or "",
        "empresa_code": empresa_profile["code"] if empresa_profile else "",
        "empresa_detected": bool(empresa_profile),
        "banco_code": bank_profile["code"] if bank_profile else "",
        "banco_detected": bool(bank_profile),
        "sem": "",
        "warnings": warnings,
    }
