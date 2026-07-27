import io
import json
import os
import zipfile

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from config import EMPRESA_PROFILES, bank_code_for, known_bank_codes
from filenaming import build_filename, dedupe_filename, missing_fields
from indexfile import read_index
from matching import apply_match, match_all, unmatched_rows
from parser import parse_pdf_bytes

app = FastAPI(title="Renombrar TFC")

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


@app.get("/api/options")
def get_options():
    return {
        "empresas": [{"code": p["code"], "label": p["label"]} for p in EMPRESA_PROFILES],
        "bancos": known_bank_codes(),
    }


@app.post("/api/index")
async def upload_index(index_file: UploadFile = File(...)):
    """Valida el concentrado y reporta qué columnas se reconocieron."""
    data = await index_file.read()
    try:
        index = read_index(index_file.filename, data)
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"detail": str(exc)})

    return {
        "filename": index_file.filename,
        "columns": index["columns"],
        "header_row": index["header_row"],
        "row_count": len(index["rows"]),
        "warnings": index["warnings"],
        "sample": index["rows"][:5],
    }


@app.post("/api/parse")
async def parse_files(
    files: list[UploadFile] = File(...),
    index_file: UploadFile | None = File(None),
):
    results = [parse_pdf_bytes(upload.filename, await upload.read()) for upload in files]

    for result in results:
        result["match_status"] = "sin_indice"
        result["match_row"] = None

    index_info = None
    if index_file is not None:
        index_data = await index_file.read()
        try:
            index = read_index(index_file.filename, index_data)
        except ValueError as exc:
            return JSONResponse(status_code=400, content={"detail": str(exc)})

        matches = match_all(results, index["rows"])
        for result, match in zip(results, matches):
            apply_match(result, match, bank_code_for)

        sobrantes = unmatched_rows(index["rows"], matches)
        index_info = {
            "filename": index_file.filename,
            "columns": index["columns"],
            "row_count": len(index["rows"]),
            "matched": sum(1 for m in matches if m["row"] is not None),
            "ambiguous": sum(1 for m in matches if m["ambiguo"]),
            "warnings": index["warnings"],
            "pendientes": [
                {
                    "fila": row["fila"],
                    "requisicion": row["requisicion"],
                    "nombre": row["nombre"],
                    "pago": row["pago"],
                }
                for row in sobrantes
            ],
        }

    return {"files": results, "index": index_info}


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
