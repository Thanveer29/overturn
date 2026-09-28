# Frontend

## Stack

React + TypeScript + Vite (`npm create vite -- --template react-ts`), `react-router-dom`
for the two routes, `react-markdown` + `remark-gfm` for rendering the LLM's markdown
output (headings/tables/bold — see below for why this needed fixing). No UI framework;
hand-written CSS (`src/index.css`) using CSS variables, since a full design system would
be overkill for two pages.

## Pages, not eight screens

The original design brief lists eight possible screens (Dashboard, Denial Workbench,
Claim Details, Appeal Strategy, Institutional Memory, Memory Timeline, Outcome/Learning,
Before-vs-After Demo). Per its own Phase 17 guidance — *"the demo should focus on
'watch the agent learn,' not 'watch us navigate our dashboard'"* — these are collapsed
into two:

- **`ClaimsListPage`** (`/`) — the Denial Workbench: a table of the 5 incoming claims.
- **`ClaimDetailPage`** (`/claims/:claimId`) — everything else, as one continuous
  workflow: claim details → evidence → before/after analysis → why-this-recommendation
  → appeal draft → outcome recording. This is deliberately one scrollable page, not five
  separate ones, so a demo is "click Analyze, watch it happen" rather than tab-hopping.

## Key components

- **`api.ts`** — typed fetch wrapper for the five backend endpoints (list/detail/
  analyze/draft/outcome), with an `ApiError` carrying the HTTP status so 503s
  (Hindsight unavailable) can be distinguished from 404s in the UI.
- **`Markdown.tsx`** — wraps `react-markdown`. Both Groq completions and Hindsight's
  `reflect()` return markdown (headings, bold, tables). The first working version
  rendered this as plain text, so a strategy recommendation showed up as literal
  `## Heading` and `| table | syntax |` on screen — this was caught during live UI
  verification (see below), not just assumed away, and fixed by rendering through
  `react-markdown` + `remark-gfm` instead of a plain `<div>`/`<pre>`.
- **`MemoryPanel.tsx`** — the "why did Overturn recommend this?" panel. `recall()`
  intentionally returns the whole bank's matches (60-70+ results for a broad query,
  confirmed in `docs/architecture/agent-orchestrator.md`), which is too much to dump in
  a UI panel. This component extracts `HC-###` case ids the recommendation actually
  cited (regex on the strategy text) and filters the recalled memories down to those,
  falling back to the first 8 if nothing was explicitly cited. This is a client-side
  heuristic, not a Hindsight API filter — documented here so it isn't mistaken for one.

## Live UI verification (real backend, real Groq, real Hindsight Cloud)

Run end-to-end through the actual browser (not just `curl`), on **CLM-104** (the
over-generalization trap case):

1. Claims list loaded all 5 claims from the live API.
2. Opened CLM-104's detail page — claim info and evidence rendered correctly.
3. Clicked "Analyze this claim" — both `without_memory` and `with_memory` calls ran,
   and after the markdown fix, both panels rendered as proper formatted text (headings,
   tables), not raw syntax.
4. The "why" panel showed **"Historical cases cited: HC-003 HC-007 HC-018 HC-001 HC-002
   HC-006 HC-015 HC-008"** as chips, and correctly filtered to **16 of 72** recalled
   memories — exactly the ones backing those citations.
5. "Generate appeal draft" produced a formatted letter.
6. "Record outcome" (approved) succeeded, retained into Hindsight, and the status badge
   updated in place without a page reload.

One rough edge found during this: this sandboxed browser pane's screenshot capture
returned blank/stale frames when the page was scrolled while the pane was hidden or
mid-transition — `get_page_text`/`read_page` were used instead to verify rendered
content, per the tool's own guidance for a hidden pane, and confirmed correct content on
every check. This looks like a tool-side rendering quirk, not an application bug (a
non-scrolled screenshot of the same page rendered perfectly).

## A dev-environment gotcha worth recording

`preview_start({name: "frontend"})` did **not** use this repo's `.claude/launch.json` —
it ran a same-named `"frontend"` config from a different, unrelated project that
happened to be this session's original working directory, launching its
`react-scripts start` (a completely different app) instead of this repo's Vite server.
The Browser-pane tooling appears to resolve `.claude/launch.json` against the session's
original root, not the directory `cd`'d to during the session. Worked around by starting
`npm run dev` directly and attaching the browser pane by URL (`navigate` /
`preview_start({url: ...})`) instead of by config name.

## Running locally

```bash
# backend (from repo root)
.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --port 8000

# frontend (separate terminal)
cd frontend && npm run dev   # http://localhost:5173
```

`frontend/.env` sets `VITE_API_BASE_URL=http://localhost:8000`. CORS is already
configured on the backend for `localhost:5173`.

```bash
cd frontend && npm run lint && npm run build   # oxlint clean, tsc + vite build clean
```
