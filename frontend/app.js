const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const tableSection = document.getElementById("table-section");
const tbody = document.getElementById("files-tbody");
const statusText = document.getElementById("status-text");
const downloadBtn = document.getElementById("download-btn");

const REQUIRED_FIELDS = ["fecha", "concepto", "importe", "empresa_code", "banco_code", "beneficiario", "sem"];

let items = []; // { id, file, fields: {...}, warnings: [] }
let empresaOptions = [];
let bancoOptions = [];

function sanitizeToken(text) {
  if (!text) return "";
  const noAccents = text.normalize("NFKD").replace(/[̀-ͯ]/g, "");
  let out = noAccents.toUpperCase().replace(/[^A-Z0-9 ._-]/g, "");
  out = out.trim().replace(/\s+/g, "_").replace(/_+/g, "_");
  return out;
}

function buildFilename(fields, extension) {
  const parts = [
    sanitizeToken(fields.fecha),
    sanitizeToken(fields.concepto),
    sanitizeToken(fields.importe),
    sanitizeToken(fields.empresa_code),
    sanitizeToken(fields.banco_code),
    sanitizeToken(fields.beneficiario),
    "SEM",
    sanitizeToken(fields.sem),
  ].filter(Boolean);
  return `${parts.join("_")}.${extension}`;
}

function extOf(filename) {
  const idx = filename.lastIndexOf(".");
  return idx >= 0 ? filename.slice(idx + 1) : "pdf";
}

async function loadOptions() {
  const res = await fetch("/api/options");
  const data = await res.json();
  empresaOptions = data.empresas;
  bancoOptions = data.bancos;
}

function optionsHtml(options, selected) {
  const blank = `<option value="" ${!selected ? "selected" : ""}>-- Selecciona --</option>`;
  const rest = options
    .map(
      (o) =>
        `<option value="${o.code}" ${o.code === selected ? "selected" : ""}>${o.label} (${o.code})</option>`
    )
    .join("");
  return blank + rest;
}

function renderRow(item) {
  const tr = document.createElement("tr");
  tr.dataset.id = item.id;

  const ext = extOf(item.file.name);

  tr.innerHTML = `
    <td>
      <div class="original-name">${item.file.name}</div>
      ${item.warnings.length ? `<div class="warnings">${item.warnings.join("<br/>")}</div>` : ""}
    </td>
    <td><input type="text" data-field="fecha" value="${item.fields.fecha}" placeholder="DDMMAA" maxlength="6" /></td>
    <td><input type="text" data-field="concepto" value="${item.fields.concepto}" /></td>
    <td><input type="text" data-field="importe" value="${item.fields.importe}" /></td>
    <td><select data-field="empresa_code">${optionsHtml(empresaOptions, item.fields.empresa_code)}</select></td>
    <td><select data-field="banco_code">${optionsHtml(bancoOptions, item.fields.banco_code)}</select></td>
    <td><input type="text" data-field="beneficiario" value="${item.fields.beneficiario}" /></td>
    <td><input type="text" data-field="sem" value="${item.fields.sem}" placeholder="ej. 30.3" /></td>
    <td class="filename-preview" data-preview></td>
  `;

  tbody.appendChild(tr);

  tr.querySelectorAll("[data-field]").forEach((el) => {
    el.addEventListener("input", () => {
      item.fields[el.dataset.field] = el.value;
      updateRowPreview(tr, item, ext);
      updateDownloadState();
    });
  });

  updateRowPreview(tr, item, ext);
}

function updateRowPreview(tr, item, ext) {
  const preview = tr.querySelector("[data-preview]");
  const missing = REQUIRED_FIELDS.filter((f) => !String(item.fields[f] || "").trim());

  tr.querySelectorAll("[data-field]").forEach((el) => {
    el.classList.toggle("invalid", missing.includes(el.dataset.field));
  });

  preview.textContent = missing.length
    ? `Falta completar: ${missing.join(", ")}`
    : buildFilename(item.fields, ext);
}

function updateDownloadState() {
  const allValid = items.length > 0 && items.every((item) => REQUIRED_FIELDS.every((f) => String(item.fields[f] || "").trim()));
  downloadBtn.disabled = !allValid;
}

async function handleFiles(fileList) {
  const newFiles = Array.from(fileList).filter((f) => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf"));
  if (newFiles.length === 0) return;

  tableSection.classList.remove("hidden");
  statusText.textContent = "Procesando archivos...";

  const formData = new FormData();
  newFiles.forEach((f) => formData.append("files", f));

  const res = await fetch("/api/parse", { method: "POST", body: formData });
  if (!res.ok) {
    statusText.textContent = "Error al procesar los archivos.";
    return;
  }
  const results = await res.json();

  results.forEach((result, i) => {
    const id = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const item = {
      id,
      file: newFiles[i],
      fields: {
        fecha: result.fecha || "",
        concepto: result.concepto || "",
        importe: result.importe || "",
        empresa_code: result.empresa_code || "",
        banco_code: result.banco_code || "",
        beneficiario: result.beneficiario || "",
        sem: "",
      },
      warnings: result.warnings || [],
    };
    items.push(item);
    renderRow(item);
  });

  statusText.textContent = `${items.length} archivo(s) listo(s) para revisar.`;
  updateDownloadState();
}

dropzone.addEventListener("dragover", (e) => {
  e.preventDefault();
  dropzone.classList.add("drag-over");
});
dropzone.addEventListener("dragleave", () => dropzone.classList.remove("drag-over"));
dropzone.addEventListener("drop", (e) => {
  e.preventDefault();
  dropzone.classList.remove("drag-over");
  handleFiles(e.dataTransfer.files);
});
fileInput.addEventListener("change", (e) => handleFiles(e.target.files));

downloadBtn.addEventListener("click", async () => {
  downloadBtn.disabled = true;
  statusText.textContent = "Generando ZIP...";

  const formData = new FormData();
  items.forEach((item) => formData.append("files", item.file));
  formData.append("fields_json", JSON.stringify(items.map((item) => item.fields)));

  const res = await fetch("/api/rename", { method: "POST", body: formData });
  if (!res.ok) {
    statusText.textContent = "Error al generar el ZIP. Revisa los campos.";
    updateDownloadState();
    return;
  }

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = "archivos_renombrados.zip";
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);

  statusText.textContent = "ZIP descargado.";
  updateDownloadState();
});

loadOptions();
