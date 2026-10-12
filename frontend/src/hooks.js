import { useCallback, useEffect, useRef, useState } from "react";
import { getHealth } from "./api";

export function useHashRoute() {
  const read = () => (window.location.hash.replace(/^#\/?/, "") || "dashboard").split("/");
  const [parts, setParts] = useState(read);
  useEffect(() => {
    const on = () => setParts(read());
    window.addEventListener("hashchange", on);
    return () => window.removeEventListener("hashchange", on);
  }, []);
  return parts;
}

/** Polls /health. `state`: "checking" | "online" | "offline". */
export function useHealth(intervalMs = 15000) {
  const [state, setState] = useState("checking");
  const [info, setInfo] = useState(null);
  const check = useCallback(async () => {
    try { setInfo(await getHealth()); setState("online"); }
    catch { setInfo(null); setState("offline"); }
  }, []);
  useEffect(() => {
    check();
    const t = setInterval(check, intervalMs);
    return () => clearInterval(t);
  }, [check, intervalMs]);
  return { state, info, recheck: check };
}

/** Runs an async loader and tracks loading/error/data. Re-runs when `deps` change or `reload()` is called. */
export function useAsync(loader, deps = []) {
  const [s, setS] = useState({ loading: true, error: null, data: null });
  const seq = useRef(0);
  const run = useCallback(() => {
    const id = ++seq.current;
    setS((p) => ({ ...p, loading: true, error: null }));
    loader().then(
      (data) => { if (id === seq.current) setS({ loading: false, error: null, data }); },
      (error) => { if (id === seq.current) setS({ loading: false, error, data: null }); },
    );
  }, deps); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { run(); }, [run]);
  return { ...s, reload: run };
}
