"""Read (and the one write we need) access to the SQLite-loaded dataset.

Kept as plain functions over app.core.database's sqlite3 connection —
see the "don't over-engineer" note in database.py for why there's no ORM.
"""

from dataclasses import dataclass

from app.core.database import get_connection, loads
from app.models.schemas import (
    DenialReason,
    IncomingClaim,
    Insurer,
    Organization,
    Patient,
    Procedure,
    Provider,
)


@dataclass
class ClaimContext:
    claim: IncomingClaim
    org: Organization
    insurer: Insurer
    procedure: Procedure
    denial_reason: DenialReason
    patient: Patient
    provider: Provider


def _row_to_claim(row) -> IncomingClaim:
    return IncomingClaim.model_validate(
        {
            **dict(row),
            "evidence_available": loads(row["evidence_available"]),
        }
    )


def list_incoming_claims() -> list[IncomingClaim]:
    with get_connection() as conn:
        rows = conn.execute("SELECT * FROM incoming_claims ORDER BY denial_date").fetchall()
        return [_row_to_claim(r) for r in rows]


def get_claim_context(claim_id: str) -> ClaimContext | None:
    with get_connection() as conn:
        claim_row = conn.execute(
            "SELECT * FROM incoming_claims WHERE claim_id = ?", (claim_id,)
        ).fetchone()
        if claim_row is None:
            return None
        claim = _row_to_claim(claim_row)

        org = Organization.model_validate(
            dict(conn.execute("SELECT * FROM organizations WHERE id = ?", (claim.org_id,)).fetchone())
        )
        insurer = Insurer.model_validate(
            dict(conn.execute("SELECT * FROM insurers WHERE id = ?", (claim.insurer_id,)).fetchone())
        )
        procedure = Procedure.model_validate(
            dict(conn.execute("SELECT * FROM procedures WHERE id = ?", (claim.procedure_id,)).fetchone())
        )
        denial_reason = DenialReason.model_validate(
            dict(
                conn.execute(
                    "SELECT * FROM denial_reasons WHERE id = ?", (claim.denial_reason_id,)
                ).fetchone()
            )
        )
        patient = Patient.model_validate(
            dict(conn.execute("SELECT * FROM patients WHERE id = ?", (claim.patient_id,)).fetchone())
        )
        provider = Provider.model_validate(
            dict(conn.execute("SELECT * FROM providers WHERE id = ?", (claim.provider_id,)).fetchone())
        )

    return ClaimContext(
        claim=claim, org=org, insurer=insurer, procedure=procedure,
        denial_reason=denial_reason, patient=patient, provider=provider,
    )


def update_claim_status(claim_id: str, status: str) -> None:
    with get_connection() as conn:
        conn.execute(
            "UPDATE incoming_claims SET status = ? WHERE claim_id = ?", (status, claim_id)
        )
