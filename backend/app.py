import io
import json
import os
import zipfile

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from config import BANK_PROFILES, EMPRESA_PROFILES
from filenaming import build_filename, dedupe_filename, missing_fields
from parser import parse_pdf_bytes

app = FastAPI(title="Renombrar TFC")

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


@app.get("/api/options")
def get_options():
    return {
        "empresas": [{"code": p["code"], "label": p["label"]} for p in EMPRESA_PROFILES],
        "bancos": [{"code": p["code"], "label": p["label"]} for p in BANK_PROFILES],
    }


@app.post("/api/parse")
async def parse_files(files: list[UploadFile] = File(...)):
    results = []
    for upload in files:
        data = await upload.read()
        result = parse_pdf_bytes(upload.filename, data)
        results.append(result)
    return results


@app.post("/api/rename")
async def rename_files(
    files: list[UploadFile] = File(...),
    fields_json: str = Form(...),
):
    try:
        fields_list = json.loads(fields_json)
    except json.JSONDecodeError:
        return JSONResponse(status_code=400, content={"detail": "fields_json inválido"})

    if len(fields_list) != len(files):
        return JSONResponse(
            status_code=400,
            content={"detail": "El número de archivos no coincide con el número de registros de datos"},
        )

    errors = []
    for index, fields in enumerate(fields_list):
        missing = missing_fields(fields)
        if missing:
            errors.append({"index": index, "missing": missing})
    if errors:
        return JSONResponse(status_code=400, content={"detail": "Faltan campos obligatorios", "errors": errors})

    used_names: set[str] = set()
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for upload, fields in zip(files, fields_list):
            data = await upload.read()
            _, _, extension = upload.filename.rpartition(".")
            new_name = build_filename(fields, extension or "pdf")
            new_name = dedupe_filename(new_name, used_names)
            zf.writestr(new_name, data)

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=archivos_renombrados.zip"},
    )


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
