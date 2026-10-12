import { useEffect, useRef, useState } from "react";

const TYPES = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];
const EXT = { "audio/webm": "webm", "audio/ogg": "ogg", "audio/mp4": "mp4" };
const MAX_SECONDS = 120;

export function recordingSupported() {
  return typeof window !== "undefined" && !!navigator.mediaDevices?.getUserMedia && typeof window.MediaRecorder !== "undefined";
}

/** Real microphone recorder (MediaRecorder). Calls onRecorded(File) when stopped. */
export default function Recorder({ onRecorded, disabled }) {
  const [recording, setRecording] = useState(false);
  const [secs, setSecs] = useState(0);
  const [err, setErr] = useState(null);
  const mr = useRef(null), stream = useRef(null), chunks = useRef([]), timer = useRef(null);

  useEffect(() => () => { clearInterval(timer.current); stream.current?.getTracks().forEach((t) => t.stop()); }, []);

  async function start() {
    setErr(null);
    try {
      stream.current = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch (e) {
      setErr(e && e.name === "NotAllowedError" ? "Microphone permission was denied. Allow it in the browser, or upload a file instead."
        : "No usable microphone was found. Upload an audio file instead.");
      return;
    }
    const mime = TYPES.find((t) => MediaRecorder.isTypeSupported(t)) || "";
    try { mr.current = new MediaRecorder(stream.current, mime ? { mimeType: mime } : undefined); }
    catch { setErr("This browser cannot record audio. Upload a file instead."); stream.current.getTracks().forEach((t) => t.stop()); return; }
    chunks.current = [];
    mr.current.ondataavailable = (e) => { if (e.data && e.data.size) chunks.current.push(e.data); };
    mr.current.onstop = () => {
      clearInterval(timer.current);
      stream.current?.getTracks().forEach((t) => t.stop());
      const base = (mr.current.mimeType || mime || "audio/webm").split(";")[0];
      const blob = new Blob(chunks.current, { type: base });
      setRecording(false);
      if (!blob.size) { setErr("Nothing was recorded. Try again."); return; }
      onRecorded(new File([blob], `recording.${EXT[base] || "webm"}`, { type: base }));
    };
    mr.current.start();
    setSecs(0); setRecording(true);
    timer.current = setInterval(() => setSecs((s) => { if (s + 1 >= MAX_SECONDS) stop(); return s + 1; }), 1000);
  }
  function stop() { if (mr.current && mr.current.state !== "inactive") mr.current.stop(); }

  return (
    <div className="recorder">
      {!recording
        ? <button type="button" className="btn btn-secondary" onClick={start} disabled={disabled} data-testid="rec-start">● Record with microphone</button>
        : <button type="button" className="btn btn-danger" onClick={stop} data-testid="rec-stop">■ Stop ({secs}s / {MAX_SECONDS}s)</button>}
      {recording && <span className="muted small" role="status">Recording... speak clearly, then press Stop.</span>}
      {err && <p className="text-error small" role="alert">{err}</p>}
    </div>
  );
}
