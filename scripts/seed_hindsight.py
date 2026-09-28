"""Seed Hindsight: create the org's memory bank and retain all historical cases.

Requires a running Hindsight server reachable at HINDSIGHT_BASE_URL (local
`hindsight-api` / docker, or Hindsight Cloud), configured with its own LLM
key for fact extraction. See docs/architecture/hindsight-integration.md.

Run from the repo root:
    python scripts/seed_hindsight.py
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.memory.hindsight_client import OverturnMemory  # noqa: E402
from app.services.seed_loader import load_seed_data  # noqa: E402


def main() -> int:
    seed = load_seed_data()
    insurers = {i.id: i for i in seed.insurers}
    procedures = {p.id: p for p in seed.procedures}
    denial_reasons = {d.id: d for d in seed.denial_reasons}
    patients = {p.id: p for p in seed.patients}
    providers = {p.id: p for p in seed.providers}

    memory = OverturnMemory()

    for org in seed.organizations:
        print(f"Ensuring bank for {org.name} ({org.id})...")
        memory.ensure_org_bank(org.id, org.name)

    print(f"Retaining {len(seed.historical_cases)} historical cases...")
    for i, case in enumerate(seed.historical_cases, 1):
        memory.retain_historical_case(
            org_id=case.org_id,
            case=case,
            insurer=insurers[case.insurer_id],
            procedure=procedures[case.procedure_id],
            denial_reason=denial_reasons[case.denial_reason_id],
            patient=patients[case.patient_id],
            provider=providers[case.provider_id],
        )
        print(f"  [{i}/{len(seed.historical_cases)}] retained {case.case_id}")

    print("Done.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
