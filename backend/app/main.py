from fastapi import FastAPI

from app.core.config import get_settings

app = FastAPI(title="Overturn API")


@app.get("/health")
def health():
    settings = get_settings()
    return {
        "status": "ok",
        "hindsight_base_url": settings.hindsight_base_url,
        "llm_model": settings.llm_model,
    }


@app.get("/health/hindsight")
def health_hindsight():
    """Cheap live check that the configured Hindsight server is reachable.
    Not a hard dependency of app startup — reports its own status instead."""
    from app.memory.hindsight_client import OverturnMemory

    try:
        with OverturnMemory() as memory:
            memory.recall(org_id="riverside-medical-group", query="health check")
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "error", "detail": str(exc)}
