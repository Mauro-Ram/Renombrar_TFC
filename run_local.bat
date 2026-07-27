@echo off
setlocal EnableExtensions
title Renombrar TFC

cd /d "%~dp0"

echo.
echo  ==========================================
echo    RENOMBRAR TFC
echo  ==========================================
echo.

rem ---------- 1. Comprobar que los archivos esten completos ----------
if not exist "backend\app.py" goto :error_estructura
if not exist "backend\requirements.txt" goto :error_estructura

rem ---------- 2. Localizar Python ----------
rem Se prueba primero el lanzador "py", que instala python.org y que el
rem alias de la Microsoft Store no intercepta.
py -3 --version >nul 2>&1
if not errorlevel 1 goto :usar_py

python --version >nul 2>&1
if not errorlevel 1 goto :usar_python

goto :error_sin_python

:usar_py
set "PY_CMD=py -3"
goto :python_ok

:usar_python
set "PY_CMD=python"
goto :python_ok

:python_ok
echo  [1/3] Python detectado:
echo.
%PY_CMD% --version
echo.

rem ---------- 3. Preparar el entorno virtual ----------
set "VENV_PY=%~dp0backend\.venv\Scripts\python.exe"

if exist "%VENV_PY%" goto :venv_listo

echo  [2/3] Preparando el entorno por primera vez.
echo        Esto puede tardar un par de minutos, no cierres la ventana.
echo.
%PY_CMD% -m venv "%~dp0backend\.venv"
if errorlevel 1 goto :error_venv
if not exist "%VENV_PY%" goto :error_venv
goto :instalar

:venv_listo
echo  [2/3] Entorno ya preparado.
echo.

:instalar
echo  [3/3] Revisando dependencias...
echo.
"%VENV_PY%" -m pip install --disable-pip-version-check -q -r "%~dp0backend\requirements.txt"
if errorlevel 1 goto :error_pip

rem ---------- 4. Arrancar ----------
echo.
echo  ==========================================
echo    LISTO - http://127.0.0.1:8000
echo  ==========================================
echo.
echo  El navegador se abre solo en unos segundos.
echo.
echo  NO CIERRES esta ventana mientras uses la aplicacion.
echo  Para terminar: cierra esta ventana o pulsa Ctrl+C.
echo.

start "" http://127.0.0.1:8000

cd /d "%~dp0backend"
"%VENV_PY%" -m uvicorn app:app --host 127.0.0.1 --port 8000

echo.
echo  El servidor se detuvo.
pause
exit /b 0


rem ================= Mensajes de error =================

:error_estructura
echo  ERROR: no se encuentran los archivos del programa.
echo.
echo  Este archivo run_local.bat debe estar junto a las carpetas
echo  "backend" y "frontend".
echo.
echo  Si descargaste el ZIP desde GitHub:
echo    1. Haz clic derecho en el ZIP y elige "Extraer todo".
echo    2. Entra a la carpeta que se creo.
echo    3. Ejecuta run_local.bat desde ahi.
echo.
echo  No funciona ejecutarlo directamente desde dentro del ZIP.
echo.
pause
exit /b 1

:error_sin_python
echo  ERROR: Windows no encuentra Python.
echo.
echo  Aunque ya lo hayas instalado, suele ser por una de estas razones:
echo.
echo  1^) Se instalo SIN marcar "Add Python to PATH".
echo     Solucion: vuelve a abrir el instalador de Python, elige
echo     "Modify" o reinstala, y MARCA la casilla
echo     "Add python.exe to PATH" en la primera pantalla.
echo.
echo  2^) Windows tiene activo el alias de la Microsoft Store.
echo     Al escribir "python" se abre la tienda en vez del programa.
echo     Solucion: Configuracion ^> Aplicaciones ^> Configuracion
echo     avanzada de la aplicacion ^> Alias de ejecucion de la
echo     aplicacion. APAGA los interruptores "python.exe" y
echo     "python3.exe".
echo.
echo  3^) Falta reiniciar despues de instalar Python.
echo     Solucion: reinicia la laptop y vuelve a intentar.
echo.
echo  Descarga Python desde https://www.python.org/downloads/
echo  y NO desde la Microsoft Store.
echo.
pause
exit /b 1

:error_venv
echo.
echo  ERROR: no se pudo crear el entorno virtual de Python.
echo.
echo  Intenta esto:
echo    1. Borra la carpeta "backend\.venv" si existe.
echo    2. Vuelve a ejecutar run_local.bat.
echo.
echo  Si sigue fallando, puede que la carpeta este sincronizada con
echo  OneDrive o en una ruta con permisos restringidos. Copia el
echo  programa a una carpeta simple como C:\RenombrarTFC y prueba
echo  de nuevo.
echo.
pause
exit /b 1

:error_pip
echo.
echo  ERROR: no se pudieron descargar las dependencias.
echo.
echo  Casi siempre es un problema de red:
echo    - Revisa que la laptop tenga internet.
echo    - El antivirus o el proxy de la empresa puede estar
echo      bloqueando la descarga. Prueba con otra red.
echo.
pause
exit /b 1
