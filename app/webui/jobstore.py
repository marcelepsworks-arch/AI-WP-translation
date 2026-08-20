"""Durable replacement for the dashboard's in-memory job dictionary.

Jobs were held in a module-level dict, so restarting the dashboard erased
every record of what had been run. That is tolerable for a progress
spinner and not tolerable for "what did I translate yesterday, and can I
still undo it" -- an undo button is only as trustworthy as the history
behind it.

SQLite rather than a JSON file because jobs update themselves from
background threads while the request thread reads them; a single file
rewritten from several threads loses writes. The job payload is stored as
one JSON blob per row: the fields differ per action and per outcome, and
inventing a column for each would be churn with no benefit.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    seq INTEGER
);
"""


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobStore:
    def __init__(self, path: Path | str) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        # check_same_thread=False plus an explicit lock: job threads write
        # their own row while the HTTP thread reads it.
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._lock = threading.Lock()
        with self._lock:
            self._conn.executescript(_SCHEMA)
            columns = {row["name"] for row in self._conn.execute("PRAGMA table_info(jobs)")}
            if "payload" not in columns:
                self._conn.execute("ALTER TABLE jobs ADD COLUMN payload TEXT NOT NULL DEFAULT '{}'")
            self._conn.commit()

    def create(self, job_id: str, data: dict) -> None:
        now = _now()
        with self._lock:
            self._conn.execute(
                "INSERT OR REPLACE INTO jobs (job_id, created_at, updated_at, seq, payload)"
                " VALUES (?, ?, ?, (SELECT COALESCE(MAX(seq), 0) + 1 FROM jobs), ?)",
                (job_id, now, now, json.dumps(data, ensure_ascii=False)),
            )
            self._conn.commit()

    def update(self, job_id: str, **fields) -> None:
        """Merges `fields` into the stored payload. Unknown job ids are
        ignored rather than raising: a job whose row is gone is not a reason
        to crash the thread that was reporting on it.
        """
        with self._lock:
            row = self._conn.execute("SELECT payload FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            if row is None:
                return
            payload = json.loads(row["payload"])
            payload.update(fields)
            self._conn.execute(
                "UPDATE jobs SET payload = ?, updated_at = ? WHERE job_id = ?",
                (json.dumps(payload, ensure_ascii=False), _now(), job_id),
            )
            self._conn.commit()

    def get(self, job_id: str) -> dict | None:
        with self._lock:
            row = self._conn.execute("SELECT payload FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
        return json.loads(row["payload"]) if row else None

    def list_recent(self, limit: int = 50) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT job_id, created_at, updated_at, payload FROM jobs ORDER BY seq DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [
            {
                "job_id": row["job_id"],
                "created_at": row["created_at"],
                "updated_at": row["updated_at"],
                **json.loads(row["payload"]),
            }
            for row in rows
        ]
