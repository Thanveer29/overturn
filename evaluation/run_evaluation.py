"""Live evaluation harness.

Runs all 5 incoming claims through both analysis modes against the REAL
backend (Groq completions + Hindsight Cloud recall/reflect) and scores the
results against expectations hand-derived from the dataset design (see
docs/architecture/data-model.md's case matrix). This calls real, billed
APIs -- it is not the mocked/offline contract-test suite (see
backend/tests/test_api_claims.py for that).

Per the hackathon's own rule against fabricating results, EXPECTED_KEY_CASES
below records only what we already confirmed live during manual testing
(Phase 4/5 sessions) for CLM-101/104/106; CLM-103/105 are run here for the
first time in scored form, not assumed.

Run from the repo root:
    python evaluation/run_evaluation.py
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.agents.orchestrator import analyze_with_memory, analyze_without_memory  # noqa: E402
from app.services.citations import extract_case_ids  # noqa: E402
from app.services.claims_repo import get_claim_context  # noqa: E402
from app.services.seed_loader import load_seed_data  # noqa: E402

# The one historical case each claim's demo_scenario (data/claims/incoming_claims.json)
# says is the key relevant precedent. A "pass" means at least one of these was cited
# in the with-memory recommendation -- not that every case matched, since reflect()
# is free to cite additional supporting cases too (as seen live for CLM-104, which
# also cited HC-001/002/003/006/007/008/015 alongside the key case HC-018).
EXPECTED_KEY_CASES = {
    "CLM-101": {"HC-003", "HC-005", "HC-007"},
    "CLM-103": {"HC-013"},
    "CLM-104": {"HC-018"},
    "CLM-105": {"HC-016"},
    "CLM-106": {"HC-009"},
}

UNCERTAINTY_KEYWORDS = [
    "verify",
    "single",
    "one historical case",
    "does not represent",
    "not universal",
    "not guarantee",
    "limited",
]


def _case_id_to_patient_name() -> dict[str, str]:
    seed = load_seed_data()
    patients = {p.id: p.name for p in seed.patients}
    return {c.case_id: patients[c.patient_id] for c in seed.historical_cases}


def score_claim(claim_id: str, case_patient_names: dict[str, str]) -> dict:
    ctx = get_claim_context(claim_id)
    if ctx is None:
        raise ValueError(f"Unknown claim_id '{claim_id}'")

    without = analyze_without_memory(ctx)
    with_mem = analyze_with_memory(ctx)

    without_cited = extract_case_ids(without.strategy_text)
    with_cited = extract_case_ids(with_mem.strategy_text)

    expected = EXPECTED_KEY_CASES.get(claim_id, set())
    strict_hit = bool(with_cited & expected) if expected else None

    # reflect() sometimes refers to a case by the patient's name instead of its
    # "HC-###" id (both appear in the retained fact text) -- caught live on
    # CLM-105, where it cited "Yuki Tanaka" rather than "HC-016" and the
    # strict id-only check produced a false negative. This loose check is a
    # second signal, not a replacement -- both are reported so the gap
    # between "cited by id" and "actually used the right case" stays visible.
    strategy_lower = with_mem.strategy_text.lower()
    loose_hit = (
        strict_hit
        or any(case_patient_names.get(c, "\0").lower() in strategy_lower for c in expected)
        if expected
        else None
    )

    lowered = strategy_lower
    flags_uncertainty = any(kw in lowered for kw in UNCERTAINTY_KEYWORDS)

    return {
        "claim_id": claim_id,
        "without_memory_cited_cases": sorted(without_cited),
        "with_memory_cited_cases": sorted(with_cited),
        "expected_key_cases": sorted(expected),
        "recalled_key_case_strict_id_match": strict_hit,
        "recalled_key_case_incl_patient_name_match": loose_hit,
        "memory_adds_citations": len(with_cited) > len(without_cited),
        "flags_uncertainty_or_verification": flags_uncertainty,
        "recalled_memory_count": len(with_mem.recalled_memories),
    }


def main() -> int:
    case_patient_names = _case_id_to_patient_name()
    claim_ids = list(EXPECTED_KEY_CASES)
    results = []
    for claim_id in claim_ids:
        print(f"Scoring {claim_id}...")
        results.append(score_claim(claim_id, case_patient_names))

    out_path = REPO_ROOT / "evaluation" / "results.json"
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "note": "Prototype evaluation on synthetic dataset. Not a real-world performance claim.",
        "results": results,
    }
    out_path.write_text(json.dumps(payload, indent=2))

    print()
    print(
        f"{'claim':10s}  {'strict id match':>15s}  {'incl. name match':>17s}  "
        f"{'adds citations':>15s}  {'uncertainty':>11s}  memories"
    )
    for r in results:
        print(
            f"{r['claim_id']:10s}  {str(r['recalled_key_case_strict_id_match']):>15s}  "
            f"{str(r['recalled_key_case_incl_patient_name_match']):>17s}  "
            f"{str(r['memory_adds_citations']):>15s}  {str(r['flags_uncertainty_or_verification']):>11s}  "
            f"{r['recalled_memory_count']}"
        )

    n = len(results)
    strict_pass = sum(1 for r in results if r["recalled_key_case_strict_id_match"])
    loose_pass = sum(1 for r in results if r["recalled_key_case_incl_patient_name_match"])
    adds_citations_pass = sum(1 for r in results if r["memory_adds_citations"])
    print(f"\nKey case recalled (strict 'HC-###' citation only): {strict_pass}/{n}")
    print(f"Key case recalled (including reference by patient name): {loose_pass}/{n}")
    print(f"Memory adds citations vs. no-memory baseline: {adds_citations_pass}/{n}")
    print(f"\nFull results written to {out_path.relative_to(REPO_ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
