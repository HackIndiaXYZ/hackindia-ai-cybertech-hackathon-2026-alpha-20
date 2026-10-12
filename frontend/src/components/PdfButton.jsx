import { useState } from "react";
import { downloadReport, friendlyError } from "../api";

export default function PdfButton({ requestId }) {
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState(null);
  async function go() {
    setBusy(true); setMsg(null);
    try {
      const r = await downloadReport(requestId);
      setMsg({ ok: true, text: `Downloaded ${r.filename} (${Math.max(1, Math.round(r.bytes / 1024))} KB).` });
    } catch (e) { setMsg({ ok: false, text: friendlyError(e) }); }
    finally { setBusy(false); }
  }
  return (
    <span className="inline-action">
      <button className="btn btn-primary" onClick={go} disabled={busy} data-testid="pdf-btn">
        {busy ? "Preparing PDF..." : "Download PDF report"}
      </button>
      <span role="status" className={msg && !msg.ok ? "text-error" : "muted small"}>{msg ? msg.text : ""}</span>
    </span>
  );
}
