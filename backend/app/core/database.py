"""Minimal SQLite access — plain sqlite3, no ORM.

The dataset is small (a few dozen rows) and read-mostly, so an ORM would be
pure overhead here; see the "don't over-engineer" guidance in the design doc.
"""

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path

from app.core.config import REPO_ROOT, get_settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS organizations (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, type TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS insurers (
    id TEXT PRIMARY KEY, name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS procedures (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, cpt_code TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS denial_reasons (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, description TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS providers (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, specialty TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS patients (
    id TEXT PRIMARY KEY, name TEXT NOT NULL, date_of_birth TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS historical_cases (
    case_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL REFERENCES organizations(id),
    insurer_id TEXT NOT NULL REFERENCES insurers(id),
    procedure_id TEXT NOT NULL REFERENCES procedures(id),
    denial_reason_id TEXT NOT NULL REFERENCES denial_reasons(id),
    patient_id TEXT NOT NULL REFERENCES patients(id),
    provider_id TEXT NOT NULL REFERENCES providers(id),
    denial_date TEXT NOT NULL,
    evidence_submitted TEXT NOT NULL,
    evidence_missing TEXT NOT NULL,
    appeal_strategy_used TEXT NOT NULL,
    appeal_outcome TEXT NOT NULL,
    outcome_date TEXT NOT NULL,
    notes TEXT NOT NULL,
    demo_tag TEXT NOT NULL,
    retained_in_hindsight INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS incoming_claims (
    claim_id TEXT PRIMARY KEY,
    org_id TEXT NOT NULL REFERENCES organizations(id),
    insurer_id TEXT NOT NULL REFERENCES insurers(id),
    procedure_id TEXT NOT NULL REFERENCES procedures(id),
    denial_reason_id TEXT NOT NULL REFERENCES denial_reasons(id),
    patient_id TEXT NOT NULL REFERENCES patients(id),
    provider_id TEXT NOT NULL REFERENCES providers(id),
    denial_date TEXT NOT NULL,
    evidence_available TEXT NOT NULL,
    status TEXT NOT NULL,
    demo_scenario TEXT NOT NULL
);
"""


def _db_path() -> Path:
    url = get_settings().database_url
    if not url.startswith("sqlite:///"):
        raise ValueError(f"Only sqlite:/// URLs are supported, got: {url}")
    relative = url.removeprefix("sqlite:///")
    return (REPO_ROOT / relative).resolve()


@contextmanager
def get_connection():
    path = _db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db(conn: sqlite3.Connection) -> None:
    conn.executescript(SCHEMA)


def dumps(value: list[str]) -> str:
    return json.dumps(value)


def loads(value: str) -> list[str]:
    return json.loads(value)
