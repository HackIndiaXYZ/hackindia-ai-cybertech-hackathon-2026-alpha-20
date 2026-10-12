import { useEffect, useRef } from "react";
import { Card, Chips, UrgencyBadge } from "./Common";
import { describeMode, formatTime } from "../util";

export default function TriageResult({ result, actions }) {
  const r = result;
  const emergency = r.urgency === "emergency";
  const ref = useRef(null);
  useEffect(() => { ref.current?.scrollIntoView?.({ block: "start" }); }, [r.request_id]);
  return (
    <div className="result" data-testid="triage-result" ref={ref}>
      {emergency && (
        <div className="emergency-banner" role="alert">
          <strong>▲ POSSIBLE EMERGENCY - ACT NOW</strong>
          <p>{r.emergency_advice || "Seek emergency medical help immediately."}</p>
          {!r.emergency_advice && <p className="small">Do not wait for this tool or for a report. Call your local emergency number (112 in India).</p>}
        </div>
      )}
      <Card>
        <div className="result-head">
          <div>
            <p className="eyebrow">Preliminary urgency (rule-based)</p>
            <UrgencyBadge level={r.urgency} size="lg" />
          </div>
          <dl className="meta">
            <div><dt>Request ID</dt><dd className="mono" data-testid="request-id">{r.request_id}</dd></div>
            <div><dt>Created</dt><dd>{formatTime(r.created_at)}</dd></div>
            <div><dt>Input</dt><dd>{r.source === "audio" ? "Voice (transcribed)" : "Text"}</dd></div>
          </dl>
        </div>
        <h3>Why this level</h3>
        <p>{r.explanation}</p>
        {actions && <div className="actions">{actions}</div>}
      </Card>

      {r.transcript && (
        <Card title="Transcript">
          <p className="tag tag-warn">Machine transcript - may contain errors. Check it before relying on it.</p>
          <blockquote className="transcript" data-testid="transcript">{r.transcript}</blockquote>
          {r.transcription && (
            <p className="muted small">Status: {r.transcription.status} - {r.transcription.provider} / {r.transcription.model} - {r.transcription.characters} characters</p>
          )}
        </Card>
      )}

      <div className="grid-2">
        <Card title="Reported symptoms">
          <p className="tag">Detected by keyword rules in the reported text</p>
          <Chips items={r.reported_symptoms} empty="No symptoms covered by the demonstration rules were detected." />
        </Card>
        <Card title="Reported as absent">
          <p className="tag">Symptoms the person said they do not have</p>
          <Chips items={r.negated_symptoms} empty="None reported as absent." variant="chip-absent" />
        </Card>
      </div>

      <Card title="Summary">
        <p className={`tag ${r.summary_source === "ai" ? "tag-ai" : ""}`}>
          {r.summary_source === "ai" ? "AI-generated summary (untrusted, verify against the input)" : "Rule-based summary (no AI used)"}
        </p>
        <p data-testid="summary">{r.summary}</p>
      </Card>

      <Card title="Missing information and uncertainty">
        {r.uncertainties && r.uncertainties.length > 0
          ? <ul className="list">{r.uncertainties.map((u, i) => <li key={i}>{u}</li>)}</ul>
          : <p className="muted">None recorded.</p>}
      </Card>

      <Card title="How this was produced">
        <p>{describeMode(r)}</p>
        <p className="muted small">AI status: <span className="mono">{r.ai_status}</span> - AI used: {r.ai_used ? "yes" : "no"}. The AI can only raise urgency, never lower it.</p>
      </Card>

      <p className="disclaimer-inline">{r.disclaimer}</p>
    </div>
  );
}
