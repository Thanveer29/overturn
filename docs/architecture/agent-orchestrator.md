# Agent orchestrator

## Design: one clean pipeline, not eight agents for appearance

The original design brief lists eight potential agents (Denial Analyzer, Memory
Retriever, Evidence Analyzer, Historical Pattern Analyzer, Appeal Strategist, Appeal
Draft Generator, Outcome Analyzer, Memory Retention Agent) but explicitly says to
combine them where more appropriate and never split things apart just for show. Given
what Hindsight's `reflect()` already does — live-verified in
[hindsight-integration.md](hindsight-integration.md) to do recall + evidence-comparison +
directive-constrained reasoning in one call — re-implementing Memory Retriever, Evidence
Analyzer, Historical Pattern Analyzer, and Appeal Strategist as four separate LLM calls
would be redundant theater, not real engineering. So [`orchestrator.py`](../../backend/app/agents/orchestrator.py)
has four real steps:

| Step | What it does | Calls |
|---|---|---|
| `analyze_without_memory()` | The demo's "before": reasons only from the claim's own facts, no institutional history at all | Groq (`chat_completion`) |
| `analyze_with_memory()` | The demo's "after": recall (raw evidence trail, for the UI) + reflect (the actual evidence-aware, directive-constrained recommendation) | Hindsight `recall()` + `reflect()` |
| `draft_appeal()` | Turns a strategy into an actual formatted appeal letter — a distinct task (tone/formatting), not memory reasoning | Groq |
| `record_outcome()` | Retains what actually happened, closing the retain → recall → reflect → outcome → retain-again loop | Hindsight `retain()` |

Claim/insurer/procedure/patient/provider lookups (the "Denial Analyzer" step) are plain
SQLite reads in [`claims_repo.py`](../../backend/app/services/claims_repo.py) — no LLM
involved, since there's nothing to reason about in looking up a row by id. Per the
design brief's own tool-design rule ("do not allow the LLM to directly manipulate the
database without controlled tools"), the LLM never touches SQLite or Hindsight
directly — Python code always mediates.

**No LLM-driven function-calling/tool-use** is used here on purpose. The retrieval
sequence for a claim is fully deterministic (always: load claim → recall/reflect →
optionally draft → optionally record outcome), so there's nothing for the model to
decide by calling tools — that would add indirection and failure modes (the hackathon
docs specifically warn "make sure to have your agent ready to handle function calling
errors") without any actual benefit here.

## API

`backend/app/api/claims.py`, mounted at `/api/claims`:

- `GET /api/claims` — list all incoming claims (summary)
- `GET /api/claims/{claim_id}` — full detail, 404 if unknown
- `POST /api/claims/{claim_id}/analyze` — body `{"mode": "with_memory" | "without_memory"}`, returns the strategy text and (for `with_memory`) the raw recalled memories
- `POST /api/claims/{claim_id}/draft` — body `{"strategy_text": "..."}`, returns a draft appeal letter
- `POST /api/claims/{claim_id}/outcome` — body `{"outcome": "approved"|"rejected", "notes": "..."}`, records the outcome (SQLite status + Hindsight retain) — this is the human-in-the-loop point: nothing is ever submitted to a real insurer automatically, per the design brief's "human remains in control of final submission" rule

Both `analyze` and `outcome` return **503**, not a crash, if Hindsight is unreachable
(`HindsightUnavailableError`) — see Phase 22's "every external dependency should fail
gracefully" requirement.

## Live verification (real Groq + real Hindsight Cloud, not mocked)

Full request/response payloads are in the session log; summarized here.

**CLM-104 (Meridian, Knee MRI, medical-necessity denial) — the over-generalization trap:**
- *Without memory*: produced generic, textbook medical-necessity guidance (CPT codes,
  ACR Appropriateness Criteria, a general documentation checklist). Correct-sounding,
  but has no idea this specific insurer has a known "generic PT records aren't enough
  for a knee" failure mode.
- *With memory*: correctly recalled **HC-018** as the directly relevant precedent,
  explicitly said "generic or non-specific conservative treatment records are
  insufficient... requires documentation specifically tailored to the knee," and opened
  with disclaimer language pulled from the safety directive.
- This is the real, non-cosmetic degradation the design brief's Phase 32 "remove
  Hindsight and see what breaks" test asks for: without memory, the agent cannot know
  about the knee-specific documentation trap at all.

**CLM-106 (Alliance, CT Abdomen, insufficient documentation) — no precedent for this
insurer+procedure combination:**
- `reflect()` didn't fabricate a pattern. It found **HC-009** — same denial type
  (insufficient documentation) and same procedure (CT Abdomen), but a *different
  insurer* (Meridian, not Alliance) — and explicitly caveated it: *"represents only one
  historical instance of this denial type for this procedure... verify this requirement
  against the current medical policy of Alliance Coastal Insurance... Do not assume that
  documentation requirements for different procedures... apply."* This is a richer,
  more honest result than a flat "no relevant memory" message would have been, and is
  exactly the cross-insurer caution Phase 12/33 of the design brief asked the dataset to
  test for.

**CLM-105 (Summit Point, sleep study) — the full retain-again loop:**
- `draft_appeal()` produced a properly formatted appeal letter, including an explicit
  "Reviewer Flags" section listing what a human must verify before it's sent.
- `record_outcome()` retained the resolved outcome. A follow-up `recall()` for "Delroy
  Fontaine sleep study appeal outcome" returned it back, already auto-consolidated by
  Hindsight into a combined denial+outcome observation — proving retain → recall →
  reflect → outcome → retain-again works end to end, not just retain and recall in
  isolation.

## Tests

`backend/tests/test_api_claims.py` — API-contract tests (status codes, response shape,
404/503 handling) using FastAPI's `TestClient` with the orchestrator's LLM/Hindsight
calls mocked via `monkeypatch`, and a throwaway SQLite database loaded from the same
`data/*.json` (via `backend/tests/conftest.py`). These need no API keys and no network
access, so they run in CI or on a fresh clone; the *live* behavior above needs real
credentials and is verified manually and documented here instead.

```bash
python -m pytest backend/tests -q   # 9 passed
```

## Known follow-ups (frontend phase)

- `recall()` returns the whole bank's matches (60+ results for a broad query), not
  filtered by insurer/procedure — fine for a debugging script, too much for a UI panel.
  The frontend's "relevant memories" view should truncate to the top N and/or filter
  client-side by insurer/procedure name before rendering.
- No pagination or claim-creation endpoint yet — the incoming-claims list is fixed at 5
  demo claims by design (see [data-model.md](data-model.md)); a "new claim" intake flow
  is out of scope for the hackathon MVP.
