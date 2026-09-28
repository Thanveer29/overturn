"""Ad-hoc diagnostic: recall() + reflect() against a live Hindsight bank for
one incoming claim. Useful both to verify the integration and, later, as the
basis for the agent's own memory-retrieval step.

Run from the repo root:
    python scripts/query_memory.py CLM-101
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.memory.hindsight_client import OverturnMemory  # noqa: E402
from app.services.seed_loader import load_seed_data  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: python scripts/query_memory.py <claim_id>")
        return 1
    claim_id = sys.argv[1]

    seed = load_seed_data()
    insurers = {i.id: i for i in seed.insurers}
    procedures = {p.id: p for p in seed.procedures}
    denial_reasons = {d.id: d for d in seed.denial_reasons}

    claim = next((c for c in seed.incoming_claims if c.claim_id == claim_id), None)
    if claim is None:
        print(f"No incoming claim with id '{claim_id}'")
        return 1

    insurer = insurers[claim.insurer_id]
    procedure = procedures[claim.procedure_id]
    denial_reason = denial_reasons[claim.denial_reason_id]

    query = (
        f"Appeal strategy for a {procedure.name} claim denied by {insurer.name} "
        f"citing '{denial_reason.name}'. What historical cases are relevant, and "
        f"what evidence should the appeal include?"
    )
    print(f"Claim: {claim.claim_id} — {claim.demo_scenario}\n")
    print(f"Query: {query}\n")

    with OverturnMemory() as memory:
        print("=" * 20, "recall()", "=" * 20)
        recall_result = memory.recall(org_id=claim.org_id, query=query)
        results = getattr(recall_result, "results", recall_result)
        for r in results:
            rtype = getattr(r, "type", "?")
            text = getattr(r, "text", str(r))
            print(f"[{rtype}] {text}\n")

        print("=" * 20, "reflect()", "=" * 20)
        reflect_result = memory.reflect(org_id=claim.org_id, query=query)
        print(getattr(reflect_result, "text", reflect_result))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
