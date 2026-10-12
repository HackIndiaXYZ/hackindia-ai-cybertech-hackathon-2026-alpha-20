import { useEffect, useMemo, useRef, useState } from "react";
import { friendlyError, postAudio, postText } from "../api";
import { Card, ErrorBox, Spinner } from "../components/Common";
import PdfButton from "../components/PdfButton";
import Recorder, { recordingSupported } from "../components/Recorder";
import TriageResult from "../components/TriageResult";
import { AGE_GROUPS, EXAMPLES } from "../util";

function ResultActions({ r }) {
  return (<><PdfButton requestId={r.request_id} /><a className="btn btn-secondary" href={`#/cases/${r.request_id}`}>Open full case</a></>);
}

function TextIntake({ health }) {
  const max = health?.max_text_chars || 2000;
  const [text, setText] = useState("");
  const [age, setAge] = useState("unspecified");
  const [duration, setDuration] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [fieldErr, setFieldErr] = useState(null);

  async function submit(e) {
    e.preventDefault();
    const clean = text.trim();
    if (clean.replace(/[\W_]+/g, "").length < 3) { setFieldErr("Please describe the symptoms in a few words (at least 3 letters)."); return; }
    if (clean.length > max) { setFieldErr(`Please keep the description under ${max} characters.`); return; }
    setFieldErr(null); setError(null); setBusy(true); setResult(null);
    try {
      const context = { age_group: age };
      if (duration.trim()) context.duration = duration.trim();
      setResult(await postText({ symptom_description: clean, context }));
    } catch (err) { setError(err); } finally { setBusy(false); }
  }

  return (
    <>
      <Card title="Describe the symptoms">
        <form onSubmit={submit} noValidate>
          <div className="field">
            <label htmlFor="symptoms">Symptom description</label>
            <textarea id="symptoms" rows={5} value={text} onChange={(e) => setText(e.target.value)} maxLength={max + 200}
              aria-describedby="symptoms-help symptoms-err" aria-invalid={!!fieldErr} placeholder="e.g. Synthetic example: cough and mild fever for 2 days" />
            <div className="field-row">
              <span id="symptoms-help" className="muted small">Do not enter names, phone numbers or other identifying details.</span>
              <span className={`small ${text.length > max ? "text-error" : "muted"}`}>{text.length}/{max}</span>
            </div>
            {fieldErr && <p id="symptoms-err" className="text-error small" role="alert">{fieldErr}</p>}
          </div>
          <div className="form-grid">
            <div className="field">
              <label htmlFor="age">Age group (optional)</label>
              <select id="age" value={age} onChange={(e) => setAge(e.target.value)}>
                {AGE_GROUPS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
            <div className="field">
              <label htmlFor="dur">Duration (optional)</label>
              <input id="dur" value={duration} maxLength={100} onChange={(e) => setDuration(e.target.value)} placeholder="e.g. 2 days" />
            </div>
          </div>
          <div className="examples">
            <span className="muted small">Synthetic examples:</span>
            {EXAMPLES.map((ex, i) => <button type="button" key={i} className="btn btn-link" onClick={() => setText(ex)}>Example {i + 1}</button>)}
          </div>
          <button className="btn btn-primary" type="submit" disabled={busy} data-testid="submit-text">{busy ? "Analysing..." : "Get triage support"}</button>
        </form>
      </Card>
      {busy && <Spinner label="Analysing the report (rules first, then AI if configured)..." />}
      <ErrorBox error={error} />
      {result && <TriageResult result={result} actions={<ResultActions r={result} />} />}
    </>
  );
}

function VoiceIntake({ health }) {
  const maxMb = health?.max_audio_mb ?? 15;
  const formats = health?.allowed_audio_formats || ["flac", "m4a", "mp3", "mp4", "mpeg", "mpga", "ogg", "wav", "webm"];
  const [file, setFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState(null);
  const [age, setAge] = useState("unspecified");
  const [phase, setPhase] = useState("idle"); // idle | uploading | processing
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState(null);
  const [fieldErr, setFieldErr] = useState(null);
  const [result, setResult] = useState(null);
  const job = useRef(null);
  const busy = phase !== "idle";

  useEffect(() => { if (!file) { setPreviewUrl(null); return; } const u = URL.createObjectURL(file); setPreviewUrl(u); return () => URL.revokeObjectURL(u); }, [file]);
  useEffect(() => () => job.current?.abort(), []);

  function choose(f) {
    setResult(null); setError(null); setFieldErr(null);
    if (!f) { setFile(null); return; }
    const ext = (f.name.split(".").pop() || "").toLowerCase();
    if (!formats.includes(ext)) { setFile(null); setFieldErr(`Unsupported file type ".${ext}". Accepted: ${formats.join(", ")}.`); return; }
    if (f.size > maxMb * 1024 * 1024) { setFile(null); setFieldErr(`File is ${(f.size / 1048576).toFixed(1)} MB; the limit is ${maxMb} MB.`); return; }
    if (f.size === 0) { setFile(null); setFieldErr("The selected file is empty."); return; }
    setFile(f);
  }

  async function submit(e) {
    e.preventDefault();
    if (!file) { setFieldErr("Choose or record an audio file first."); return; }
    setError(null); setResult(null); setProgress(0); setPhase("uploading");
    job.current = postAudio(file, age, { onProgress: setProgress, onUploaded: () => setPhase("processing") });
    try { setResult(await job.current.promise); } catch (err) { setError(err); } finally { setPhase("idle"); job.current = null; }
  }

  return (
    <>
      <Card title="Voice symptom report">
        <form onSubmit={submit} noValidate>
          <div className="field">
            <label htmlFor="audio">Audio file</label>
            <input id="audio" type="file" accept={formats.map((f) => "." + f).join(",") + ",audio/*"} disabled={busy}
              onChange={(e) => choose(e.target.files?.[0])} aria-describedby="audio-help audio-err" data-testid="audio-input" />
            <p id="audio-help" className="muted small">Accepted: {formats.join(", ")} - up to {maxMb} MB. Use a short fictional recording.</p>
            {fieldErr && <p id="audio-err" className="text-error small" role="alert">{fieldErr}</p>}
          </div>
          {recordingSupported() && <Recorder disabled={busy} onRecorded={(f) => choose(f)} />}
          {file && (
            <div className="preview">
              <p className="small"><strong>Selected:</strong> <span data-testid="file-name">{file.name}</span> ({(file.size / 1024).toFixed(0)} KB)</p>
              <audio controls src={previewUrl} aria-label="Preview of the selected audio" />
            </div>
          )}
          <div className="field narrow">
            <label htmlFor="age2">Age group (optional)</label>
            <select id="age2" value={age} onChange={(e) => setAge(e.target.value)} disabled={busy}>
              {AGE_GROUPS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </select>
          </div>
          <button className="btn btn-primary" type="submit" disabled={busy || !file} data-testid="submit-audio">
            {phase === "uploading" ? "Uploading..." : phase === "processing" ? "Transcribing and analysing..." : "Transcribe and triage"}
          </button>
          {health && !health.stt_configured && (
            <p className="alert alert-warn small">Speech-to-text is not configured on the backend, so voice triage will return an error. Add GROQ_API_KEY to the backend .env and restart.</p>
          )}
        </form>
      </Card>
      {phase === "uploading" && (
        <div role="status"><label htmlFor="up">Uploading {Math.round(progress * 100)}%</label><progress id="up" value={progress} max="1" /></div>
      )}
      {phase === "processing" && <Spinner label="Transcribing speech, then analysing the transcript..." />}
      <ErrorBox error={error} title="Voice triage failed" />
      {result && <TriageResult result={result} actions={<ResultActions r={result} />} />}
    </>
  );
}

export default function NewCase({ health }) {
  const [tab, setTab] = useState("text");
  const tabs = useMemo(() => [["text", "Text"], ["voice", "Voice"]], []);
  return (
    <>
      <h1>New triage</h1>
      <p className="lead">Enter symptoms by text or voice. Use fictional demonstration data only.</p>
      <div className="tabs" role="tablist" aria-label="Input method">
        {tabs.map(([k, t]) => (
          <button key={k} role="tab" id={`tab-${k}`} aria-selected={tab === k} aria-controls={`panel-${k}`} className={tab === k ? "tab active" : "tab"} onClick={() => setTab(k)}>{t}</button>
        ))}
      </div>
      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`}>
        {tab === "text" ? <TextIntake health={health} /> : <VoiceIntake health={health} />}
      </div>
    </>
  );
}
