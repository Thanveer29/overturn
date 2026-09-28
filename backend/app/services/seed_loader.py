"""Shared loader: data/*.json -> validated Pydantic models.

Used by the seed-data validator, the SQLite loader, and the Hindsight
seeding script so there is exactly one place that knows the on-disk layout.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from app.core.config import REPO_ROOT
from app.models.schemas import (
    DenialReason,
    HistoricalCase,
    IncomingClaim,
    Insurer,
    Organization,
    Patient,
    Procedure,
    Provider,
)

DATA_DIR = REPO_ROOT / "data"


def _load_json(path: Path) -> list[dict]:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


@dataclass
class SeedData:
    organizations: list[Organization]
    insurers: list[Insurer]
    procedures: list[Procedure]
    denial_reasons: list[DenialReason]
    providers: list[Provider]
    patients: list[Patient]
    historical_cases: list[HistoricalCase]
    incoming_claims: list[IncomingClaim]


def load_seed_data() -> SeedData:
    seed_dir = DATA_DIR / "seed"
    return SeedData(
        organizations=[Organization.model_validate(r) for r in _load_json(seed_dir / "organizations.json")],
        insurers=[Insurer.model_validate(r) for r in _load_json(seed_dir / "insurers.json")],
        procedures=[Procedure.model_validate(r) for r in _load_json(seed_dir / "procedures.json")],
        denial_reasons=[DenialReason.model_validate(r) for r in _load_json(seed_dir / "denial_reasons.json")],
        providers=[Provider.model_validate(r) for r in _load_json(seed_dir / "providers.json")],
        patients=[Patient.model_validate(r) for r in _load_json(seed_dir / "patients.json")],
        historical_cases=[
            HistoricalCase.model_validate(r)
            for r in _load_json(DATA_DIR / "historical_cases" / "cases.json")
        ],
        incoming_claims=[
            IncomingClaim.model_validate(r)
            for r in _load_json(DATA_DIR / "claims" / "incoming_claims.json")
        ],
    )
