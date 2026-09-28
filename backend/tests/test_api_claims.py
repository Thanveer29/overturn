"""API-contract tests using mocked orchestrator calls -- no live Groq/Hindsight
credentials needed. The live behavior itself (recall/reflect/retain actually
working, and producing the expected before/after contrast) is verified
separately and documented in docs/architecture/hindsight-integration.md and
docs/architecture/agent-orchestrator.md, since that requires real credentials
and network access that CI/a fresh clone won't have.
"""

import app.api.claims as claims_api
from app.agents.orchestrator import HindsightUnavailableError, RecalledMemory, StrategyResult
from fastapi.testclient import TestClient


def _client() -> TestClient:
    from app.main import app

    return TestClient(app)


def test_list_claims_returns_all_five():
    resp = _client().get("/api/claims")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 5
    assert {c["claim_id"] for c in body} == {"CLM-101", "CLM-103", "CLM-104", "CLM-105", "CLM-106"}


def test_get_claim_detail():
    resp = _client().get("/api/claims/CLM-101")
    assert resp.status_code == 200
    body = resp.json()
    assert body["insurer_name"] == "Meridian Health Partners"
    assert body["procedure_name"] == "MRI Lumbar Spine without Contrast"
    assert "7-week physical therapy records" in body["evidence_available"]


def test_get_unknown_claim_404():
    resp = _client().get("/api/claims/NOT-A-CLAIM")
    assert resp.status_code == 404


def test_analyze_without_memory(monkeypatch):
    monkeypatch.setattr(
        claims_api,
        "analyze_without_memory",
        lambda ctx: StrategyResult(mode="without_memory", strategy_text="generic advice"),
    )
    resp = _client().post("/api/claims/CLM-101/analyze", json={"mode": "without_memory"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "without_memory"
    assert body["strategy_text"] == "generic advice"
    assert body["recalled_memories"] == []


def test_analyze_with_memory(monkeypatch):
    monkeypatch.setattr(
        claims_api,
        "analyze_with_memory",
        lambda ctx: StrategyResult(
            mode="with_memory",
            strategy_text="evidence-aware advice citing HC-003",
            recalled_memories=[RecalledMemory(type="observation", text="Meridian denied ...")],
        ),
    )
    resp = _client().post("/api/claims/CLM-101/analyze", json={"mode": "with_memory"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["mode"] == "with_memory"
    assert len(body["recalled_memories"]) == 1
    assert body["recalled_memories"][0]["type"] == "observation"


def test_analyze_reports_hindsight_unavailable_as_503(monkeypatch):
    def _raise(ctx):
        raise HindsightUnavailableError("Hindsight call failed: connection refused")

    monkeypatch.setattr(claims_api, "analyze_with_memory", _raise)
    resp = _client().post("/api/claims/CLM-101/analyze", json={"mode": "with_memory"})
    assert resp.status_code == 503


def test_draft_endpoint(monkeypatch):
    monkeypatch.setattr(claims_api, "draft_appeal", lambda ctx, strategy_text: f"Dear Insurer: {strategy_text}")
    resp = _client().post("/api/claims/CLM-101/draft", json={"strategy_text": "include PT records"})
    assert resp.status_code == 200
    assert resp.json()["draft"] == "Dear Insurer: include PT records"


def test_outcome_updates_claim_status(monkeypatch):
    monkeypatch.setattr(claims_api, "record_outcome", lambda ctx, outcome, notes: None)
    resp = _client().post(
        "/api/claims/CLM-103/outcome", json={"outcome": "approved", "notes": "test note"}
    )
    assert resp.status_code == 200

    detail = _client().get("/api/claims/CLM-103").json()
    assert detail["status"] == "resolved_approved"


def test_outcome_reports_hindsight_unavailable_as_503(monkeypatch):
    def _raise(ctx, outcome, notes):
        raise HindsightUnavailableError("retain failed")

    monkeypatch.setattr(claims_api, "record_outcome", _raise)
    resp = _client().post(
        "/api/claims/CLM-104/outcome", json={"outcome": "rejected", "notes": ""}
    )
    assert resp.status_code == 503
