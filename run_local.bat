@echo off
setlocal

cd /d "%~dp0backend"

if not exist ".venv" (
    echo Creando entorno virtual de Python...
    python -m venv .venv
)

call .venv\Scripts\activate.bat

echo Instalando/actualizando dependencias...
pip install -r requirements.txt -q

start "" http://127.0.0.1:8000

echo.
echo Renombrar TFC esta corriendo en http://127.0.0.1:8000
echo No cierres esta ventana mientras uses la aplicacion.
echo.

uvicorn app:app --host 127.0.0.1 --port 8000

pause
