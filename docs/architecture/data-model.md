# Overturn data model

## Entities

| Entity | File | Purpose |
|---|---|---|
| `Organization` | `data/seed/organizations.json` | The healthcare org. Maps 1:1 to a Hindsight memory bank — memory is institutional, not per-user (see [hindsight-integration.md](hindsight-integration.md), once written). |
| `Insurer` | `data/seed/insurers.json` | Fictional payer names. Deliberately generic-sounding, not modeled on any real insurer. |
| `Procedure` | `data/seed/procedures.json` | CPT-coded procedures. |
| `DenialReason` | `data/seed/denial_reasons.json` | The denial category cited by the insurer. |
| `Provider` | `data/seed/providers.json` | Ordering physicians at the org. |
| `Patient` | `data/seed/patients.json` | Synthetic patients — invented names/DOBs, no real PHI. |
| `HistoricalCase` | `data/historical_cases/cases.json` | A **resolved** claim + appeal + outcome. This is what gets retained into Hindsight to build institutional memory. |
| `IncomingClaim` | `data/claims/incoming_claims.json` | An **unresolved** denial the agent processes live during the demo. |

Schemas: [`backend/app/models/schemas.py`](../../backend/app/models/schemas.py).

There is deliberately no `MemoryObservation` entity of our own — Hindsight's `recall()` already returns auto-consolidated `observation` results with `source_fact_ids` and scored `source_facts` (semantic/keyword/reranker/final). We surface that data directly in the UI's "why this recommendation" panel rather than re-implementing a confidence system, per the verified API in [hindsight-integration.md](hindsight-integration.md).

## Relationships

```
Organization 1──* HistoricalCase / IncomingClaim
Insurer      1──* HistoricalCase / IncomingClaim
Procedure    1──* HistoricalCase / IncomingClaim
DenialReason 1──* HistoricalCase / IncomingClaim
Patient      1──1 HistoricalCase / IncomingClaim
Provider     1──* HistoricalCase / IncomingClaim
```

`validate_seed_data.py` enforces referential integrity (every foreign id in a case/claim must exist in the seed reference data) and uniqueness of `case_id`/`claim_id`.

## Why the dataset is deliberately messy

Per the hackathon guidance ("don't make every case conveniently match... the system must demonstrate actual retrieval and reasoning") and the design spec's edge-case list, each historical case carries a `demo_tag` marking what it's meant to prove. This is metadata for our own evaluation/labeling — it is never sent to the LLM as ground truth, since that would make the "pattern discovery" fake.

| `demo_tag` | Count | What it demonstrates |
|---|---|---|
| `core-pattern-fail` | 4 | Meridian + Lumbar MRI + medical necessity, rejected for missing/insufficient conservative-treatment (PT) documentation. Establishes the pattern. |
| `core-pattern-success` | 3 | Same cluster, approved once PT documentation (+ specialist referral) is included. The pattern the agent should learn and recall. |
| `conflicting-evidence` | 1 | PT documentation present (matches the "winning" pattern) but the appeal still failed for an unrelated reason (missing neuro exam findings). Pattern is necessary but not sufficient — the agent must not overstate certainty. |
| `irrelevant-different-procedure` | 2 | Same insurer, different procedure/denial reason. Must be filtered out of lumbar-MRI reasoning, not treated as relevant history. |
| `different-insurer-same-surface-pattern` | 3 | Alliance Coastal, same procedure/denial reason as the Meridian cluster, but Alliance has its own additional requirement (imaging within 90 days) not present in Meridian's pattern. Tests that the agent doesn't blindly transfer one insurer's rule to another. |
| `administrative-not-clinical` | 2 | Denial is a policy classification or billing error, not a documentation gap — more clinical evidence would not have changed the outcome. Tests that the agent recognizes when the right move isn't "add more evidence." |
| `stale` | 1 | ~3 years old. Tests that the agent treats old precedent as weak/needing-verification rather than current guidance. |
| `single-precedent` | 1 | Only one historical case exists for this insurer. Tests that the agent flags low confidence instead of presenting one data point as an established pattern. |
| `over-generalization-trap` | 1 | Same insurer and denial reason as the core cluster, but a different body part (knee, not spine) where the generic PT language wasn't specific enough. Tests that the agent doesn't over-generalize "PT documentation" as a universal fix for this insurer. |

## The five live-demo claims

`data/claims/incoming_claims.json` — each `demo_scenario` field states which historical cases it should (and shouldn't) recall:

1. **CLM-101** — mirrors the core Meridian pattern with matching evidence already on hand → confident, specific recommendation.
2. **CLM-103** — Alliance Coastal, imaging is 4 months old → should recall the insurer-specific 90-day imaging requirement (HC-013), not just Meridian's PT-only rule.
3. **CLM-104** — Meridian knee MRI → should recall HC-018's caution (generic PT records weren't knee-specific) instead of the irrelevant lumbar cluster.
4. **CLM-105** — Summit Point, only HC-016 exists → recommend the strategy but flag it as single-precedent.
5. **CLM-106** — no relevant history at all → agent should say so plainly rather than force a recommendation, per the spec's required failure-mode language.

The before/after (with/without Hindsight) demo mode reuses **CLM-101** rather than a separate dataset entry — same claim, memory context toggled off vs. on.

## Verification

```bash
python -m venv .venv
.venv/Scripts/pip install -r backend/requirements.txt
.venv/Scripts/python scripts/validate_seed_data.py
```

Validates every JSON file against the Pydantic schemas, checks referential integrity, and prints summary counts (currently: 18 historical cases, 5 incoming claims, 7 approved / 11 rejected historical outcomes).
