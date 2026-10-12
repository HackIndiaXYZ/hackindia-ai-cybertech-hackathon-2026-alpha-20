import { listPatients, listTriage } from "../api";
import { Card, Empty, ErrorBox, Spinner, UrgencyBadge } from "../components/Common";
import { useAsync } from "../hooks";
import { STATUS_LABEL, URGENCY_ORDER, formatTime } from "../util";

function Stat({ label, value, sub, testid }) {
  return <div className="stat"><p className="stat-value" data-testid={testid}>{value}</p><p className="stat-label">{label}</p>{sub && <p className="muted small">{sub}</p>}</div>;
}

export default function Dashboard() {
  const triage = useAsync(() => listTriage(100), []);
  const queue = useAsync(() => listPatients(), []);
  const items = triage.data?.items || [];
  const patients = queue.data?.patients || [];
  const byUrg = (arr) => Object.fromEntries(URGENCY_ORDER.map((u) => [u, arr.filter((x) => x.urgency === u).length]));
  const cu = byUrg(items), qu = byUrg(patients);

  return (
    <>
      <h1>Clinic dashboard</h1>
      <p className="lead">Live numbers from the backend database. Nothing on this page is hardcoded.</p>

      <Card title="Triage requests" actions={<a className="btn btn-primary btn-sm" href="#/new">New triage</a>}>
        {triage.loading && <Spinner />}
        <ErrorBox error={triage.error} onRetry={triage.reload} />
        {triage.data && (items.length === 0 ? (
          <Empty title="No triage requests yet">Submit a fictional case from <a href="#/new">New triage</a> and it will appear here.</Empty>
        ) : (
          <>
            <div className="stats">
              <Stat label="Total stored requests" value={triage.data.total} testid="stat-total" />
              {URGENCY_ORDER.map((u) => <Stat key={u} label={<UrgencyBadge level={u} size="sm" />} value={cu[u]} sub={`in latest ${items.length}`} testid={`stat-case-${u}`} />)}
            </div>
            <div className="table-wrap">
              <table>
                <caption className="sr-only">Most recent triage requests</caption>
                <thead><tr><th>Time</th><th>Urgency</th><th>Reported symptoms</th><th>Input</th><th><span className="sr-only">Open</span></th></tr></thead>
                <tbody>
                  {items.slice(0, 5).map((c) => (
                    <tr key={c.request_id}>
                      <td>{formatTime(c.created_at)}</td>
                      <td><UrgencyBadge level={c.urgency} size="sm" /></td>
                      <td>{c.reported_symptoms.length ? c.reported_symptoms.join(", ") : <span className="muted">none detected</span>}</td>
                      <td>{c.source === "audio" ? "Voice" : "Text"}</td>
                      <td><a href={`#/cases/${c.request_id}`}>Open</a></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {items.length > 5 && <p><a href="#/cases">View all cases</a></p>}
          </>
        ))}
      </Card>

      <Card title="Clinic queue" actions={<a className="btn btn-secondary btn-sm" href="#/queue">Manage queue</a>}>
        {queue.loading && <Spinner />}
        <ErrorBox error={queue.error} onRetry={queue.reload} />
        {queue.data && (patients.length === 0 ? (
          <Empty title="The queue is empty">Add an entry from <a href="#/queue">Clinic queue</a> or from a case.</Empty>
        ) : (
          <>
            <p className="tag">{queue.data.synthetic_data_notice}</p>
            <div className="stats">
              <Stat label="In queue" value={queue.data.count} testid="stat-queue" />
              {URGENCY_ORDER.map((u) => <Stat key={u} label={<UrgencyBadge level={u} size="sm" />} value={qu[u]} testid={`stat-queue-${u}`} />)}
            </div>
            <ul className="list">
              {patients.filter((p) => p.status !== "seen").slice(0, 4).map((p) => (
                <li key={p.id}><UrgencyBadge level={p.urgency} size="sm" /> <strong>{p.display_name}</strong> - {p.chief_complaint} <span className="muted">({STATUS_LABEL[p.status]})</span></li>
              ))}
            </ul>
          </>
        ))}
      </Card>
    </>
  );
}
