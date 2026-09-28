import os
import sys
from pathlib import Path

import pytest

BACKEND_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture(scope="session", autouse=True)
def _test_database(tmp_path_factory):
    """Point the app at a throwaway SQLite file, loaded from the same
    data/*.json used everywhere else, so tests never touch the dev database
    and never need live Groq/Hindsight credentials."""
    db_path = tmp_path_factory.mktemp("db") / "test_overturn.db"
    os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
    os.environ.setdefault("GROQ_API_KEY", "test-key-not-used")
    os.environ.setdefault("HINDSIGHT_API_KEY", "test-key-not-used")

    from app.core.config import get_settings

    get_settings.cache_clear()

    from app.core.database import dumps, get_connection, init_db
    from app.services.seed_loader import load_seed_data

    seed = load_seed_data()
    with get_connection() as conn:
        init_db(conn)
        conn.executemany(
            "INSERT OR REPLACE INTO organizations VALUES (?, ?, ?)",
            [(o.id, o.name, o.type) for o in seed.organizations],
        )
        conn.executemany(
            "INSERT OR REPLACE INTO insurers VALUES (?, ?)", [(i.id, i.name) for i in seed.insurers]
        )
        conn.executemany(
            "INSERT OR REPLACE INTO procedures VALUES (?, ?, ?)",
            [(p.id, p.name, p.cpt_code) for p in seed.procedures],
        )
        conn.executemany(
            "INSERT OR REPLACE INTO denial_reasons VALUES (?, ?, ?)",
            [(d.id, d.name, d.description) for d in seed.denial_reasons],
        )
        conn.executemany(
            "INSERT OR REPLACE INTO providers VALUES (?, ?, ?)",
            [(p.id, p.name, p.specialty) for p in seed.providers],
        )
        conn.executemany(
            "INSERT OR REPLACE INTO patients VALUES (?, ?, ?)",
            [(p.id, p.name, p.date_of_birth.isoformat()) for p in seed.patients],
        )
        conn.executemany(
            """INSERT OR REPLACE INTO historical_cases
               (case_id, org_id, insurer_id, procedure_id, denial_reason_id, patient_id,
                provider_id, denial_date, evidence_submitted, evidence_missing,
                appeal_strategy_used, appeal_outcome, outcome_date, notes, demo_tag,
                retained_in_hindsight)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
            [
                (
                    c.case_id, c.org_id, c.insurer_id, c.procedure_id, c.denial_reason_id,
                    c.patient_id, c.provider_id, c.denial_date.isoformat(),
                    dumps(c.evidence_submitted), dumps(c.evidence_missing),
                    c.appeal_strategy_used, c.appeal_outcome, c.outcome_date.isoformat(), c.notes, c.demo_tag,
                )
                for c in seed.historical_cases
            ],
        )
        conn.executemany(
            """INSERT OR REPLACE INTO incoming_claims
               (claim_id, org_id, insurer_id, procedure_id, denial_reason_id, patient_id,
                provider_id, denial_date, evidence_available, status, demo_scenario)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                (
                    c.claim_id, c.org_id, c.insurer_id, c.procedure_id, c.denial_reason_id,
                    c.patient_id, c.provider_id, c.denial_date.isoformat(),
                    dumps(c.evidence_available), c.status, c.demo_scenario,
                )
                for c in seed.incoming_claims
            ],
        )

    yield
