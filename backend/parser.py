"""Extracción de datos de comprobantes SPEI en PDF.

Cada formato de comprobante tiene su propio layout (etiquetas y orden
distintos), así que cada uno tiene su propia función `parse_<formato>` que
recibe el texto normalizado del PDF y devuelve los campos "crudos" antes de
darles formato. `detect_format` decide qué parser usar según
config.FORMAT_PROFILES.
"""

import io
import re

from pypdf import PdfReader

from config import EMPRESA_PROFILES, FORMAT_PROFILES
from text_utils import sanitize_token, strip_accents  # noqa: F401 (reexport)

MESES_ES = {
    "ene": "01", "feb": "02", "mar": "03", "abr": "04",
    "may": "05", "jun": "06", "jul": "07", "ago": "08",
    "sep": "09", "oct": "10", "nov": "11", "dic": "12",
}

# Etiquetas del comprobante Santander "Comprobante de Operación", en el
# orden en que aparecen. Incluye tanto transferencias interbancarias
# ("Fecha y hora de Alta") como del mismo banco ("Fecha aplicación").
SANTANDER_LABELS = [
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
    "Fecha aplicación:",
    "Fecha y hora de Liquidación:",
    "Clave de Rastreo:",
    "RFC Beneficiario:",
    "RFC Ordenante:",
    "Importe IVA:",
    "Email del Beneficiario:",
    "Banco Destino:",
]

# Etiquetas del "Reporte de Transferencia a Otros Bancos" de Banorte. Este
# formato viene de imprimir una página web a PDF y con frecuencia inserta
# espacios sueltos dentro de las palabras (p. ej. "T ransferir"); por eso la
# extracción usa un patrón tolerante a espacios (ver _flex_label_pattern).
BANORTE_LABELS = [
    "Cuenta/ CLABE Ordenante",
    "Nombre del Ordenante",
    "RFC Ordenante",
    "Moneda",
    "ID Tercero",
    "Nombre del Beneficiario",
    "Cuenta/ CLABE Beneficiario",
    "Titular de la Cuenta",
    "RFC Beneficiario",
    "Importe a Transferir",
    "IVA",
    "Fecha Aplicación",
    "Referencia numérica",
    "Propósito de la Transferencia",
    "Clave de Rastreo",
    "Confirmación",
]

# Etiquetas del "Comprobante de transferencia" que emite la plataforma de
# dispersión. Este comprobante NO dice desde qué banco salió el dinero
# ("Banco destino" es el del beneficiario), así que el banco del nombre de
# archivo se toma del concentrado de Excel.
TRANSFERENCIA_LABELS = [
    "Emisor:",
    "Cuenta de retiro:",
    "Tipo de operación:",
    "Beneficiario:",
    "Cuenta destino:",
    "Banco destino:",
    "Importe:",
    "Fecha y hora de operación:",
    "Número de operación:",
    "Concepto:",
    "Referencia:",
    "Clave de rastreo:",
    "Estatus:",
]


