"""Catálogos configurables de la app.

Hay dos conceptos distintos que conviene no confundir:

* **Formato de comprobante** (`FORMAT_PROFILES`): el *diseño* del PDF, que
  determina qué parser usar. Agregar uno nuevo implica escribir su función
  `parse_<formato>(text)` en parser.py y registrarla en `parser.PARSERS`.
* **Banco del nombre de archivo** (`BANK_CODE_ALIASES`): el código corto que
  va en el nombre final. No es una lista cerrada: si el banco no está en el
  diccionario, el código se genera a partir de su nombre, así que un banco
  nuevo funciona sin tocar el código.

Algunos formatos (p. ej. el "Comprobante de transferencia" de una plataforma
de dispersión) no dicen desde qué banco salió el dinero; en esos casos `code`
va vacío y el banco se toma del concentrado de Excel.

Para agregar una empresa/cuenta origen nueva: añade una entrada a
EMPRESA_PROFILES con el texto que aparece en el comprobante para la cuenta
que origina el pago (Santander: "Cuenta Cargo"; Banorte: "Nombre del
Ordenante"; dispersión: "Emisor") y el código deseado en el nombre.
"""

from text_utils import normalize_key, sanitize_token

FORMAT_PROFILES = [
    {
        "key": "santander",
        "label": "Santander (SuperLínea)",
        "code": "STDR",
        "signatures": ["Comprobante de Operación", "SuperLínea"],
    },
    {
        "key": "banorte",
        "label": "Banorte",
        "code": "BNT",
        "signatures": ["Banorte", "Nombre del Ordenante"],
    },
    {
        # El banco pagador no viene en este comprobante: se toma del Excel.
        "key": "transferencia",
        "label": "Comprobante de transferencia (dispersión)",
        "code": "",
        "signatures": ["Comprobante de transferencia", "Clave de rastreo"],
    },
]

EMPRESA_PROFILES = [
    {
        "key": "fuentes_corp",
        "label": "The Fuentes Corporation",
        "code": "FUENTES",
        "signatures": ["FUENTES CORPORATION"],
    },
    {
        "key": "janupi",
        "label": "Janupi Construcciones",
        "code": "JANUPI",
        "signatures": ["JANUPI CONSTRUCCIONES"],
    },
    {
        "key": "ark_zoque",
        "label": "Desarrollos Ark Zoque",
        "code": "ARKZOQUE",
        "signatures": ["ARK ZOQUE"],
    },
]

# Códigos cortos preferidos por banco. Es solo una tabla de preferencias:
# un banco que no esté aquí igual funciona, usando su nombre saneado.
BANK_CODE_ALIASES = {
    "SANTANDER": "STDR",
    "BANORTE": "BNT",
    "BBVA": "BBVA",
    "BBVA BANCOMER": "BBVA",
    "BANCOMER": "BBVA",
    "BANAMEX": "BANAMEX",
    "CITIBANAMEX": "BANAMEX",
    "HSBC": "HSBC",
    "SCOTIABANK": "SCOTIA",
    "INBURSA": "INBURSA",
    "BANCO AZTECA": "AZTECA",
    "AZTECA": "AZTECA",
    "BANCO DEL BAJIO": "BAJIO",
    "BAJIO": "BAJIO",
    "AFIRME": "AFIRME",
    "BANREGIO": "BANREGIO",
    "MIFEL": "MIFEL",
    "MULTIVA": "MULTIVA",
    "ACTINVER": "ACTINVER",
    "BANCOPPEL": "BANCOPPEL",
    "BANCO COPPEL": "BANCOPPEL",
    "MERCADO PAGO": "MERCADOPAGO",
    "MERCADO PAGO W": "MERCADOPAGO",
    "MERCADOPAGO": "MERCADOPAGO",
    "NU": "NU",
    "NU MEXICO": "NU",
    "NUBANK": "NU",
    "KLAR": "KLAR",
    "SPIN": "SPIN",
    "SPIN BY OXXO": "SPIN",
    "STP": "STP",
    "HEY BANCO": "HEY",
    "HEY": "HEY",
}


def bank_code_for(name: str) -> str:
    """Convierte el nombre de un banco en el código que va en el archivo.

    Usa `BANK_CODE_ALIASES` cuando lo conoce y, si no, sanea el nombre. Así
    un banco nuevo en el concentrado no rompe el renombrado.
    """
    if not name:
        return ""
    key = normalize_key(name)
    if key in BANK_CODE_ALIASES:
        return BANK_CODE_ALIASES[key]
    # El código va sin espacios para que se lea como un solo campo dentro
    # del nombre, que ya usa el espacio como separador.
    return sanitize_token(name).replace(" ", "")


def known_bank_codes() -> list[str]:
    """Códigos sugeridos para el autocompletado de la interfaz."""
    codes = set(BANK_CODE_ALIASES.values())
    codes.update(p["code"] for p in FORMAT_PROFILES if p["code"])
    return sorted(codes)
