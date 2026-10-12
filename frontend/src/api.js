// Single place that talks to the backend. Contracts mirror app/schemas.py of the FastAPI service.
export const API_BASE = String(import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000").replace(/\/+$/, "");

export class ApiError extends Error {
  constructor({ status = 0, code = "unknown", message = "", details = null, kind = "http" }) {
    super(message || code);
    this.status = status;
    this.code = code;
    this.details = details;
    this.kind = kind; // "http" | "network" | "timeout" | "aborted" | "parse"
  }
}

async function parseError(status, text) {
  try {
    const body = JSON.parse(text);
    if (body && body.error) {
      return new ApiError({ status, code: body.error.code, message: body.error.message, details: body.error.details });
    }
  } catch { /* not JSON */ }
  return new ApiError({ status, code: "http_error", message: `The server returned HTTP ${status}.` });
}

export async function request(path, { method = "GET", json, timeoutMs = 30000, signal } = {}) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort("timeout"), timeoutMs);
  if (signal) signal.addEventListener("abort", () => ctrl.abort("aborted"), { once: true });
  try {
    const res = await fetch(API_BASE + path, {
      method,
      headers: json !== undefined ? { "Content-Type": "application/json" } : undefined,
      body: json !== undefined ? JSON.stringify(json) : undefined,
      signal: ctrl.signal,
    });
    const text = await res.text();
    if (!res.ok) throw await parseError(res.status, text);
    try { return JSON.parse(text); } catch { throw new ApiError({ kind: "parse", code: "bad_response", message: "The server sent an unreadable response." }); }
  } catch (e) {
    if (e instanceof ApiError) throw e;
    if (ctrl.signal.aborted) {
      const timedOut = ctrl.signal.reason === "timeout";
      throw new ApiError({ kind: timedOut ? "timeout" : "aborted", code: timedOut ? "timeout" : "aborted",
        message: timedOut ? "The request took too long." : "Request cancelled." });
    }
    throw new ApiError({ kind: "network", code: "network", message: "Cannot reach the backend." });
  } finally {
    clearTimeout(timer);
  }
}

export const getHealth = (signal) => request("/health", { timeoutMs: 6000, signal });
export const postText = (payload) => request("/api/v1/triage/text", { method: "POST", json: payload, timeoutMs: 60000 });
export const listTriage = (limit = 100) => request(`/api/v1/triage?limit=${limit}`);
export const getTriage = (id) => request(`/api/v1/triage/${encodeURIComponent(id)}`);
export const listPatients = (status) => request("/api/v1/patients" + (status ? `?status=${encodeURIComponent(status)}` : ""));
export const createPatient = (payload) => request("/api/v1/patients", { method: "POST", json: payload });
export const updatePatient = (id, payload) => request(`/api/v1/patients/${encodeURIComponent(id)}`, { method: "PATCH", json: payload });

/** Multipart upload with progress. The browser sets the multipart boundary; we never set Content-Type. */
export function postAudio(file, ageGroup, { onProgress, onUploaded, timeoutMs = 120000 } = {}) {
  const xhr = new XMLHttpRequest();
  const promise = new Promise((resolve, reject) => {
    const form = new FormData();
    form.append("file", file, file.name);
    if (ageGroup) form.append("age_group", ageGroup);
    xhr.open("POST", API_BASE + "/api/v1/triage/audio");
    xhr.timeout = timeoutMs;
    xhr.upload.onprogress = (e) => { if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total); };
    xhr.upload.onload = () => onUploaded && onUploaded();
    xhr.onload = async () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try { resolve(JSON.parse(xhr.responseText)); }
        catch { reject(new ApiError({ kind: "parse", code: "bad_response", message: "The server sent an unreadable response." })); }
      } else reject(await parseError(xhr.status, xhr.responseText));
    };
    xhr.onerror = () => reject(new ApiError({ kind: "network", code: "network", message: "Cannot reach the backend." }));
    xhr.ontimeout = () => reject(new ApiError({ kind: "timeout", code: "timeout", message: "The request took too long." }));
    xhr.onabort = () => reject(new ApiError({ kind: "aborted", code: "aborted", message: "Upload cancelled." }));
    xhr.send(form);
  });
  return { promise, abort: () => xhr.abort() };
}

/** Download the real PDF; verifies it is a PDF before saving. */
export async function downloadReport(requestId) {
  let res;
  try {
    res = await fetch(`${API_BASE}/api/v1/reports/${encodeURIComponent(requestId)}/pdf`);
  } catch {
    throw new ApiError({ kind: "network", code: "network", message: "Cannot reach the backend." });
  }
  if (!res.ok) throw await parseError(res.status, await res.text());
  const blob = await res.blob();
  const head = await blob.slice(0, 5).text();
  if (head !== "%PDF-") throw new ApiError({ kind: "parse", code: "bad_pdf", message: "The server did not return a valid PDF." });
  const cd = res.headers.get("content-disposition") || "";
  const m = /filename="?([^";]+)"?/i.exec(cd);
  const filename = m ? m[1] : `medtriage-report-${requestId.slice(0, 8)}.pdf`;
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename;
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
  return { filename, bytes: blob.size };
}

/** Turn any error into a short, actionable sentence for the UI. Never shows stack traces. */
export function friendlyError(err) {
  if (!(err instanceof ApiError)) return "Something unexpected went wrong. Please try again.";
  switch (err.code) {
    case "network": return `Cannot reach the backend at ${API_BASE}. Start it (start_backend.bat) and check the status indicator.`;
    case "timeout": return "The request took too long. The AI service may be slow or unavailable - try again.";
    case "aborted": return err.message;
    case "transcription_not_configured": return "Speech-to-text is not configured. Add GROQ_API_KEY to the backend .env file and restart the backend.";
    case "transcription_rate_limited": return "The speech-to-text provider rate limit was reached. Wait a moment and try again.";
    case "transcription_timeout": return "Transcription timed out. Try a shorter recording.";
    case "transcription_auth_failed": return "The speech-to-text provider rejected the API key. Check GROQ_API_KEY in the backend .env.";
    case "transcription_empty_transcript": return "No speech was detected in the audio. Try a clearer or louder recording.";
    case "transcription_provider_error":
    case "transcription_provider_unreachable":
    case "transcription_malformed_response": return "The speech-to-text service is unavailable right now. Try again later or use text intake.";
    case "file_too_large": return err.message + " Try a shorter recording.";
    case "empty_file": return "The selected file is empty.";
    case "unreadable_audio": return "That file could not be read as audio of the declared type.";
    case "triage_not_found":
    case "report_not_found": return "No case exists for this request ID (it may have been mistyped or the database was reset).";
    case "patient_not_found": return "That queue entry no longer exists.";
    case "validation_error": {
      const d = Array.isArray(err.details) ? err.details.map((x) => x.message).filter(Boolean).join("; ") : "";
      return "The request was rejected: " + (d || "invalid input") + ".";
    }
    default: return err.message || "Request failed.";
  }
}
