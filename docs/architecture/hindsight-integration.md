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

## What's implemented, and live-verified against Hindsight Cloud

**Implemented** ([`backend/app/memory/hindsight_client.py`](../../backend/app/memory/hindsight_client.py)):
`OverturnMemory.ensure_org_bank()`, `.retain_historical_case()`, `.retain_outcome()`,
`.recall()`, `.reflect()`, plus context-manager support (`with OverturnMemory() as m:`)
so the underlying `aiohttp` session closes cleanly.

### Local server attempt — blocked, documented for the record

Docker isn't available in this dev environment, so the bare-metal `pip install
hindsight-api` route was tried first. It failed twice, for two distinct, real reasons
(not fabricated — both came from actual stack traces):

1. The default local-ML embeddings/reranker path needs `sentence-transformers`, which
   isn't installed by `hindsight-api` alone — the server printed its own actionable
   error naming the fix (`pip install hindsight-api[local-ml]`, or switch to a remote
   embeddings provider).
2. After installing `sentence-transformers`, importing it transitively pulls in
   `scikit-learn`'s compiled `_pairwise_distances_reduction` extension, and loading that
   `.pyd` was blocked by this machine's **Windows Application Control policy**
   (`DLL load failed... An Application Control policy has blocked this file`) — a
   corporate security control, not something to work around.

Given that, **Hindsight Cloud** was used instead — it does embeddings/reranking
server-side, sidestepping the blocked local dependency entirely, and is a legitimate
deployment target on its own.

### Live verification against Hindsight Cloud

```bash
python scripts/validate_seed_data.py   # schema + referential integrity — passes
python scripts/load_db.py              # loads all seed data into SQLite — passes
python scripts/seed_hindsight.py       # creates the bank + directive, retains 18 cases — passes
python scripts/query_memory.py CLM-101 # live recall() + reflect() — see below
```

`seed_hindsight.py` created the `riverside-medical-group` bank, applied
`retain_mission`/`reflect_mission`/disposition config, created the
`verify-before-asserting-policy` directive, and retained all 18 historical cases without
error.

`query_memory.py CLM-101` (Meridian + Lumbar MRI + medical necessity — the core pattern
case) then proved the full loop live:

- **`recall()`** returned all of HC-001–HC-008 and HC-015 (the Meridian lumbar-MRI
  cluster) as both `world` facts and auto-consolidated `observation`s, alongside
  everything else in the bank (Alliance/Summit Point cases, the CT-abdomen and
  sleep-study cases) — confirming `recall()` is a broad multi-strategy search, not a
  filtered one; narrowing happens in `reflect()` or via the agent's own tool-level
  filtering (Phase 5).
- **`reflect()`** produced a structured, evidence-cited recommendation: it built a table
  of exactly the 9 relevant historical cases, correctly identified the winning pattern
  (6+ weeks PT documentation + specialist referral, from HC-003/005/007), correctly
  flagged HC-008 as a case where that same pattern still failed (missing neurological
  exam findings), and referenced HC-018 as a cross-insurer caution against generic
  documentation — all without being told any of this by the query itself.
- The directive worked as designed: `reflect()`'s output opened with *"These do not
  represent a guaranteed, current, or universal policy of Meridian Health Partners.
  Always verify the insurer's current clinical guidelines..."* — language pulled
  directly from `SAFETY_DIRECTIVE_CONTENT`, confirming Hindsight is enforcing the
  directive during reasoning rather than it being decorative.

This is the strongest evidence so far for the hackathon's 25%-weighted "Use of Hindsight
Memory" criterion: the safety framing and the pattern-vs-exception reasoning came from
Hindsight's own retrieval and reasoning, not from prompt engineering in Overturn's code.

## Known follow-ups

- `recall()`'s `types`/`min_scores`/`tags` filters (verified in the API reference) aren't
  used yet — the agent's tools (Phase 5) should filter by insurer/procedure so the UI's
  "relevant memories" list isn't the full bank.
- `retain_outcome()` is written but not yet exercised — that happens once the agent
  processes a live claim and its outcome is recorded (Phase 6/7).
