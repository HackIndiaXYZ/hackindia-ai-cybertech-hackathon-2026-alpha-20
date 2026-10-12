import { friendlyError } from "../api";
import { URGENCY } from "../util";

export function UrgencyBadge({ level, size = "md" }) {
  const u = URGENCY[level] || URGENCY.undetermined;
  return (
    <span className={`badge ${u.cls} badge-${size}`} title={u.hint}>
      <span aria-hidden="true">{u.glyph}</span> {u.label}
    </span>
  );
}

export function Spinner({ label = "Loading..." }) {
  return <div className="loading" role="status"><span className="spinner" aria-hidden="true" /> {label}</div>;
}

export function ErrorBox({ error, onRetry, title = "Something went wrong" }) {
  if (!error) return null;
  return (
    <div className="alert alert-error" role="alert">
      <strong>{title}</strong>
      <p>{typeof error === "string" ? error : friendlyError(error)}</p>
      {onRetry && <button className="btn btn-secondary btn-sm" onClick={onRetry}>Try again</button>}
    </div>
  );
}

export function Empty({ title, children }) {
  return (
    <div className="empty">
      <p className="empty-title">{title}</p>
      {children && <div className="empty-body">{children}</div>}
    </div>
  );
}

export function Card({ title, children, actions, className = "" }) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <header className="card-head">
          {title && <h2>{title}</h2>}
          {actions}
        </header>
      )}
      {children}
    </section>
  );
}

export function Chips({ items, empty, variant = "" }) {
  if (!items || items.length === 0) return <p className="muted">{empty}</p>;
  return <ul className="chips">{items.map((t, i) => <li key={i} className={`chip ${variant}`}>{t}</li>)}</ul>;
}
