import { useState } from "react";
import { createPatient, friendlyError, listPatients, updatePatient } from "../api";
import { Card, Empty, ErrorBox, Spinner, UrgencyBadge } from "../components/Common";
import { useAsync } from "../hooks";
import { AGE_GROUPS, STATUS_LABEL, URGENCY_ORDER, formatTime } from "../util";

function Row({ p, onChanged }) {
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState(null);
  async function setStatus(status) {
    setBusy(true); setErr(null);
    try { await updatePatient(p.id, { status }); onChanged(); } catch (e) { setErr(friendlyError(e)); } finally { setBusy(false); }
  }
  return (
    <tr>
      <td className="mono">{p.id}</td>
      <td><UrgencyBadge level={p.urgency} size="sm" /></td>
      <td>{p.display_name}</td>
      <td>{p.chief_complaint}{p.triage_request_id && <> - <a href={`#/cases/${p.triage_request_id}`}>case</a></>}</td>
      <td>{formatTime(p.arrived_at)}</td>
      <td>
        <label className="sr-only" htmlFor={`st-${p.id}`}>Status for {p.id}</label>
        <select id={`st-${p.id}`} value={p.status} disabled={busy} onChange={(e) => setStatus(e.target.value)}>
          {Object.entries(STATUS_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
        </select>
        {err && <p className="text-error small" role="alert">{err}</p>}
      </td>
    </tr>
  );
}

function AddForm({ onAdded }) {
  const [f, setF] = useState({ display_name: "", age_group: "unspecified", chief_complaint: "", urgency: "undetermined" });
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  async function submit(e) {
    e.preventDefault();
    if (!f.display_name.trim() || f.chief_complaint.trim().length < 3) { setMsg({ ok: false, text: "Enter a pseudonym and a chief complaint (3+ characters)." }); return; }
    setBusy(true); setMsg(null);
    try {
      const p = await createPatient({ ...f, display_name: f.display_name.trim(), chief_complaint: f.chief_complaint.trim() });
      setMsg({ ok: true, text: `Added ${p.id}.` }); setF({ ...f, display_name: "", chief_complaint: "" }); onAdded();
    } catch (err) { setMsg({ ok: false, text: friendlyError(err) }); } finally { setBusy(false); }
  }
  return (
    <Card title="Add a synthetic queue entry">
      <p className="muted small">Pseudonyms only. Urgency set here is manual; for an assessed urgency, add from a case instead.</p>
      <form onSubmit={submit} noValidate className="form-grid">
        <div className="field"><label htmlFor="n-name">Pseudonym</label><input id="n-name" value={f.display_name} maxLength={60} onChange={set("display_name")} placeholder="e.g. Demo Patient G" /></div>
        <div className="field"><label htmlFor="n-age">Age group</label><select id="n-age" value={f.age_group} onChange={set("age_group")}>{AGE_GROUPS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></div>
        <div className="field wide"><label htmlFor="n-comp">Chief complaint</label><input id="n-comp" value={f.chief_complaint} maxLength={300} onChange={set("chief_complaint")} /></div>
        <div className="field"><label htmlFor="n-urg">Urgency</label><select id="n-urg" value={f.urgency} onChange={set("urgency")}>{URGENCY_ORDER.map((u) => <option key={u} value={u}>{u}</option>)}</select></div>
        <div className="field"><button className="btn btn-secondary" disabled={busy} type="submit">{busy ? "Adding..." : "Add to queue"}</button></div>
      </form>
      {msg && <p role="status" className={msg.ok ? "text-ok" : "text-error"}>{msg.text}</p>}
    </Card>
  );
}

export default function Queue() {
  const [status, setStatus] = useState("");
  const q = useAsync(() => listPatients(status || undefined), [status]);
  const rows = q.data?.patients || [];
  return (
    <>
      <h1>Clinic queue</h1>
      <p className="lead">Most urgent first, then earliest arrival. Records are synthetic demonstration data stored in SQLite.</p>
      <Card title="Queue" actions={
        <span className="field inline"><label htmlFor="flt">Show</label>
          <select id="flt" value={status} onChange={(e) => setStatus(e.target.value)}>
            <option value="">All</option>{Object.entries(STATUS_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </select></span>}>
        {q.loading && <Spinner />}
        <ErrorBox error={q.error} onRetry={q.reload} />
        {q.data && (rows.length === 0 ? <Empty title="No entries match">Add one below.</Empty> : (
          <div className="table-wrap">
            <table data-testid="queue-table">
              <caption className="sr-only">Clinic queue</caption>
              <thead><tr><th>ID</th><th>Urgency</th><th>Pseudonym</th><th>Chief complaint</th><th>Arrived</th><th>Status</th></tr></thead>
              <tbody>{rows.map((p) => <Row key={p.id} p={p} onChanged={q.reload} />)}</tbody>
            </table>
          </div>
        ))}
      </Card>
      <AddForm onAdded={q.reload} />
    </>
  );
}
