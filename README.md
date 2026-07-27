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
red, y los PDF nunca salen del equipo.

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
