# Hindsight integration

## Verified API (not guessed)

Per the hackathon's strict rule against fabricating Hindsight APIs, everything below was
confirmed against `hindsight.vectorize.io`'s live docs and the `vectorize-io/hindsight`
GitHub README before any code was written.

- **Install**: `pip install hindsight-client` (Python client). Server itself: `pip install
  hindsight-api` (bare metal, needs an LLM key) or the `ghcr.io/vectorize-io/hindsight`
  Docker image (also needs an LLM key, e.g. `HINDSIGHT_API_LLM_API_KEY`).
- **Client**: `Hindsight(base_url=..., api_key=..., timeout=...)`. `base_url` is
  `http://localhost:8888` for a local server, `https://api.hindsight.vectorize.io` for
  Hindsight Cloud.
- **Bank creation**: `create_bank(bank_id=...)` — banks are otherwise also created
  implicitly on first write. Configuration (mission, disposition) is applied separately via
  `update_bank_config(bank_id, retain_mission=, reflect_mission=, disposition_skepticism=,
  disposition_literalism=, disposition_empathy=, ...)`.
  **Directives** (hard rules) are a *separate* call: `create_directive(bank_id, name,
  content, tags=, is_active=)`. They only affect `reflect()`, not `recall()`.
- **`retain(bank_id, content, context=, timestamp=, document_id=, metadata=,
  retain_async=)`** — writes a fact.
- **`recall(bank_id, query, types=["world","experience","observation"], min_scores=,
  tags=, temporal_window=, budget=)`** — multi-strategy search (TEMPR: semantic + BM25 +
  graph + temporal). `observation` results carry `source_fact_ids` and a `source_facts`
  dict with per-stage scores (`semantic`, `keyword`, `reranker`, `final`) — **this is
  Hindsight's own evidence/confidence data**, which is why Overturn doesn't implement a
  separate confidence system (see Phase 7 in the original design brief).
- **`reflect(bank_id, query, budget=, context=, apply_all_directives=)`** — agentic
  reasoning over Mental Models → Observations → raw Facts, respecting active directives.

## Mapping onto Overturn

| Hindsight primitive | Overturn usage |
|---|---|
| One bank per org | `bank_id = org.id` (e.g. `riverside-medical-group`). Memory is institutional, shared across every staff member at that org — not per-user. |
| `retain()` | Called once per historical case during seeding (`scripts/seed_hindsight.py`), and again whenever a live claim's outcome is resolved during the demo — closing the retain → recall → reflect → outcome → retain-again loop. |
| `recall()` | Used to answer "what do we know about this insurer + procedure + denial reason?" — surfaces both matching and (correctly) non-matching historical cases. |
| `reflect()` | Used to generate the actual appeal-strategy recommendation, since it does prioritized Mental-Model → Observation → Fact reasoning natively. |
| Directive (`verify-before-asserting-policy`) | Hindsight-enforced safety rule: never assert a historical pattern is a guaranteed/current insurer policy; always frame as "N of M historical cases," and call out single-precedent cases explicitly. This is Hindsight's own hard-rule mechanism, not something Overturn re-implements — see [`hindsight_client.py`](../../backend/app/memory/hindsight_client.py). |
| `disposition_skepticism=4` | Set high deliberately — the bank should lean skeptical/cautious when reasoning about denial patterns, matching the "historical observation, verify current policy" tone required by the design brief. |

## What's implemented vs. what's still open

**Implemented** ([`backend/app/memory/hindsight_client.py`](../../backend/app/memory/hindsight_client.py)):
`OverturnMemory.ensure_org_bank()`, `.retain_historical_case()`, `.retain_outcome()`,
`.recall()`, `.reflect()`. Confirmed to import, construct, and fail *cleanly* (not crash)
against an unreachable server — see verification below.

**Not yet live-tested**: every call above still needs to be proven against a real,
running Hindsight instance. That requires either:

1. **Local server** — `pip install hindsight-api` or Docker, which needs an LLM API key
   (Groq's free tier is what the hackathon docs recommend) for the server's own fact
   extraction. Docker is not available in this dev environment, so the bare-metal `pip`
   route is the fallback.
2. **Hindsight Cloud** — `https://api.hindsight.vectorize.io` + an API key (the
   `MEMHACK99` promo code gives $50 credit, added after registering in billing).

Neither can be provisioned without your credentials — this is the actual blocker on
finishing live verification of this phase.

## Verification performed without a live server

```bash
python scripts/validate_seed_data.py   # schema + referential integrity — passes
python scripts/load_db.py              # loads all seed data into SQLite — passes
uvicorn app.main:app                   # FastAPI boots
curl localhost:8000/health             # {"status":"ok", "hindsight_base_url": "...", ...}
curl localhost:8000/health/hindsight   # {"status":"error", "detail": "Cannot connect..."}
```

The last line is the expected, correctly-handled result with no server running: the
wrapper attempted a real `recall()` call against `HINDSIGHT_BASE_URL` and reported the
connection failure instead of crashing the app.

## Next step once credentials are available

```bash
# Option A: local, bare-metal
export HINDSIGHT_API_LLM_PROVIDER=groq
export HINDSIGHT_API_LLM_API_KEY=gsk_...
pip install hindsight-api && hindsight-api   # starts on :8888

# Option B: Hindsight Cloud — set in .env
HINDSIGHT_BASE_URL=https://api.hindsight.vectorize.io
HINDSIGHT_API_KEY=<your cloud key>
```

Then: `python scripts/seed_hindsight.py` (creates the bank + directive, retains all 18
historical cases) and re-check `curl localhost:8000/health/hindsight` for `{"status":
"ok"}`.
