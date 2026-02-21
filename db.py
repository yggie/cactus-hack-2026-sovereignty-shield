"""SQLite database for cases, files, and findings."""

from __future__ import annotations

import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from models import (
    Case, CaseFile, CaseStatus, FileFormat, Finding,
    FindingCategory, RiskLevel, Severity,
)

DATA_DIR = Path(__file__).parent / "data"
DB_PATH = DATA_DIR / "analyst.db"
UPLOADS_DIR = DATA_DIR / "uploads"


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    UPLOADS_DIR.mkdir(exist_ok=True)


def _connect() -> sqlite3.Connection:
    _ensure_dirs()
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db() -> None:
    conn = _connect()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS cases (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            risk_level TEXT NOT NULL DEFAULT 'low',
            cloud_consent INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS case_files (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            filename TEXT NOT NULL,
            format TEXT NOT NULL,
            message_count INTEGER NOT NULL DEFAULT 0,
            preview TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS findings (
            id TEXT PRIMARY KEY,
            case_id TEXT NOT NULL REFERENCES cases(id) ON DELETE CASCADE,
            file_id TEXT NOT NULL REFERENCES case_files(id) ON DELETE CASCADE,
            category TEXT NOT NULL,
            severity TEXT NOT NULL,
            quote TEXT NOT NULL,
            explanation TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'local',
            chunk_index INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL
        );
    """)
    conn.close()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


# --- Cases ---

def create_case(name: str) -> Case:
    case_id = _new_id()
    now = _now_iso()
    conn = _connect()
    conn.execute(
        "INSERT INTO cases (id, name, status, risk_level, cloud_consent, created_at) VALUES (?, ?, ?, ?, ?, ?)",
        (case_id, name, CaseStatus.OPEN.value, RiskLevel.LOW.value, 0, now),
    )
    conn.commit()
    conn.close()
    return Case(id=case_id, name=name, created_at=datetime.fromisoformat(now))


def list_cases() -> list[Case]:
    conn = _connect()
    rows = conn.execute("SELECT * FROM cases ORDER BY created_at DESC").fetchall()
    conn.close()
    return [
        Case(
            id=r["id"], name=r["name"], status=CaseStatus(r["status"]),
            risk_level=RiskLevel(r["risk_level"]),
            cloud_consent=bool(r["cloud_consent"]),
            created_at=datetime.fromisoformat(r["created_at"]),
        )
        for r in rows
    ]


def get_case(case_id: str) -> Case | None:
    conn = _connect()
    r = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    if not r:
        conn.close()
        return None
    files = _list_files_conn(conn, case_id)
    findings = _list_findings_conn(conn, case_id)
    conn.close()
    return Case(
        id=r["id"], name=r["name"], status=CaseStatus(r["status"]),
        risk_level=RiskLevel(r["risk_level"]),
        cloud_consent=bool(r["cloud_consent"]),
        created_at=datetime.fromisoformat(r["created_at"]),
        files=files, findings=findings,
    )


def update_case(case_id: str, **kwargs: str | bool) -> Case | None:
    conn = _connect()
    for key, value in kwargs.items():
        if key == "cloud_consent":
            conn.execute(f"UPDATE cases SET {key} = ? WHERE id = ?", (int(value), case_id))
        else:
            conn.execute(f"UPDATE cases SET {key} = ? WHERE id = ?", (value, case_id))
    conn.commit()
    conn.close()
    return get_case(case_id)


def delete_case(case_id: str) -> bool:
    conn = _connect()
    cur = conn.execute("DELETE FROM cases WHERE id = ?", (case_id,))
    conn.commit()
    conn.close()
    return cur.rowcount > 0


# --- Files ---

def _list_files_conn(conn: sqlite3.Connection, case_id: str) -> list[CaseFile]:
    rows = conn.execute(
        "SELECT * FROM case_files WHERE case_id = ? ORDER BY created_at", (case_id,)
    ).fetchall()
    return [
        CaseFile(
            id=r["id"], case_id=r["case_id"], filename=r["filename"],
            format=FileFormat(r["format"]), message_count=r["message_count"],
            preview=r["preview"], created_at=datetime.fromisoformat(r["created_at"]),
        )
        for r in rows
    ]


def add_file(case_id: str, filename: str, fmt: FileFormat, message_count: int, preview: str) -> CaseFile:
    file_id = _new_id()
    now = _now_iso()
    conn = _connect()
    conn.execute(
        "INSERT INTO case_files (id, case_id, filename, format, message_count, preview, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (file_id, case_id, filename, fmt.value, message_count, preview, now),
    )
    conn.commit()
    conn.close()
    return CaseFile(
        id=file_id, case_id=case_id, filename=filename, format=fmt,
        message_count=message_count, preview=preview,
        created_at=datetime.fromisoformat(now),
    )


def get_file_path(file_id: str) -> Path:
    return UPLOADS_DIR / file_id


# --- Findings ---

def _list_findings_conn(conn: sqlite3.Connection, case_id: str) -> list[Finding]:
    rows = conn.execute(
        "SELECT * FROM findings WHERE case_id = ? ORDER BY created_at", (case_id,)
    ).fetchall()
    return [
        Finding(
            id=r["id"], case_id=r["case_id"], file_id=r["file_id"],
            category=FindingCategory(r["category"]), severity=Severity(r["severity"]),
            quote=r["quote"], explanation=r["explanation"], source=r["source"],
            chunk_index=r["chunk_index"],
            created_at=datetime.fromisoformat(r["created_at"]),
        )
        for r in rows
    ]


def list_findings(case_id: str) -> list[Finding]:
    conn = _connect()
    findings = _list_findings_conn(conn, case_id)
    conn.close()
    return findings


def add_finding(
    case_id: str, file_id: str, category: FindingCategory, severity: Severity,
    quote: str, explanation: str, source: str = "local", chunk_index: int = 0,
) -> Finding:
    finding_id = _new_id()
    now = _now_iso()
    conn = _connect()
    conn.execute(
        "INSERT INTO findings (id, case_id, file_id, category, severity, quote, explanation, source, chunk_index, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (finding_id, case_id, file_id, category.value, severity.value, quote, explanation, source, chunk_index, now),
    )
    conn.commit()
    conn.close()
    return Finding(
        id=finding_id, case_id=case_id, file_id=file_id, category=category,
        severity=severity, quote=quote, explanation=explanation, source=source,
        chunk_index=chunk_index, created_at=datetime.fromisoformat(now),
    )


def clear_findings(case_id: str) -> int:
    conn = _connect()
    cur = conn.execute("DELETE FROM findings WHERE case_id = ?", (case_id,))
    conn.commit()
    conn.close()
    return cur.rowcount


# Initialize on import
init_db()
