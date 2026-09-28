"""Validate data/ against the Pydantic schemas and check referential integrity.

Run from the repo root:
    python scripts/validate_seed_data.py

Exits non-zero on any validation or referential-integrity error.
"""

import sys
from collections import Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.services.seed_loader import load_seed_data  # noqa: E402


def main() -> int:
    errors: list[str] = []
    seed = load_seed_data()

    org_ids = {o.id for o in seed.organizations}
    insurer_ids = {i.id for i in seed.insurers}
    procedure_ids = {p.id for p in seed.procedures}
    denial_reason_ids = {d.id for d in seed.denial_reasons}
    provider_ids = {p.id for p in seed.providers}
    patient_ids = {p.id for p in seed.patients}

    def check_refs(record_id, org_id, insurer_id, procedure_id, denial_reason_id, patient_id, provider_id):
        if org_id not in org_ids:
            errors.append(f"{record_id}: unknown org_id '{org_id}'")
        if insurer_id not in insurer_ids:
            errors.append(f"{record_id}: unknown insurer_id '{insurer_id}'")
        if procedure_id not in procedure_ids:
            errors.append(f"{record_id}: unknown procedure_id '{procedure_id}'")
        if denial_reason_id not in denial_reason_ids:
            errors.append(f"{record_id}: unknown denial_reason_id '{denial_reason_id}'")
        if patient_id not in patient_ids:
            errors.append(f"{record_id}: unknown patient_id '{patient_id}'")
        if provider_id not in provider_ids:
            errors.append(f"{record_id}: unknown provider_id '{provider_id}'")

    seen_case_ids: set[str] = set()
    for c in seed.historical_cases:
        if c.case_id in seen_case_ids:
            errors.append(f"duplicate case_id '{c.case_id}'")
        seen_case_ids.add(c.case_id)
        check_refs(c.case_id, c.org_id, c.insurer_id, c.procedure_id, c.denial_reason_id, c.patient_id, c.provider_id)

    seen_claim_ids: set[str] = set()
    for c in seed.incoming_claims:
        if c.claim_id in seen_claim_ids:
            errors.append(f"duplicate claim_id '{c.claim_id}'")
        seen_claim_ids.add(c.claim_id)
        check_refs(c.claim_id, c.org_id, c.insurer_id, c.procedure_id, c.denial_reason_id, c.patient_id, c.provider_id)
        if c.claim_id in seen_case_ids:
            errors.append(f"claim_id '{c.claim_id}' collides with a historical case_id")

    if errors:
        print(f"FAILED — {len(errors)} error(s):")
        for e in errors:
            print(f"  - {e}")
        return 1

    print("Seed data OK.")
    print(f"  organizations:     {len(seed.organizations)}")
    print(f"  insurers:          {len(seed.insurers)}")
    print(f"  procedures:        {len(seed.procedures)}")
    print(f"  denial reasons:    {len(seed.denial_reasons)}")
    print(f"  providers:         {len(seed.providers)}")
    print(f"  patients:          {len(seed.patients)}")
    print(f"  historical cases:  {len(seed.historical_cases)}")
    print(f"  incoming claims:   {len(seed.incoming_claims)}")

    print("\nHistorical cases by demo_tag:")
    for tag, count in sorted(Counter(c.demo_tag for c in seed.historical_cases).items()):
        print(f"  {tag:45s} {count}")

    print("\nHistorical cases by outcome:")
    for outcome, count in sorted(Counter(c.appeal_outcome for c in seed.historical_cases).items()):
        print(f"  {outcome:45s} {count}")

    print("\nHistorical cases by insurer:")
    insurer_names = {i.id: i.name for i in seed.insurers}
    for insurer_id, count in sorted(Counter(c.insurer_id for c in seed.historical_cases).items()):
        print(f"  {insurer_names[insurer_id]:45s} {count}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
