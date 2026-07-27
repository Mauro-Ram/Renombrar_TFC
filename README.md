# Renombrar TFC — multi-banco (con concentrado)

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
- **`Rename_PC`**: rama de uso local, para correrla en una PC de oficina
  (Windows) sin servidor ni Docker.

**Proyecto multi-banco** — agrega el concentrado de pagos como índice:

- **`Rename_PC_Multiple_BK`** (esta rama): para los SPEI de pago que salen de
  múltiples cuentas, donde el banco no es fijo y el comprobante no trae ni la
  requisición ni el banco pagador. Se usa igual que `Rename_PC` (local, con
  `run_local.bat`), pero además acepta el concentrado de Excel.

Los cambios de esta rama **no están** en `Rename_NB` ni en `Rename_PC`.

## Instalar en una PC nueva

### 1. Instalar Python

Descarga Python 3.10 o superior desde **<https://www.python.org/downloads/>**
— *no desde la Microsoft Store*.

En la **primera pantalla** del instalador, antes de darle a "Install",
**marca la casilla `Add python.exe to PATH`**. Es el paso que más se olvida y
sin él Windows no encuentra Python después.

### 2. Descargar el programa

Si bajas el ZIP desde GitHub, **descomprímelo primero** (clic derecho →
"Extraer todo"). El `.bat` no funciona ejecutándolo desde dentro del ZIP.

### 3. Ejecutar

1. Haz doble clic en `run_local.bat`.
2. La primera vez tarda un par de minutos preparando el entorno.
3. Se abre solo http://127.0.0.1:8000 en el navegador.
4. Las siguientes veces arranca en segundos.

La app corre **solo en esa computadora**: `127.0.0.1` no es accesible desde la
red, y ni los PDF ni el concentrado salen del equipo.

## Si no arranca

El `.bat` verifica cada paso y muestra el motivo en pantalla. Los casos más
frecuentes en una laptop nueva:

### "Windows no encuentra Python" (aunque ya lo instalaste)

- **Se instaló sin marcar "Add python.exe to PATH".** Vuelve a abrir el
  instalador de Python, elige *Modify* (o reinstala) y marca la casilla.
- **El alias de la Microsoft Store está capturando el comando.** En Windows 10
  y 11, escribir `python` abre la tienda en vez del programa. Ve a
  *Configuración → Aplicaciones → Configuración avanzada de la aplicación →
  Alias de ejecución de la aplicación* y **apaga** `python.exe` y `python3.exe`.
- **Falta reiniciar.** El PATH se refresca al iniciar sesión de nuevo.

Para comprobar si Python quedó bien instalado, abre una ventana de `cmd` y
escribe:

```
py --version
```

Si responde con un número de versión, el `.bat` va a funcionar.

### La ventana se abre y se cierra de inmediato

Suele ser una versión vieja del `.bat`. Descarga de nuevo esta rama: el
lanzador actual siempre deja la ventana abierta y explica el error.

### "no se pudieron descargar las dependencias"

Falta internet, o el antivirus/proxy de la empresa está bloqueando la descarga
de paquetes. Prueba con otra red.

### Arrancarla a mano (opcional)

```bash
cd backend
pip install -r requirements.txt
uvicorn app:app --reload
```

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
run_local.bat     # Lanzador: doble clic para usar la app
backend/
  app.py          # API FastAPI (parseo, emparejamiento y generación del ZIP)
  parser.py       # Extracción de texto y campos del PDF
  indexfile.py    # Lectura del concentrado de pagos (.xlsx/.csv)
  matching.py     # Emparejamiento comprobante <-> fila del concentrado
  filenaming.py   # Construcción del nombre final de archivo
  config.py       # Catálogo de formatos, empresas y códigos de banco
  text_utils.py   # Normalización de texto compartida
  requirements.txt
frontend/
  index.html, app.js, styles.css   # UI sin frameworks, sin paso de build
```
