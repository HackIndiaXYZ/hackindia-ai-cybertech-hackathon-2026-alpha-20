"""SQLite persistence for triage results and the synthetic patient queue.

Uses the standard-library sqlite3 module. A new connection is opened per call so
it is safe under FastAPI's threadpool. Data is stored in a local file
(DATABASE_PATH) and therefore DOES persist between restarts. Demo use only.
"""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Iterator, List, Optional

SCHEMA = """
CREATE TABLE IF NOT EXISTS triage_results (
    request_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    payload    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS patients (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    display_name    TEXT NOT NULL,
    age_group       TEXT NOT NULL DEFAULT 'unspecified',
    chief_complaint TEXT NOT NULL,
    urgency         TEXT NOT NULL DEFAULT 'undetermined',
    status          TEXT NOT NULL DEFAULT 'waiting',
    triage_request_id TEXT,
    arrived_at      TEXT NOT NULL,
    updated_at      TEXT NOT NULL
);
"""

# SYNTHETIC records only. Names are obvious placeholders, not real people.
SEED_PATIENTS = [
    ("Demo Patient A", "adult", "Chest tightness since this morning", "emergency", "in_assessment"),
    ("Demo Patient B", "child", "Fever and cough for two days", "routine", "waiting"),
    ("Demo Patient C", "older_adult", "Severe stomach pain since last night", "urgent", "waiting"),
    ("Demo Patient D", "adult", "Mild sore throat and runny nose", "routine", "waiting"),
    ("Demo Patient E", "adult", "Dizziness after standing up", "routine", "seen"),
]

URGENCY_ORDER_SQL = ("CASE urgency WHEN 'emergency' THEN 3 WHEN 'urgent' THEN 2 "
                     "WHEN 'routine' THEN 1 ELSE 0 END")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def format_patient_id(row_id: int) -> str:
    return f"P-{row_id:04d}"


def parse_patient_id(patient_id: str) -> Optional[int]:
    if isinstance(patient_id, str) and patient_id.startswith("P-") and patient_id[2:].isdigit():
        return int(patient_id[2:])
    return None


class Database:
    def __init__(self, path: str):
        self.path = path

    @contextmanager
    def _conn(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    def init(self, seed: bool = True) -> None:
        with self._conn() as c:
            c.executescript(SCHEMA)
            if seed and c.execute("SELECT COUNT(*) FROM patients").fetchone()[0] == 0:
                ts = now_iso()
                for name, age, complaint, urg, status in SEED_PATIENTS:
                    c.execute(
                        "INSERT INTO patients (display_name, age_group, chief_complaint, urgency, status, arrived_at, updated_at)"
                        " VALUES (?,?,?,?,?,?,?)", (name, age, complaint, urg, status, ts, ts))

    # ---- triage results ----
    def save_triage(self, record: Dict[str, Any]) -> None:
        with self._conn() as c:
            c.execute("INSERT INTO triage_results (request_id, created_at, payload) VALUES (?,?,?)",
                      (record["request_id"], record["created_at"], json.dumps(record, ensure_ascii=False)))

    def get_triage(self, request_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as c:
            row = c.execute("SELECT payload FROM triage_results WHERE request_id = ?", (request_id,)).fetchone()
        return json.loads(row["payload"]) if row else None

    def list_triage(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Most recent triage results, newest first. Returns a privacy-minimal summary (no input text)."""
        with self._conn() as c:
            rows = c.execute("SELECT payload FROM triage_results ORDER BY created_at DESC, rowid DESC LIMIT ?",
                             (int(limit),)).fetchall()
        keys = ("request_id", "created_at", "source", "urgency", "reported_symptoms", "summary_source", "mode", "ai_used")
        out = []
        for r in rows:
            rec = json.loads(r["payload"])
            out.append({k: rec.get(k) for k in keys})
        return out

    def count_triage(self) -> int:
        with self._conn() as c:
            return c.execute("SELECT COUNT(*) FROM triage_results").fetchone()[0]

    # ---- patients ----
    @staticmethod
    def _patient(row: sqlite3.Row) -> Dict[str, Any]:
        d = dict(row)
        d["id"] = format_patient_id(d["id"])
        return d

    def list_patients(self, status: Optional[str] = None, urgency: Optional[str] = None) -> List[Dict[str, Any]]:
        sql, args = "SELECT * FROM patients WHERE 1=1", []
        if status:
            sql += " AND status = ?"; args.append(status)
        if urgency:
            sql += " AND urgency = ?"; args.append(urgency)
        sql += f" ORDER BY {URGENCY_ORDER_SQL} DESC, arrived_at ASC, id ASC"
        with self._conn() as c:
            return [self._patient(r) for r in c.execute(sql, args).fetchall()]

    def get_patient(self, patient_id: str) -> Optional[Dict[str, Any]]:
        rid = parse_patient_id(patient_id)
        if rid is None:
            return None
        with self._conn() as c:
            row = c.execute("SELECT * FROM patients WHERE id = ?", (rid,)).fetchone()
        return self._patient(row) if row else None

    def create_patient(self, display_name: str, age_group: str, chief_complaint: str,
                       urgency: str = "undetermined", triage_request_id: Optional[str] = None) -> Dict[str, Any]:
        ts = now_iso()
        with self._conn() as c:
            cur = c.execute(
                "INSERT INTO patients (display_name, age_group, chief_complaint, urgency, status, triage_request_id, arrived_at, updated_at)"
                " VALUES (?,?,?,?,?,?,?,?)",
                (display_name, age_group, chief_complaint, urgency, "waiting", triage_request_id, ts, ts))
            rid = cur.lastrowid
            row = c.execute("SELECT * FROM patients WHERE id = ?", (rid,)).fetchone()
        return self._patient(row)

    def update_patient(self, patient_id: str, changes: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        rid = parse_patient_id(patient_id)
        allowed = {"status", "urgency", "chief_complaint", "age_group", "display_name"}
        changes = {k: v for k, v in changes.items() if k in allowed and v is not None}
        if rid is None:
            return None
        with self._conn() as c:
            if not c.execute("SELECT 1 FROM patients WHERE id = ?", (rid,)).fetchone():
                return None
            if changes:
                sets = ", ".join(f"{k} = ?" for k in changes)
                c.execute(f"UPDATE patients SET {sets}, updated_at = ? WHERE id = ?",
                          (*changes.values(), now_iso(), rid))
            row = c.execute("SELECT * FROM patients WHERE id = ?", (rid,)).fetchone()
        return self._patient(row)
