"""Thin, typed wrapper around the Hindsight client for Overturn.

One memory bank per healthcare organization — institutional memory, not
per-user. See docs/architecture/hindsight-integration.md for the design
rationale and the verified API this is built against.
"""

from datetime import datetime

from app.core.config import get_settings
from app.models.schemas import (
    DenialReason,
    HistoricalCase,
    Insurer,
    Patient,
    Procedure,
    Provider,
)

SAFETY_DIRECTIVE_NAME = "verify-before-asserting-policy"
SAFETY_DIRECTIVE_CONTENT = (
    "When discussing insurer denial patterns, never state or imply that a historical "
    "pattern is a guaranteed, current, or universal insurer policy. Always frame "
    "recommendations as an observation from a specific number of historical cases "
    "(e.g. 'N of M historical cases included X and succeeded') and explicitly tell the "
    "reader to verify against the insurer's current policy before relying on it. Do not "
    "treat a single historical case as an established pattern — say so explicitly if "
    "only one case is available."
)


class OverturnMemory:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        from hindsight_client import Hindsight  # imported lazily: optional dep

        settings = get_settings()
        self._client = Hindsight(
            base_url=base_url or settings.hindsight_base_url,
            api_key=api_key or settings.hindsight_api_key,
        )

    def __enter__(self) -> "OverturnMemory":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def ensure_org_bank(self, org_id: str, org_name: str) -> None:
        """Create (idempotently) and configure the org's memory bank.

        The SDK docs don't specify the exact exception raised when a bank or
        directive already exists, so failures here are logged and swallowed
        rather than assumed to be a specific error type.
        """
        try:
            self._client.create_bank(bank_id=org_id)
        except Exception as exc:
            print(f"  create_bank({org_id}): {exc} (continuing — bank may already exist)")

        self._client.update_bank_config(
            org_id,
            retain_mission=(
                f"Focus on facts about insurance claim denials and appeals at {org_name}: "
                "insurer, procedure, denial reason, evidence submitted, evidence missing, "
                "appeal strategy used, and outcome. Ignore unrelated conversational chatter."
            ),
            reflect_mission=(
                f"You are an appeal-strategy assistant for the revenue-cycle team at {org_name}. "
                "You help staff recall relevant institutional history about insurer denial "
                "patterns and draft evidence-aware appeal strategies. You never claim certainty "
                "about an insurer's current policy from historical patterns alone."
            ),
            disposition_skepticism=4,
            disposition_literalism=3,
            disposition_empathy=2,
        )

        try:
            self._client.create_directive(
                bank_id=org_id,
                name=SAFETY_DIRECTIVE_NAME,
                content=SAFETY_DIRECTIVE_CONTENT,
            )
        except Exception as exc:
            print(f"  create_directive({org_id}): {exc} (continuing — directive may already exist)")

    def retain_historical_case(
        self,
        org_id: str,
        case: HistoricalCase,
        insurer: Insurer,
        procedure: Procedure,
        denial_reason: DenialReason,
        patient: Patient,
        provider: Provider,
    ) -> None:
        content = (
            f"Historical appeal case {case.case_id}: {insurer.name} denied a "
            f"{procedure.name} claim for patient {patient.name} (ordering provider "
            f"{provider.name}) citing '{denial_reason.name}' on {case.denial_date.isoformat()}. "
            f"Evidence submitted: {', '.join(case.evidence_submitted) or 'none'}. "
            f"Evidence missing: {', '.join(case.evidence_missing) or 'none'}. "
            f"Appeal strategy used: {case.appeal_strategy_used} "
            f"Outcome: appeal was {case.appeal_outcome} on {case.outcome_date.isoformat()}. "
            f"{case.notes}"
        )
        self._client.retain(
            bank_id=org_id,
            content=content,
            context=(
                f"insurer={insurer.name}; procedure={procedure.name}; "
                f"denial_reason={denial_reason.name}; outcome={case.appeal_outcome}"
            ),
            timestamp=datetime.combine(case.denial_date, datetime.min.time()),
            document_id=case.case_id,
            metadata={
                "case_id": case.case_id,
                "insurer_id": case.insurer_id,
                "procedure_id": case.procedure_id,
                "denial_reason_id": case.denial_reason_id,
                "outcome": case.appeal_outcome,
                "demo_tag": case.demo_tag,
            },
        )

    def retain_outcome(self, org_id: str, content: str, *, document_id: str, metadata: dict) -> None:
        """Retain a newly resolved outcome — the 'retain again' step that
        closes the experience -> memory -> recall -> adaptation -> outcome ->
        learning loop for a live claim processed during the demo."""
        self._client.retain(bank_id=org_id, content=content, document_id=document_id, metadata=metadata)

    def recall(self, org_id: str, query: str, **kwargs):
        return self._client.recall(bank_id=org_id, query=query, **kwargs)

    def reflect(self, org_id: str, query: str, **kwargs):
        return self._client.reflect(bank_id=org_id, query=query, **kwargs)
