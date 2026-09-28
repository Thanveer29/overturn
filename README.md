# Overturn

> Turn every denied claim into institutional knowledge.

**Status:** early scaffold — architecture and repo structure only. Implementation in progress.

Overturn is an AI-powered medical insurance denial-appeal intelligence agent for
healthcare revenue-cycle teams. It uses [Hindsight](https://hindsight.vectorize.io/)
as its memory layer so that every denial and appeal outcome becomes institutional
knowledge that improves future recommendations.

This README is a placeholder. The full README (architecture, setup, demo, dataset,
evaluation, limitations) will be written once the core implementation lands — see
`docs/architecture/` for the design docs in the meantime.

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
