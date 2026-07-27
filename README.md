# Renombrar TFC

Aplicación web interna para renombrar de forma masiva comprobantes SPEI en PDF,
usando el formato:

```
FECHA CONCEPTO IMPORTE EMPRESA BANCO BENEFICIARIO SEM SEMANA.pdf
```

Ejemplo:

```
240726 N129 SLP OFICINAS CHAPULTEPEC IND H2 4350 FUENTES STDR JONATAN CAMPOS CORTEZ SEM 30.3.pdf
```

- **Fecha, Concepto, Importe y Beneficiario (Cuenta Abono)** se extraen
  automáticamente del PDF.
- **Empresa** (cuenta origen) y **Banco** se detectan por patrones de texto/diseño
  del comprobante (ver `backend/config.py`); si no se reconocen, se seleccionan
  manualmente en la tabla.
- **Semana (SEM)** siempre se captura a mano, ya que no aparece en el comprobante.

### Bancos y empresas soportados hoy

| Banco | Código en el nombre | Formato de comprobante |
|---|---|---|
| Santander | `STDR` | "Comprobante de Operación" (SuperLínea), interbancaria o mismo banco |
| Banorte | `BNT` | "Reporte de Transferencia a Otros Bancos" |

| Empresa (cuenta origen) | Código en el nombre |
|---|---|
| The Fuentes Corporation | `FUENTES` |
| Janupi Construcciones | `JANUPI` |

## Cómo funciona

1. Arrastras uno o varios PDF a la app.
2. El backend lee el texto de cada PDF y llena la tabla con los datos detectados.
3. Revisas/corriges cada fila (los campos en rojo son obligatorios y faltan).
4. Descargas un `.zip` con todos los archivos ya renombrados.

Los archivos originales **no se modifican**; el renombrado ocurre solo sobre las
copias dentro del ZIP.

## Ramas del repositorio

- **`Rename_NB`**: rama de nube, para desplegarse en un servidor (VPS/Docker).
  Trae el `Dockerfile` y el `docker-compose.yml` que esta rama no necesita.
- **`Rename_PC`** (esta rama): rama de uso local, para correrla directamente en
  una PC de oficina (Windows) sin servidor ni Docker.

## Ejecutar en la PC

Lo único que hay que instalar es [Python 3.10+](https://www.python.org/downloads/)
(al instalarlo, marcar la casilla **"Add Python to PATH"**).

1. Descarga/clona esta rama del repositorio.
2. Haz doble clic en `run_local.bat`.
3. El script crea un entorno virtual, instala las dependencias y abre
   automáticamente http://127.0.0.1:8000 en el navegador.
4. Para volver a usar la app, solo vuelve a hacer doble clic en `run_local.bat`
   (la segunda vez es más rápido porque ya no reinstala nada).

La app corre **solo en esta computadora**: `127.0.0.1` no es accesible desde la
red, y los PDF nunca salen del equipo.

### Arrancarla a mano (opcional)

```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload
```

## Agregar un banco o empresa nuevos

- **Empresa nueva**: solo edita `EMPRESA_PROFILES` en `backend/config.py` con
  un `signatures` (texto que identifica la cuenta origen en el comprobante) y
  el `code` correspondiente. No requiere tocar `parser.py`.
- **Banco nuevo**: cada banco trae su propio formato de comprobante (distintas
  etiquetas y orden), así que además de agregar la entrada a `BANK_PROFILES`
  (con `key`, `signatures` y `code`) hay que escribir una función
  `parse_<banco>(text)` en `backend/parser.py` (sigue el patrón de
  `parse_santander`/`parse_banorte`) y registrarla en el diccionario `PARSERS`.

Si un comprobante no coincide con ningún perfil, la app deja los campos vacíos
y los marca como pendientes para selección/captura manual — no se pierde
ningún archivo por un formato no reconocido.

## Estructura del proyecto

```
run_local.bat     # Lanzador: doble clic para usar la app
backend/
  app.py          # API FastAPI (parseo y generación del ZIP)
  parser.py       # Extracción de texto y campos del PDF
  filenaming.py   # Construcción del nombre final de archivo
  config.py       # Catálogo de bancos y empresas reconocidos
  requirements.txt
frontend/
  index.html, app.js, styles.css   # UI sin frameworks, sin paso de build
```
