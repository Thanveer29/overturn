# Overturn

> Turn every denied claim into institutional knowledge.

**Status:** core loop working end-to-end (backend, Hindsight memory, agent, frontend),
live-verified against real Groq + Hindsight Cloud. Evaluation harness, tests, and
submission content (video/article) are still in progress.

Overturn is an AI-powered medical insurance denial-appeal intelligence agent for
healthcare revenue-cycle teams. It uses [Hindsight](https://hindsight.vectorize.io/)
as its memory layer so that every denial and appeal outcome becomes institutional
knowledge that improves future recommendations.

This README is still a placeholder for the polished version (setup, demo, dataset,
evaluation, limitations) that will be written once evaluation and submission content are
done. In the meantime, see `docs/architecture/`:

- [`data-model.md`](docs/architecture/data-model.md) — entities and the synthetic dataset
- [`hindsight-integration.md`](docs/architecture/hindsight-integration.md) — the verified
  Hindsight API and live retain/recall/reflect results
- [`agent-orchestrator.md`](docs/architecture/agent-orchestrator.md) — the agent pipeline
  and live before/after verification
- [`frontend.md`](docs/architecture/frontend.md) — the UI and how to run it locally

## Repo layout

```
backend/     FastAPI app, agent orchestrator, Hindsight integration, tools
frontend/    React/Vite dashboard
data/        Synthetic claims, historical cases, seed data
evaluation/  Memory retrieval / recommendation evaluation harness
docs/        Architecture, demo materials, screenshots
scripts/     Setup and dev utility scripts
```

## Disclaimer

Overturn is a hackathon prototype built on synthetic data. It is not a medical or
legal decision system, does not submit real insurance appeals, and always keeps a
human in the loop before any appeal is finalized.
