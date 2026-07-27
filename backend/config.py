"""Catálogos configurables de la app.

Para agregar un banco nuevo hace falta también escribir su parser en
parser.py (cada banco trae un formato de comprobante distinto), y luego
registrar aquí su "key" (debe coincidir con la usada en parser.PARSERS),
las frases que lo identifican ("signatures") y el código que debe usarse
en el nombre de archivo.

Para agregar una empresa/cuenta origen nueva: añade una entrada a
EMPRESA_PROFILES con el texto que aparece en el comprobante para la cuenta
que origina el pago (Santander: "Cuenta Cargo"; Banorte: "Nombre del
Ordenante") y el código deseado en el nombre de archivo.
"""

BANK_PROFILES = [
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
]
