# Evaluation

**Prototype evaluation on a synthetic dataset. Not a real-world performance claim.**

## What this measures

`run_evaluation.py` runs all 5 incoming claims through both `analyze_without_memory()`
and `analyze_with_memory()` against the real backend (Groq completions + Hindsight
Cloud recall/reflect — not mocked; see `backend/tests/` for the offline contract tests)
and scores three things:

1. **Key case recalled** — for each claim, did the with-memory recommendation reference
   the one historical case its `demo_scenario` says is the key relevant precedent (see
   `EXPECTED_KEY_CASES` in the script, and `docs/architecture/data-model.md`'s case
   matrix)? Reported two ways — see the honest limitation below.
2. **Memory adds citations** — does the with-memory strategy cite more `HC-###` cases
   than the without-memory one (which should always cite zero, since it has no
   institutional history to draw on)?
3. **Uncertainty flagged** — does the with-memory recommendation include
   verification/caveat language (the safety directive's job — see
   `docs/architecture/hindsight-integration.md`)?

## Results (most recent run)

| Claim | Key case recalled (strict `HC-###` citation) | Key case recalled (incl. patient-name reference) | Memory adds citations | Uncertainty flagged |
|---|---|---|---|---|
| CLM-101 | ✅ | ✅ | ✅ | ✅ |
| CLM-103 | ✅ | ✅ | ✅ | ✅ |
| CLM-104 | ✅ | ✅ | ✅ | ✅ |
| CLM-105 | ❌ | ✅ | ❌ | ✅ |
| CLM-106 | ✅ | ✅ | ✅ | ✅ |

**4/5 strict, 5/5 including patient-name references, 5/5 uncertainty-flagged.** Full
machine-readable output (including the actual cited case lists) is in `results.json`,
regenerated each run — not hand-edited.

## An honest limitation this run surfaced

CLM-105 "failed" the strict metric, and here's exactly why, verified by hand (not
guessed): `reflect()`'s recommendation for CLM-105 read *"...following the strategy
used in the cases of Delroy Fontaine and Yuki Tanaka"* — it referenced the expected
precedent (HC-016) **by the patient's name, not by its `HC-016` case id**, even though
both appear in the retained fact's text. The citation-extraction heuristic (here, and
in `frontend/src/components/MemoryPanel.tsx`) only pattern-matches `HC-\d{3}`, so it
missed this as a citation. Once the check was extended to also accept a reference to
the case's patient name, CLM-105 passes (5/5). This is a real gap in a **string-matching
proxy metric**, not in the underlying memory system — the qualitative strategy text
(readable in full via `python scripts/query_memory.py CLM-105`) clearly used the right
institutional history regardless of which identifier it chose to cite by.

A second, unplanned wrinkle: earlier manual UI testing (Phase 5) recorded a real
"approved" outcome for CLM-105 itself into Hindsight Cloud. `reflect()` correctly
treated that as a second Summit Point precedent alongside HC-016 — which is the memory
system doing exactly what it's designed to do (retain → recall → reflect → outcome →
retain-again), but it does mean CLM-105's "only one historical case" framing in the
original dataset design is no longer strictly true after that test run. Left as-is and
documented here rather than reset, since it's a genuine (if accidental) demonstration of
the learning loop compounding over real usage.

## Running it yourself

```bash
python evaluation/run_evaluation.py
```

Calls real Groq + Hindsight Cloud APIs (10 live calls: 5 claims × 2 modes) — this costs
a small amount of API usage and takes roughly a minute. Overwrites `evaluation/results.json`
with a fresh timestamp each run; the version committed to the repo is a snapshot of one
real run, not hand-edited, and will differ slightly on re-runs given LLM non-determinism.
