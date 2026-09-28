from typing import Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents.orchestrator import (
    HindsightUnavailableError,
    analyze_with_memory,
    analyze_without_memory,
    draft_appeal,
    record_outcome,
)
from app.services import claims_repo

router = APIRouter(prefix="/api/claims", tags=["claims"])


class ClaimSummary(BaseModel):
    claim_id: str
    insurer_name: str
    procedure_name: str
    denial_reason_name: str
    patient_name: str
    denial_date: str
    status: str


class ClaimDetail(ClaimSummary):
    provider_name: str
    evidence_available: list[str]
    demo_scenario: str


def _to_summary(ctx: claims_repo.ClaimContext) -> ClaimSummary:
    return ClaimSummary(
        claim_id=ctx.claim.claim_id,
        insurer_name=ctx.insurer.name,
        procedure_name=ctx.procedure.name,
        denial_reason_name=ctx.denial_reason.name,
        patient_name=ctx.patient.name,
        denial_date=ctx.claim.denial_date.isoformat(),
        status=ctx.claim.status,
    )


def _get_context_or_404(claim_id: str) -> claims_repo.ClaimContext:
    ctx = claims_repo.get_claim_context(claim_id)
    if ctx is None:
        raise HTTPException(status_code=404, detail=f"Unknown claim_id '{claim_id}'")
    return ctx


@router.get("", response_model=list[ClaimSummary])
def list_claims():
    contexts = [claims_repo.get_claim_context(c.claim_id) for c in claims_repo.list_incoming_claims()]
    return [_to_summary(ctx) for ctx in contexts if ctx is not None]


@router.get("/{claim_id}", response_model=ClaimDetail)
def get_claim(claim_id: str):
    ctx = _get_context_or_404(claim_id)
    return ClaimDetail(
        **_to_summary(ctx).model_dump(),
        provider_name=ctx.provider.name,
        evidence_available=ctx.claim.evidence_available,
        demo_scenario=ctx.claim.demo_scenario,
    )


class RecalledMemoryOut(BaseModel):
    type: str
    text: str


class AnalyzeRequest(BaseModel):
    mode: Literal["with_memory", "without_memory"]


class AnalyzeResponse(BaseModel):
    mode: str
    strategy_text: str
    recalled_memories: list[RecalledMemoryOut]


@router.post("/{claim_id}/analyze", response_model=AnalyzeResponse)
def analyze_claim(claim_id: str, body: AnalyzeRequest):
    ctx = _get_context_or_404(claim_id)
    try:
        if body.mode == "with_memory":
            result = analyze_with_memory(ctx)
        else:
            result = analyze_without_memory(ctx)
    except HindsightUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return AnalyzeResponse(
        mode=result.mode,
        strategy_text=result.strategy_text,
        recalled_memories=[RecalledMemoryOut(type=m.type, text=m.text) for m in result.recalled_memories],
    )


class DraftRequest(BaseModel):
    strategy_text: str


class DraftResponse(BaseModel):
    draft: str


@router.post("/{claim_id}/draft", response_model=DraftResponse)
def draft(claim_id: str, body: DraftRequest):
    ctx = _get_context_or_404(claim_id)
    return DraftResponse(draft=draft_appeal(ctx, body.strategy_text))


class OutcomeRequest(BaseModel):
    outcome: Literal["approved", "rejected"]
    notes: str = ""


class OutcomeResponse(BaseModel):
    status: str


@router.post("/{claim_id}/outcome", response_model=OutcomeResponse)
def outcome(claim_id: str, body: OutcomeRequest):
    ctx = _get_context_or_404(claim_id)
    try:
        record_outcome(ctx, body.outcome, body.notes)
    except HindsightUnavailableError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    claims_repo.update_claim_status(claim_id, f"resolved_{body.outcome}")
    return OutcomeResponse(status="recorded")
