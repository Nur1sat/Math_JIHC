from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel


class Settings(BaseModel):
    app_name: str = "Math_JIHC API"
    api_prefix: str = "/api/v1"
    base_dir: Path = Path(__file__).resolve().parents[1]
    database_path: Path = base_dir / "data.sqlite3"
    uploads_dir: Path = base_dir / "uploads"
    token_ttl_seconds: int = 60 * 60 * 24
    cache_ttl_seconds: int = 20
    max_upload_size_bytes: int = 5 * 1024 * 1024
    secret_key: str = "math-jihc-local-secret"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.base_dir.mkdir(parents=True, exist_ok=True)
    return settings
