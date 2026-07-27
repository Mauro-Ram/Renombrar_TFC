# Renombrar TFC

Aplicación web interna para renombrar de forma masiva comprobantes SPEI en PDF,
usando el formato:

```
FECHA_CONCEPTO_IMPORTE_EMPRESA_BANCO_BENEFICIARIO_SEM_SEMANA.pdf
```

Ejemplo:

```
240726_N129_SLP_OFICINAS_CHAPULTEPEC_IND_H2_4350_FUENTES_STDR_JONATAN_CAMPOS_CORTEZ_SEM_30.3.pdf
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

- **`Rename_NB`** (esta rama): rama de nube, para desplegarse en un servidor
  (VPS/Docker).
- **`Rename_PC`**: rama de uso local, mismo código más un script para correrla
  directamente en una PC de oficina (Windows) sin servidor ni Docker.

## Ejecutar en local

```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload
```

Abre http://localhost:8000

## Ejecutar con Docker

```bash
docker compose up --build
```

Abre http://localhost:8000

## Desplegar en Hostinger

El *shared hosting* de Hostinger solo sirve PHP y no permite correr una app
Python persistente. Para esta app necesitas un plan **VPS de Hostinger**
(cualquiera que soporte Docker):

1. Entra al VPS por SSH e instala Docker (Hostinger lo ofrece como plantilla
   de sistema operativo, o instálalo manualmente).
2. Copia este repositorio al VPS (`git clone ...`).
3. Corre `docker compose up -d --build`.
4. Configura un dominio/subdominio apuntando al VPS y, opcionalmente, un
   proxy inverso (nginx/Caddy) con HTTPS hacia el puerto `8000`.

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
backend/
  app.py          # API FastAPI (parseo y generación del ZIP)
  parser.py       # Extracción de texto y campos del PDF
  filenaming.py   # Construcción del nombre final de archivo
  config.py       # Catálogo de bancos y empresas reconocidos
frontend/
  index.html, app.js, styles.css   # UI sin frameworks, sin paso de build
Dockerfile, docker-compose.yml
```
