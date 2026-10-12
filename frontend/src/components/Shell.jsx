import { API_BASE } from "../api";

const NAV = [
  ["dashboard", "Dashboard"], ["new", "New triage"], ["cases", "Cases"], ["queue", "Clinic queue"], ["about", "Safety & about"],
];

export default function Shell({ route, health, children }) {
  const { state, info, recheck } = health;
  const label = state === "online" ? "Backend connected" : state === "checking" ? "Checking backend..." : "Backend offline";
  return (
    <div className="app">
      <a className="skip" href="#main">Skip to content</a>
      <header className="topbar">
        <a className="brand" href="#/dashboard" aria-label="MedTriage AI home">
          <span className="logo" aria-hidden="true">+</span>
          <span>MedTriage <b>AI</b></span>
          <span className="proto">Prototype</span>
        </a>
        <nav aria-label="Main">
          {NAV.map(([k, t]) => (
            <a key={k} href={`#/${k}`} className={route === k ? "active" : ""} aria-current={route === k ? "page" : undefined}>{t}</a>
          ))}
        </nav>
        <button className={`status status-${state}`} onClick={recheck} title={`API: ${API_BASE} - click to re-check`}>
          <span className="dot" aria-hidden="true" />
          <span data-testid="backend-status">{label}</span>
          {state === "online" && info && (
            <span className="status-sub">AI {info.llm_configured ? "on" : "off"} - Voice {info.stt_configured ? "on" : "off"}</span>
          )}
        </button>
      </header>
      <div className="safety-bar" role="note">
        <strong>Prototype - not a diagnosis.</strong> Does not diagnose, prescribe or replace a clinician.
        <strong> Emergency? Call your local emergency number now (112 in India).</strong>
      </div>
      <main id="main" tabIndex={-1}>
        {state === "offline" && (
          <div className="alert alert-error" role="alert">
            <strong>Backend unreachable at {API_BASE}.</strong>
            <p>Run <code>start_backend.bat</code> (or <code>python -m uvicorn app.main:app --reload</code>), then click the status indicator. Pages that need data will stay empty until it is running.</p>
          </div>
        )}
        {children}
      </main>
      <footer className="footer">
        MedTriage AI - HackIndia AI &amp; CyberTech 2026 - Team Alpha 2.0 - Synthetic demonstration data only. Not clinically validated.
      </footer>
    </div>
  );
}
