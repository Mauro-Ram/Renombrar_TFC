# Renombrar TFC — multi-banco (con concentrado)

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
  del comprobante (ver `backend/config.py`); si no se reconocen, se completan
  manualmente en la tabla.
- **Semana (SEM)** normalmente se captura a mano, ya que no aparece en el
  comprobante (salvo que el concentrado traiga una columna de semana).

### Formatos de comprobante soportados hoy

| Formato | Banco en el nombre |
|---|---|
| Santander — "Comprobante de Operación" (SuperLínea), interbancaria o mismo banco | `STDR` |
| Banorte — "Reporte de Transferencia a Otros Bancos" | `BNT` |
| Dispersión — "Comprobante de transferencia" | del concentrado |

| Empresa (cuenta origen) | Código en el nombre |
|---|---|
| The Fuentes Corporation | `FUENTES` |
| Janupi Construcciones | `JANUPI` |
| Desarrollos Ark Zoque | `ARKZOQUE` |

Los **bancos no son una lista cerrada**: el código del nombre de archivo sale de
`BANK_CODE_ALIASES` en `backend/config.py` cuando el banco es conocido y, si no,
se genera a partir de su nombre. Un banco nuevo en el concentrado funciona sin
tocar código; agregarlo a la tabla solo sirve para fijarle una abreviatura.

## Cómo funciona

1. *(Opcional)* Subes el **concentrado de pagos** (`.xlsx` o `.csv`).
2. Arrastras uno o varios PDF a la app.
3. El backend lee el texto de cada PDF, lo empareja contra el concentrado y
   llena la tabla.
4. Revisas/corriges cada fila (los campos en rojo son obligatorios y faltan).
5. Descargas un `.zip` con todos los archivos ya renombrados.

Los archivos originales **no se modifican**; el renombrado ocurre solo sobre las
copias dentro del ZIP.

## El concentrado de pagos como índice

Algunos comprobantes (los de dispersión) no traen la información que necesita el
nombre de archivo: el concepto es genérico (`ABONO`) y el banco pagador no
aparece. Para esos casos se sube el concentrado, del que se toman:

| Campo del nombre | Columna del concentrado |
|---|---|
| Concepto | Número de requisición |
| Beneficiario | Nombre |
| Banco | Banco |
| Importe | Pago |

La **fecha siempre sale del comprobante**, nunca del concentrado.

No hace falta que el concentrado tenga un formato fijo: la app busca la fila de
encabezados (aunque haya títulos y filas vacías arriba) y reconoce sinónimos de
columna — `PAGO`/`IMPORTE`/`MONTO`, `NOMBRE`/`BENEFICIARIO`,
`REQUISICIÓN`/`FOLIO`, etc. Después de leerlo, la app muestra qué columna usó
para cada campo, para poder confirmarlo de un vistazo.

### Cómo se emparejan los comprobantes

Cada PDF se busca en el concentrado por **nombre + monto**. La comparación de
nombres ignora acentos, mayúsculas y el orden de las palabras.

Ese par no es una llave única: es normal que a una misma persona se le hagan dos
pagos iguales el mismo día bajo requisiciones distintas. Por eso la asignación es
**1 a 1** (una fila del concentrado se consume por un solo comprobante, así que
dos PDFs idénticos reciben requisiciones distintas) y esos casos se marcan como
**Ambiguo**: la app asigna una fila, pero avisa cuáles requisiciones empataron
para que se verifique a mano cuál corresponde a cada comprobante.

Cada archivo queda con uno de estos estados:

- **Concentrado ✓** — se encontró una única coincidencia.
- **Ambiguo ⚠** — varias filas empatan en nombre y monto; hay que verificar.
- **Sin coincidencia** — no está en el concentrado; se usan los datos del PDF.

Al final se listan también los pagos del concentrado que se quedaron **sin
comprobante**, para detectar los que faltan por descargar del banco.

## Ramas del repositorio

Son **dos proyectos distintos**, no versiones del mismo:

**Proyecto base** — renombrado a partir del PDF solamente:

- **`Rename_NB`**: rama de nube, para desplegarse en un servidor (VPS/Docker).
- **`Rename_PC`**: rama de uso local, mismo código más `run_local.bat` para
  correrla en una PC de oficina (Windows) sin servidor ni Docker.

**Proyecto multi-banco** — agrega el concentrado de pagos como índice:

- **`Rename_PC_Multiple_BK`** (esta rama): para los SPEI de pago que salen de
  múltiples cuentas, donde el banco no es fijo y el comprobante no trae ni la
  requisición ni el banco pagador. Se usa igual que `Rename_PC` (local, con
  `run_local.bat`), pero además acepta el concentrado de Excel.

Los cambios de esta rama **no están** en `Rename_NB` ni en `Rename_PC`.

## Ejecutar en local (sin Docker)

Requiere tener [Python 3.10+](https://www.python.org/downloads/) instalado en
la PC (al instalarlo, marcar la casilla "Add Python to PATH").

1. Descarga/clona esta rama del repositorio.
2. Haz doble clic en `run_local.bat`.
3. El script crea un entorno virtual, instala las dependencias y abre
   automáticamente http://127.0.0.1:8000 en el navegador.
4. Para volver a usar la app, solo vuelve a hacer doble clic en `run_local.bat`
   (la segunda vez es más rápido porque ya no reinstala nada).

## Ejecutar en local con Python directamente

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

## Agregar un banco, empresa o formato nuevos

- **Banco nuevo**: no hay que hacer nada. Si viene en el concentrado, su código
  se genera solo. Para fijarle una abreviatura (p. ej. `SANTANDER` → `STDR`),
  agrega una línea a `BANK_CODE_ALIASES` en `backend/config.py`.
- **Empresa nueva**: edita `EMPRESA_PROFILES` en `backend/config.py` con un
  `signatures` (texto que identifica la cuenta origen en el comprobante) y el
  `code` correspondiente. No requiere tocar `parser.py`.
- **Formato de comprobante nuevo**: cada formato trae distintas etiquetas y
  orden, así que además de agregar la entrada a `FORMAT_PROFILES` (con `key`,
  `signatures` y `code` — vacío si el comprobante no dice el banco pagador) hay
  que escribir una función `parse_<formato>(text)` en `backend/parser.py`
  (sigue el patrón de `parse_santander`/`parse_transferencia`) y registrarla en
  el diccionario `PARSERS`.

Si un comprobante no coincide con ningún perfil, la app deja los campos vacíos
y los marca como pendientes para captura manual — no se pierde ningún archivo
por un formato no reconocido.

## Estructura del proyecto

```
backend/
  app.py          # API FastAPI (parseo, emparejamiento y generación del ZIP)
  parser.py       # Extracción de texto y campos del PDF
  indexfile.py    # Lectura del concentrado de pagos (.xlsx/.csv)
  matching.py     # Emparejamiento comprobante <-> fila del concentrado
  filenaming.py   # Construcción del nombre final de archivo
  config.py       # Catálogo de formatos, empresas y códigos de banco
  text_utils.py   # Normalización de texto compartida
frontend/
  index.html, app.js, styles.css   # UI sin frameworks, sin paso de build
Dockerfile, docker-compose.yml
```
