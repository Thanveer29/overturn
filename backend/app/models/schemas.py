"""Pydantic schemas for Overturn's domain entities.

These mirror the JSON seed/historical-case/claim data under data/. They are
the single source of truth for shape validation before anything gets loaded
into SQLite or retained into Hindsight.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel


class Organization(BaseModel):
    id: str
    name: str
    type: str


class Insurer(BaseModel):
    id: str
    name: str


class Procedure(BaseModel):
    id: str
    name: str
    cpt_code: str


class DenialReason(BaseModel):
    id: str
    name: str
    description: str


class Provider(BaseModel):
    id: str
    name: str
    specialty: str


class Patient(BaseModel):
    id: str
    name: str
    date_of_birth: date


AppealOutcome = Literal["approved", "rejected"]

# What story beat / edge case (Phase 12 / Phase 33 of the design doc) a
# historical case exists to demonstrate. Used by evaluation + the UI to
# label memory provenance, not sent to the LLM as ground truth.
DemoTag = Literal[
    "core-pattern-fail",
    "core-pattern-success",
    "irrelevant-different-procedure",
    "different-insurer-same-surface-pattern",
    "stale",
    "single-precedent",
    "administrative-not-clinical",
    "over-generalization-trap",
    "conflicting-evidence",
]


class HistoricalCase(BaseModel):
    """A fully resolved claim + appeal + outcome. Seeded into Hindsight as
    retained facts so the agent has institutional memory to recall from."""

    case_id: str
    org_id: str
    insurer_id: str
    procedure_id: str
    denial_reason_id: str
    patient_id: str
    provider_id: str
    denial_date: date
    evidence_submitted: list[str]
    evidence_missing: list[str]
    appeal_strategy_used: str
    appeal_outcome: AppealOutcome
    outcome_date: date
    notes: str
    demo_tag: DemoTag


class IncomingClaim(BaseModel):
    """A live, unresolved denial the agent processes during the demo."""

    claim_id: str
    org_id: str
    insurer_id: str
    procedure_id: str
    denial_reason_id: str
    patient_id: str
    provider_id: str
    denial_date: date
    evidence_available: list[str]
    status: Literal["pending_appeal", "resolved_approved", "resolved_rejected"]
    demo_scenario: str
