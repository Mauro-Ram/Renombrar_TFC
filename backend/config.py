"""Catálogos configurables de la app.

Para agregar un banco nuevo: añade una entrada a BANK_PROFILES con frases
("signatures") que aparezcan siempre en el texto de ese comprobante y el
código que debe usarse en el nombre de archivo.

Para agregar una empresa/cuenta origen nueva: añade una entrada a
EMPRESA_PROFILES con el texto que aparece en "Cuenta Cargo" del comprobante
y el código deseado en el nombre de archivo.
"""

BANK_PROFILES = [
    {
        "key": "bbva_superlinea",
        "label": "BBVA (SuperLínea)",
        "code": "STDR",
        "signatures": ["Comprobante de Operación", "SuperLínea"],
    },
]

EMPRESA_PROFILES = [
    {
        "key": "fuentes_corp",
        "label": "The Fuentes Corporation",
        "code": "FUENTES",
        "signatures": ["FUENTES CORPORATION"],
    },
]
