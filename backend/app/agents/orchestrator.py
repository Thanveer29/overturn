"""The core agent pipeline: Denial Analyzer -> Memory Retriever -> Evidence
Analyzer -> Appeal Strategist -> Draft Generator, collapsed into a small
number of real steps rather than eight agents kept separate for appearance.

Two steps call an LLM (Groq) directly:
  - analyze_without_memory(): the before/after demo's "before" side --
    deliberately has no Hindsight context, so the contrast is real, not
    staged (see docs/architecture/before-after-demo.md).
  - draft_appeal(): letter generation -- a distinct task (tone/formatting)
    from strategy reasoning.

The "with memory" strategy step delegates to Hindsight's own reflect(),
which already does recall + evidence-aware reasoning under the bank's
directives (live-verified in docs/architecture/hindsight-integration.md).
Re-deriving that with a second, separate LLM call would be redundant and
less honest about where the intelligence is actually coming from.
"""

from dataclasses import dataclass, field

from app.memory.hindsight_client import OverturnMemory
from app.services.claims_repo import ClaimContext
from app.services.llm import LLMError, chat_completion


class HindsightUnavailableError(Exception):
    """Raised when a live Hindsight call fails, so the API can degrade
    gracefully (Phase 22: every external dependency should fail gracefully)
    instead of the request crashing."""


def _claim_summary(ctx: ClaimContext) -> str:
    evidence = ", ".join(ctx.claim.evidence_available) or "none on file"
    return (
        f"{ctx.procedure.name} claim for patient {ctx.patient.name} (ordering provider "
        f"{ctx.provider.name}) was denied by {ctx.insurer.name}, citing '{ctx.denial_reason.name}' "
        f"on {ctx.claim.denial_date.isoformat()}. Evidence currently available: {evidence}."
    )


def _memory_query(ctx: ClaimContext) -> str:
    return (
        f"{_claim_summary(ctx)} Based on institutional history, what appeal strategy should be "
        "used? Explicitly state whether the currently available evidence appears sufficient "
        "given historical patterns for this insurer and procedure, and what (if anything) is "
        "missing."
    )


@dataclass
class RecalledMemory:
    type: str
    text: str


@dataclass
class StrategyResult:
    mode: str  # "with_memory" | "without_memory"
    strategy_text: str
    recalled_memories: list[RecalledMemory] = field(default_factory=list)


def analyze_without_memory(ctx: ClaimContext) -> StrategyResult:
    """The demo's 'before' side: no institutional memory at all."""
    system = (
        "You are an appeal-strategy assistant for a healthcare revenue-cycle team. "
        "You have no access to this organization's appeal history. Reason only from "
        "general medical-billing knowledge."
    )
    user = f"{_claim_summary(ctx)} Recommend an appeal strategy for this denial."
    try:
        text = chat_completion(system, user)
    except LLMError as exc:
        text = f"(LLM analysis unavailable: {exc})"
    return StrategyResult(mode="without_memory", strategy_text=text)


def analyze_with_memory(ctx: ClaimContext) -> StrategyResult:
    """The demo's 'after' side: recall() for the raw evidence trail, reflect()
    for the actual evidence-aware, directive-constrained recommendation."""
    query = _memory_query(ctx)
    try:
        with OverturnMemory() as memory:
            recall_response = memory.recall(org_id=ctx.org.id, query=query)
            reflect_response = memory.reflect(org_id=ctx.org.id, query=query)
    except Exception as exc:  # Hindsight's SDK doesn't document a typed error hierarchy
        raise HindsightUnavailableError(f"Hindsight call failed: {exc}") from exc

    recalled = [
        RecalledMemory(type=getattr(r, "type", "?"), text=getattr(r, "text", str(r)))
        for r in getattr(recall_response, "results", [])
    ]
    strategy_text = getattr(reflect_response, "text", str(reflect_response))
    return StrategyResult(mode="with_memory", strategy_text=strategy_text, recalled_memories=recalled)


def draft_appeal(ctx: ClaimContext, strategy_text: str) -> str:
    """Turn a strategy recommendation into an actual appeal-letter draft.
    A distinct task from strategy reasoning: formatting and tone, not memory."""
    system = (
        "You draft formal insurance-appeal letters for a healthcare organization's "
        "revenue-cycle team. Write in a professional, factual tone. Do not invent "
        "clinical facts not given to you. This draft will be reviewed by a human "
        "before submission -- flag anything the reviewer should double check."
    )
    user = (
        f"{_claim_summary(ctx)}\n\n"
        f"Recommended appeal strategy:\n{strategy_text}\n\n"
        f"Write the appeal letter, addressed to {ctx.insurer.name}, referencing the "
        f"denied {ctx.procedure.name} claim for patient {ctx.patient.name}."
    )
    try:
        return chat_completion(system, user, max_completion_tokens=1500)
    except LLMError as exc:
        return f"(Draft generation unavailable: {exc})"


def record_outcome(ctx: ClaimContext, outcome: str, notes: str) -> None:
    """Close the loop: retain what actually happened so future recalls see it.
    This is the 'retain again' step of experience -> memory -> recall ->
    adaptation -> outcome -> learning."""
    content = (
        f"Live appeal outcome for {ctx.claim.claim_id}: {ctx.procedure.name} claim for "
        f"{ctx.patient.name}, denied by {ctx.insurer.name} citing '{ctx.denial_reason.name}', "
        f"was {outcome}. {notes}"
    )
    try:
        with OverturnMemory() as memory:
            memory.retain_outcome(
                org_id=ctx.org.id,
                content=content,
                document_id=ctx.claim.claim_id,
                metadata={
                    "claim_id": ctx.claim.claim_id,
                    "insurer_id": ctx.insurer.id,
                    "procedure_id": ctx.procedure.id,
                    "denial_reason_id": ctx.denial_reason.id,
                    "outcome": outcome,
                },
            )
    except Exception as exc:
        raise HindsightUnavailableError(f"Hindsight retain failed: {exc}") from exc
