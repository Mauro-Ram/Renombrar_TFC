"""Construcción del nombre final de archivo a partir de los campos capturados."""

from text_utils import sanitize_token

REQUIRED_FIELDS = ["fecha", "concepto", "importe", "empresa_code", "banco_code", "beneficiario", "sem"]


def missing_fields(fields: dict) -> list[str]:
    return [name for name in REQUIRED_FIELDS if not str(fields.get(name, "")).strip()]


def build_filename(fields: dict, extension: str) -> str:
    fecha = sanitize_token(fields.get("fecha", ""))
    concepto = sanitize_token(fields.get("concepto", ""))
    importe = sanitize_token(fields.get("importe", ""))
    empresa = sanitize_token(fields.get("empresa_code", ""))
    banco = sanitize_token(fields.get("banco_code", ""))
    beneficiario = sanitize_token(fields.get("beneficiario", ""))
    sem = sanitize_token(fields.get("sem", ""))

    parts = [fecha, concepto, importe, empresa, banco, beneficiario, "SEM", sem]
    base = "_".join(p for p in parts if p)
    ext = extension if extension.startswith(".") else f".{extension}"
    return f"{base}{ext}"


def dedupe_filename(name: str, used_names: set[str]) -> str:
    if name not in used_names:
        used_names.add(name)
        return name
    stem, dot, ext = name.rpartition(".")
    if not dot:
        stem, ext = name, ""
    counter = 2
    while True:
        candidate = f"{stem} ({counter}).{ext}" if ext else f"{stem} ({counter})"
        if candidate not in used_names:
            used_names.add(candidate)
            return candidate
        counter += 1