def _normalize_whitespace(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _flex_label_pattern(label: str) -> str:
    """Patrón para una etiqueta que tolera espacios sueltos entre
    caracteres, ya que algunos PDFs (Banorte) los insertan al extraer texto."""
    chars = [c for c in label if not c.isspace()]
    return r"\s*".join(re.escape(c) for c in chars)


def _extract_between(text: str, label: str, labels_order: list[str]) -> str | None:
    idx = labels_order.index(label)
    following = labels_order[idx + 1 :]
    lookahead = [_flex_label_pattern(l) for l in following] or [r"$"]
    pattern = _flex_label_pattern(label) + r"\s*(.*?)\s*(?=" + "|".join(lookahead) + r"|$)"
    match = re.search(pattern, text)
    if not match:
        return None
    value = match.group(1).strip(" :")
    return value or None


def format_fecha(raw: str) -> str | None:
    """'24/07/2026 17:47:52' o '05/01/2026' -> '240726' (DDMMAA).
    También soporta fechas con mes en texto: '27/jul./2026' -> '270726'."""
    if not raw:
        return None
    match = re.search(r"(\d{1,2})/(\d{1,2})/(\d{4})", raw)
    if match:
        dd, mm, yyyy = match.groups()
        return f"{dd.zfill(2)}{mm.zfill(2)}{yyyy[-2:]}"
    match = re.search(r"(\d{1,2})/([A-Za-zÁÉÍÓÚáéíóúñÑ]{3,4})\.?/(\d{4})", raw)
    if match:
        dd, mon, yyyy = match.groups()
        mm = MESES_ES.get(strip_accents(mon).lower().rstrip("."))
        if mm:
            return f"{dd.zfill(2)}{mm}{yyyy[-2:]}"
    return None


def format_importe(raw: str) -> str | None:
    """'$ 4,350.00 MXN' -> '4350' (o '4350.50' si hay centavos)."""
    if not raw:
        return None
    match = re.search(r"([\d,]+(?:\.\d{2})?)", raw)
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


def parse_santander(text: str) -> dict:
    cuenta_cargo = _extract_between(text, "Cuenta Cargo:", SANTANDER_LABELS)
    cuenta_abono = _extract_between(text, "Cuenta Abono:", SANTANDER_LABELS)
    fecha_raw = _extract_between(text, "Fecha y hora de Alta:", SANTANDER_LABELS) or _extract_between(
        text, "Fecha aplicación:", SANTANDER_LABELS
    )
    return {
        "fecha_raw": fecha_raw,
        "concepto_raw": _extract_between(text, "Concepto:", SANTANDER_LABELS),
        "importe_raw": _extract_between(text, "Importe:", SANTANDER_LABELS),
        "beneficiario_raw": name_after_dash(cuenta_abono) if cuenta_abono else None,
        "empresa_source": cuenta_cargo,
        "operacion_id": _extract_between(text, "Clave de Rastreo:", SANTANDER_LABELS),
    }


def parse_banorte(text: str) -> dict:
    return {
        "fecha_raw": _extract_between(text, "Fecha Aplicación", BANORTE_LABELS),
        "concepto_raw": _extract_between(text, "Propósito de la Transferencia", BANORTE_LABELS),
        "importe_raw": _extract_between(text, "Importe a Transferir", BANORTE_LABELS),
        "beneficiario_raw": _extract_between(text, "Nombre del Beneficiario", BANORTE_LABELS),
        "empresa_source": _extract_between(text, "Nombre del Ordenante", BANORTE_LABELS),
        "operacion_id": _extract_between(text, "Clave de Rastreo", BANORTE_LABELS),
    }


def parse_transferencia(text: str) -> dict:
    """Comprobante de dispersión. El "Concepto" suele ser genérico ('ABONO'),
    así que el concepto real (la requisición) viene del concentrado."""
    return {
        "fecha_raw": _extract_between(text, "Fecha y hora de operación:", TRANSFERENCIA_LABELS),
        "concepto_raw": _extract_between(text, "Concepto:", TRANSFERENCIA_LABELS),
        "importe_raw": _extract_between(text, "Importe:", TRANSFERENCIA_LABELS),
        "beneficiario_raw": _extract_between(text, "Beneficiario:", TRANSFERENCIA_LABELS),
        "empresa_source": _extract_between(text, "Emisor:", TRANSFERENCIA_LABELS),
        "operacion_id": _extract_between(text, "Clave de rastreo:", TRANSFERENCIA_LABELS),
        "banco_destino": _extract_between(text, "Banco destino:", TRANSFERENCIA_LABELS),
    }


PARSERS = {
    "santander": parse_santander,
    "banorte": parse_banorte,
    "transferencia": parse_transferencia,
}

# Conceptos que el comprobante trae por defecto y que no describen el pago:
# si solo tenemos esto, el concepto real debe venir del concentrado.
CONCEPTOS_GENERICOS = {"ABONO", "PAGO", "TRANSFERENCIA", "SPEI", "DEPOSITO"}

# Avisos que el concentrado puede resolver: si el emparejamiento aporta el
# dato, matching.apply_match los retira para no alarmar de más.
WARN_SIN_BANCO = "Este comprobante no indica el banco pagador; se toma del concentrado o se captura a mano."
WARN_SIN_CONCEPTO = "No se encontró el concepto en el comprobante."
WARN_CONCEPTO_GENERICO_PREFIJO = "El concepto del comprobante es genérico"
WARN_SIN_BENEFICIARIO = "No se encontró el beneficiario en el comprobante."


def detect_format(text: str) -> dict | None:
    for profile in FORMAT_PROFILES:
        if all(sig in text for sig in profile["signatures"]):
            return profile
    return None


def detect_empresa(source_text: str) -> dict | None:
    if not source_text:
        return None
    upper = strip_accents(source_text).upper()
    for profile in EMPRESA_PROFILES:
        if any(strip_accents(sig).upper() in upper for sig in profile["signatures"]):
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

    format_profile = detect_format(text) if text else None
    parsed = {}
    if not format_profile:
        warnings.append(
            "No se reconoció el formato del comprobante; completa los datos manualmente."
        )
    else:
        parser_fn = PARSERS.get(format_profile["key"])
        parsed = parser_fn(text) if parser_fn else {}
        if format_profile["key"] == "banorte":
            warnings.append(
                "Este formato (Banorte) a veces inserta espacios dentro de palabras al extraer el texto; "
                "revisa Concepto y Beneficiario antes de descargar."
            )

    empresa_profile = detect_empresa(parsed.get("empresa_source") or "")

    fecha_raw = parsed.get("fecha_raw")
    importe_raw = parsed.get("importe_raw")
    concepto_raw = parsed.get("concepto_raw")
    beneficiario = parsed.get("beneficiario_raw")

    fecha = format_fecha(fecha_raw) if fecha_raw else None
    importe = format_importe(importe_raw) if importe_raw else None

    # El banco solo se conoce cuando el propio formato lo identifica; los
    # comprobantes de dispersión lo dejan vacío para que lo aporte el Excel.
    banco_code = format_profile["code"] if format_profile else ""

    concepto = concepto_raw or ""
    concepto_generico = bool(concepto) and concepto.strip().upper() in CONCEPTOS_GENERICOS

    if fecha_raw and not fecha:
        warnings.append("No se pudo interpretar la fecha del comprobante.")
    if not fecha_raw:
        warnings.append("No se encontró la fecha en el comprobante.")
    if importe_raw and not importe:
        warnings.append("No se pudo interpretar el importe del comprobante.")
    if not importe_raw:
        warnings.append("No se encontró el importe en el comprobante.")
    if not concepto_raw:
        warnings.append(WARN_SIN_CONCEPTO)
    elif concepto_generico:
        warnings.append(
            f"{WARN_CONCEPTO_GENERICO_PREFIJO} ('{concepto}'); usa la requisición del concentrado."
        )
    if not beneficiario:
        warnings.append(WARN_SIN_BENEFICIARIO)
    if format_profile and not banco_code:
        warnings.append(WARN_SIN_BANCO)
    if not empresa_profile:
        warnings.append("No se reconoció la empresa/cuenta origen; selecciónala manualmente.")

    return {
        "original_filename": filename,
        "fecha": fecha or "",
        "concepto": concepto,
        "concepto_generico": concepto_generico,
        "importe": importe or "",
        "beneficiario": beneficiario or "",
        "empresa_code": empresa_profile["code"] if empresa_profile else "",
        "empresa_detected": bool(empresa_profile),
        "empresa_source": parsed.get("empresa_source") or "",
        "banco_code": banco_code,
        "banco_detected": bool(banco_code),
        "formato": format_profile["key"] if format_profile else "",
        "operacion_id": parsed.get("operacion_id") or "",
        "sem": "",
        "warnings": warnings,
    }
