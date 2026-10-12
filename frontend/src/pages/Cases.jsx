import { useState } from "react";
import { createPatient, friendlyError, getTriage, listTriage } from "../api";
import { Card, Empty, ErrorBox, Spinner, UrgencyBadge } from "../components/Common";
import PdfButton from "../components/PdfButton";
import TriageResult from "../components/TriageResult";
import { useAsync } from "../hooks";
import { AGE_GROUPS, formatTime } from "../util";

function AddToQueue({ r }) {
  const [name, setName] = useState("");
  const [age, setAge] = useState("unspecified");
  const [complaint, setComplaint] = useState((r.reported_symptoms[0] ? `Reported: ${r.reported_symptoms.join(", ")}` : "Symptoms under review").slice(0, 300));
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  async function submit(e) {
    e.preventDefault();
    if (!name.trim()) { setMsg({ ok: false, text: "Enter a pseudonym (not a real name)." }); return; }
    setBusy(true); setMsg(null);
    try {
      const p = await createPatient({ display_name: name.trim(), age_group: age, chief_complaint: complaint.trim(), triage_request_id: r.request_id });
      setMsg({ ok: true, text: `Added to the queue as ${p.id} with urgency ${p.urgency.toUpperCase()}.` });
    } catch (err) { setMsg({ ok: false, text: friendlyError(err) }); } finally { setBusy(false); }
  }
  return (
    <Card title="Add to clinic queue">
      <p className="muted small">Uses this case's urgency. Use a pseudonym only - never a real name.</p>
      <form onSubmit={submit} noValidate className="form-grid">
        <div className="field"><label htmlFor="q-name">Pseudonym</label><input id="q-name" value={name} maxLength={60} onChange={(e) => setName(e.target.value)} placeholder="e.g. Demo Patient F" /></div>
        <div className="field"><label htmlFor="q-age">Age group</label><select id="q-age" value={age} onChange={(e) => setAge(e.target.value)}>{AGE_GROUPS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></div>
        <div className="field wide"><label htmlFor="q-comp">Chief complaint</label><input id="q-comp" value={complaint} maxLength={300} onChange={(e) => setComplaint(e.target.value)} /></div>
        <div className="field wide"><button className="btn btn-secondary" disabled={busy} type="submit">{busy ? "Adding..." : "Add to queue"}</button></div>
      </form>
      {msg && <p role="status" className={msg.ok ? "text-ok" : "text-error"}>{msg.text} {msg.ok && <a href="#/queue">Open queue</a>}</p>}
    </Card>
  );
}

function CaseDetail({ id }) {
  const q = useAsync(() => getTriage(id), [id]);
  return (
    <>
      <p><a href="#/cases">&larr; All cases</a></p>
      <h1>Case details</h1>
      {q.loading && <Spinner />}
      <ErrorBox error={q.error} onRetry={q.reload} title="Case could not be loaded" />
      {q.data && (
        <>
          <TriageResult result={q.data} actions={<PdfButton requestId={q.data.request_id} />} />
          <AddToQueue r={q.data} />
        </>
      )}
    </>
  );
}

export default function Cases({ id }) {
  const q = useAsync(() => (id ? Promise.resolve(null) : listTriage(100)), [id]);
  if (id) return <CaseDetail id={id} />;
  const items = q.data?.items || [];
  return (
    <>
      <h1>Cases</h1>
      <p className="lead">Every stored triage request, newest first. Original text is not shown in this list.</p>
      {q.loading && <Spinner />}
      <ErrorBox error={q.error} onRetry={q.reload} />
      {q.data && (items.length === 0
        ? <Empty title="No cases yet">Run a fictional triage from <a href="#/new">New triage</a>.</Empty>
        : (
          <Card>
            <div className="table-wrap">
              <table data-testid="cases-table">
                <caption className="sr-only">Stored triage requests</caption>
                <thead><tr><th>Time</th><th>Urgency</th><th>Reported symptoms</th><th>Input</th><th>Summary by</th><th><span className="sr-only">Open</span></th></tr></thead>
                <tbody>
                  {items.map((c) => (
                    <tr key={c.request_id}>
                      <td>{formatTime(c.created_at)}</td>
                      <td><UrgencyBadge level={c.urgency} size="sm" /></td>
                      <td>{c.reported_symptoms.length ? c.reported_symptoms.join(", ") : <span className="muted">none detected</span>}</td>
                      <td>{c.source === "audio" ? "Voice" : "Text"}</td>
                      <td>{c.summary_source === "ai" ? "AI" : "Rules"}</td>
                      <td><a href={`#/cases/${c.request_id}`}>Open</a></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="muted small">Showing {q.data.count} of {q.data.total} stored requests.</p>
          </Card>
        ))}
    </>
  );
}
