from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(REPO_ROOT / ".env"), env_file_encoding="utf-8", extra="ignore"
    )

    hindsight_base_url: str = "http://localhost:8888"
    hindsight_api_key: str | None = None

    groq_api_key: str | None = None
    llm_model: str = "openai/gpt-oss-120b"

    database_url: str = "sqlite:///./data/overturn.db"
    backend_port: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
