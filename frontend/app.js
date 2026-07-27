const dropzone = document.getElementById("dropzone");
const fileInput = document.getElementById("file-input");
const indexDropzone = document.getElementById("index-dropzone");
const indexInput = document.getElementById("index-input");
const indexSummary = document.getElementById("index-summary");
const tableSection = document.getElementById("table-section");
const tbody = document.getElementById("files-tbody");
const statusText = document.getElementById("status-text");
const downloadBtn = document.getElementById("download-btn");
const bancosList = document.getElementById("bancos-list");
const empresasList = document.getElementById("empresas-list");

const REQUIRED_FIELDS = ["fecha", "concepto", "importe", "empresa_code", "banco_code", "beneficiario", "sem"];

const MATCH_LABELS = {
  ok: { text: "Concentrado ✓", css: "match-ok" },
  ambiguo: { text: "Ambiguo ⚠", css: "match-ambiguo" },
  sin_coincidencia: { text: "Sin coincidencia", css: "match-none" },
  sin_indice: { text: "", css: "" },
};

let items = []; // { id, file, fields: {...}, warnings: [], matchStatus }
let indexFile = null; // El concentrado se reenvía en cada /api/parse

function escapeHtml(text) {
  return String(text ?? "").replace(/[&<>"']/g, (c) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[c]);
}

// Debe coincidir con sanitize_token del backend: los campos se separan con
// espacios, así que el nombre final no lleva guiones bajos.
function sanitizeToken(text) {
  if (!text) return "";
  const noAccents = text.normalize("NFKD").replace(/[̀-ͯ]/g, "");
  let out = noAccents.toUpperCase().replace(/[^A-Z0-9 ._-]/g, "");
  return out.replace(/_/g, " ").replace(/\s+/g, " ").trim();
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
  return `${parts.join(" ")}.${extension}`;
}

function extOf(filename) {
  const idx = filename.lastIndexOf(".");
  return idx >= 0 ? filename.slice(idx + 1) : "pdf";
}

async function loadOptions() {
  const res = await fetch("/api/options");
  const data = await res.json();
  bancosList.innerHTML = data.bancos.map((c) => `<option value="${escapeHtml(c)}"></option>`).join("");
  empresasList.innerHTML = data.empresas
    .map((e) => `<option value="${escapeHtml(e.code)}">${escapeHtml(e.label)}</option>`)
    .join("");
}

function renderRow(item) {
  const tr = document.createElement("tr");
  tr.dataset.id = item.id;

  const ext = extOf(item.file.name);
  const match = MATCH_LABELS[item.matchStatus] || MATCH_LABELS.sin_indice;

  tr.innerHTML = `
    <td>
      <div class="original-name">${escapeHtml(item.file.name)}</div>
      ${match.text ? `<span class="badge ${match.css}">${match.text}</span>` : ""}
      ${item.warnings.length ? `<div class="warnings">${item.warnings.map(escapeHtml).join("<br/>")}</div>` : ""}
    </td>
    <td><input type="text" data-field="fecha" value="${escapeHtml(item.fields.fecha)}" placeholder="DDMMAA" maxlength="6" /></td>
    <td><input type="text" data-field="concepto" value="${escapeHtml(item.fields.concepto)}" /></td>
    <td><input type="text" data-field="importe" value="${escapeHtml(item.fields.importe)}" /></td>
    <td><input type="text" data-field="empresa_code" list="empresas-list" value="${escapeHtml(item.fields.empresa_code)}" /></td>
    <td><input type="text" data-field="banco_code" list="bancos-list" value="${escapeHtml(item.fields.banco_code)}" /></td>
    <td><input type="text" data-field="beneficiario" value="${escapeHtml(item.fields.beneficiario)}" /></td>
    <td><input type="text" data-field="sem" value="${escapeHtml(item.fields.sem)}" placeholder="ej. 30.3" /></td>
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
  const allValid =
    items.length > 0 &&
    items.every((item) => REQUIRED_FIELDS.every((f) => String(item.fields[f] || "").trim()));
  downloadBtn.disabled = !allValid;
}

function renderIndexSummary(info) {
  indexSummary.classList.remove("hidden");
  if (!info) {
    indexSummary.innerHTML = "";
    indexSummary.classList.add("hidden");
    return;
  }
  if (info.error) {
    indexSummary.innerHTML = `<div class="summary-error">${escapeHtml(info.error)}</div>`;
    return;
  }

  const cols = Object.entries(info.columns || {})
    .map(([logical, header]) => `<li><strong>${escapeHtml(logical)}</strong> → “${escapeHtml(header)}”</li>`)
    .join("");

  const pendientes = (info.pendientes || []).length
    ? `<details class="pendientes">
         <summary>${info.pendientes.length} pago(s) del concentrado sin comprobante</summary>
         <ul>${info.pendientes
           .map((p) => `<li>Fila ${p.fila}: ${escapeHtml(p.requisicion || "(sin req.)")} — ${escapeHtml(p.nombre)} — $${escapeHtml(p.pago)}</li>`)
           .join("")}</ul>
       </details>`
    : "";

  const conteo =
    info.matched !== undefined
      ? `<p><strong>${info.matched}</strong> de ${items.length} comprobante(s) emparejados${
          info.ambiguous ? `, <span class="warn-inline">${info.ambiguous} ambiguo(s)</span>` : ""
        }.</p>`
      : "";

  indexSummary.innerHTML = `
    <p class="summary-title">📄 ${escapeHtml(info.filename)} — ${info.row_count} pago(s) leídos</p>
    <p class="summary-sub">Columnas reconocidas:</p>
    <ul class="cols">${cols}</ul>
    ${conteo}
    ${(info.warnings || []).map((w) => `<div class="summary-warn">${escapeHtml(w)}</div>`).join("")}
    ${pendientes}
  `;
}

async function handleIndexFile(file) {
  if (!file) return;
  indexFile = file;
  indexSummary.classList.remove("hidden");
  indexSummary.innerHTML = `<p class="summary-title">Leyendo ${escapeHtml(file.name)}…</p>`;

  const formData = new FormData();
  formData.append("index_file", file);
  const res = await fetch("/api/index", { method: "POST", body: formData });
  const data = await res.json();

  if (!res.ok) {
    indexFile = null;
    renderIndexSummary({ error: data.detail || "No se pudo leer el concentrado." });
    return;
  }
  renderIndexSummary(data);

  // Si ya había PDFs cargados, se vuelven a emparejar con el nuevo índice.
  if (items.length) await reparseAll();
}

async function parseFiles(files) {
  const formData = new FormData();
  files.forEach((f) => formData.append("files", f));
  if (indexFile) formData.append("index_file", indexFile);

  const res = await fetch("/api/parse", { method: "POST", body: formData });
  const data = await res.json();
  if (!res.ok) throw new Error(data.detail || "Error al procesar los archivos.");
  return data;
}

function itemFromResult(file, result) {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    file,
    fields: {
      fecha: result.fecha || "",
      concepto: result.concepto || "",
      importe: result.importe || "",
      empresa_code: result.empresa_code || "",
      banco_code: result.banco_code || "",
      beneficiario: result.beneficiario || "",
      sem: result.sem || "",
    },
    warnings: result.warnings || [],
    matchStatus: result.match_status || "sin_indice",
  };
}

async function reparseAll() {
  statusText.textContent = "Volviendo a emparejar con el concentrado…";
  const files = items.map((item) => item.file);
  try {
    const data = await parseFiles(files);
    items = data.files.map((result, i) => itemFromResult(files[i], result));
    tbody.innerHTML = "";
    items.forEach(renderRow);
    if (data.index) renderIndexSummary(data.index);
    statusText.textContent = `${items.length} archivo(s) listo(s) para revisar.`;
    updateDownloadState();
  } catch (err) {
    statusText.textContent = err.message;
  }
}

async function handleFiles(fileList) {
  const newFiles = Array.from(fileList).filter(
    (f) => f.type === "application/pdf" || f.name.toLowerCase().endsWith(".pdf")
  );
  if (newFiles.length === 0) return;

  tableSection.classList.remove("hidden");
  statusText.textContent = "Procesando archivos...";

  // Se reprocesa todo junto para que el emparejamiento 1 a 1 con el
  // concentrado tome en cuenta los archivos que ya estaban cargados.
  const allFiles = [...items.map((item) => item.file), ...newFiles];

  try {
    const data = await parseFiles(allFiles);
    items = data.files.map((result, i) => itemFromResult(allFiles[i], result));
    tbody.innerHTML = "";
    items.forEach(renderRow);
    if (data.index) renderIndexSummary(data.index);
    statusText.textContent = `${items.length} archivo(s) listo(s) para revisar.`;
    updateDownloadState();
  } catch (err) {
    statusText.textContent = err.message;
  }
}

function wireDropzone(zone, onFiles) {
  zone.addEventListener("dragover", (e) => {
    e.preventDefault();
    zone.classList.add("drag-over");
  });
  zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("drag-over");
    onFiles(e.dataTransfer.files);
  });
}

wireDropzone(dropzone, handleFiles);
wireDropzone(indexDropzone, (files) => handleIndexFile(files[0]));
fileInput.addEventListener("change", (e) => handleFiles(e.target.files));
indexInput.addEventListener("change", (e) => handleIndexFile(e.target.files[0]));

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
