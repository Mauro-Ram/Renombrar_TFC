"""Emparejamiento de comprobantes PDF contra el concentrado de pagos.

La regla práctica es que un pago se identifica por *nombre + monto*. Eso casi
siempre alcanza, pero no es una llave única: es normal que a una misma
persona se le hagan dos pagos iguales el mismo día (dos requisiciones
distintas). Por eso aquí:

* la asignación es 1 a 1 — una fila del concentrado se consume por un solo
  comprobante, para que dos PDFs iguales no reciban la misma requisición;
* cuando un comprobante empata igual de bien con varias filas, se asigna la
  primera pero se marca como ambiguo, para revisión manual.
"""

from decimal import Decimal

from parser import (
    WARN_CONCEPTO_GENERICO_PREFIJO,
    WARN_SIN_BANCO,
    WARN_SIN_BENEFICIARIO,
    WARN_SIN_CONCEPTO,
    format_importe,
)
from text_utils import name_tokens

# Qué tan parecidos deben ser los nombres para aceptar una coincidencia.
MIN_NAME_SCORE = 0.6


def name_score(a: str, b: str) -> float:
    """Similitud entre dos nombres, de 0 a 1, sin importar el orden de las
    palabras ('PEREZ VELAZQUEZ JULIO' ~ 'Julio Pérez Velázquez')."""
    tokens_a = name_tokens(a)
    tokens_b = name_tokens(b)
    if not tokens_a or not tokens_b:
        return 0.0
    if tokens_a == tokens_b:
        return 1.0
    interseccion = tokens_a & tokens_b
    if not interseccion:
        return 0.0
    # Si un nombre está contenido en el otro (el concentrado a veces omite
    # el segundo apellido) se considera muy buena coincidencia.
    if tokens_a <= tokens_b or tokens_b <= tokens_a:
        return 0.95
    return len(interseccion) / len(tokens_a | tokens_b)


def _amounts_match(pdf_importe: str, row_pago: str) -> bool:
    try:
        return Decimal(pdf_importe) == Decimal(row_pago)
    except (ArithmeticError, ValueError, TypeError):
        return False


def _candidates(parsed: dict, rows: list[dict]) -> list[tuple[float, int]]:
    """Filas del concentrado compatibles con un comprobante, mejor primero."""
    importe = str(parsed.get("importe") or "").strip()
    beneficiario = parsed.get("beneficiario") or ""
    if not importe or not beneficiario:
        return []

    scored: list[tuple[float, int]] = []
    for idx, row in enumerate(rows):
        if not _amounts_match(importe, row["pago"]):
            continue
        score = name_score(beneficiario, row["nombre"])
        if score >= MIN_NAME_SCORE:
            scored.append((score, idx))
    scored.sort(key=lambda item: (-item[0], item[1]))
    return scored


def match_all(parsed_list: list[dict], rows: list[dict]) -> list[dict]:
    """Asigna a cada comprobante una fila del concentrado.

    Devuelve una lista paralela a `parsed_list` con, por cada comprobante:
    `row` (la fila asignada o None), `ambiguo` y `candidatos`.
    """
    all_candidates = [_candidates(parsed, rows) for parsed in parsed_list]

    # Se resuelven primero las coincidencias más claras: mejor puntaje y,
    # a puntaje igual, las que tienen menos filas candidatas.
    order = sorted(
        range(len(parsed_list)),
        key=lambda i: (
            -(all_candidates[i][0][0] if all_candidates[i] else 0),
            len(all_candidates[i]) or 999,
            i,
        ),
    )

    results: list[dict] = [
        {"row": None, "ambiguo": False, "candidatos": []} for _ in parsed_list
    ]
    used: set[int] = set()

    for i in order:
        candidates = all_candidates[i]
        if not candidates:
            continue
        top_score = candidates[0][0]
        empatados = [idx for score, idx in candidates if score == top_score]
        disponibles = [(score, idx) for score, idx in candidates if idx not in used]
        if not disponibles:
            results[i]["candidatos"] = [rows[idx] for idx in empatados]
            continue

        _, chosen = disponibles[0]
        used.add(chosen)
        results[i]["row"] = rows[chosen]
        results[i]["ambiguo"] = len(empatados) > 1
        results[i]["candidatos"] = [rows[idx] for idx in empatados]

    return results


def unmatched_rows(rows: list[dict], results: list[dict]) -> list[dict]:
    """Pagos del concentrado que no recibieron comprobante."""
    asignadas = {id(r["row"]) for r in results if r["row"] is not None}
    return [row for row in rows if id(row) not in asignadas]


def _drop_warnings(parsed: dict, *prefixes: str) -> None:
    """Retira avisos que el concentrado ya resolvió."""
    parsed["warnings"] = [
        w for w in parsed["warnings"] if not any(w.startswith(p) for p in prefixes)
    ]


def apply_match(parsed: dict, result: dict, bank_code_for) -> dict:
    """Sobrescribe los campos del comprobante con los del concentrado.

    La fecha siempre se queda con la del PDF: es el dato que el concentrado
    no tiene con la precisión del comprobante.
    """
    row = result.get("row")
    if row is None:
        parsed["match_status"] = "sin_coincidencia"
        parsed["warnings"].append(
            "No se encontró este pago en el concentrado (nombre + monto); "
            "revisa el importe o captura los datos a mano."
        )
        return parsed

    if row.get("requisicion"):
        parsed["concepto"] = row["requisicion"]
        parsed["concepto_generico"] = False
        _drop_warnings(parsed, WARN_SIN_CONCEPTO, WARN_CONCEPTO_GENERICO_PREFIJO)
    if row.get("nombre"):
        parsed["beneficiario"] = row["nombre"]
        _drop_warnings(parsed, WARN_SIN_BENEFICIARIO)
    if row.get("banco"):
        parsed["banco_code"] = bank_code_for(row["banco"])
        parsed["banco_detected"] = True
        _drop_warnings(parsed, WARN_SIN_BANCO)
    if row.get("semana"):
        parsed["sem"] = row["semana"]
    # Se reusa el mismo formato del PDF ('4350.00' -> '4350', '483.60' se queda).
    parsed["importe"] = format_importe(row["pago"]) or parsed["importe"]

    parsed["match_status"] = "ambiguo" if result["ambiguo"] else "ok"
    parsed["match_row"] = row["fila"]

    if not row.get("requisicion"):
        parsed["warnings"].append(
            f"La fila {row['fila']} del concentrado no trae requisición; captura el concepto a mano."
        )
    if not row.get("banco"):
        parsed["warnings"].append(
            f"La fila {row['fila']} del concentrado no trae banco; captúralo a mano."
        )
    if result["ambiguo"]:
        requisiciones = ", ".join(
            c.get("requisicion") or f"fila {c['fila']}" for c in result["candidatos"]
        )
        parsed["warnings"].append(
            f"Coincidencia ambigua: el mismo nombre y monto aparecen en varias filas "
            f"del concentrado ({requisiciones}). Se asignó la fila {row['fila']}; "
            f"verifica cuál requisición corresponde a este comprobante."
        )

    return parsed
