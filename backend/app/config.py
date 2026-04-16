from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field


DEFAULT_LOCAL_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]


def parse_csv(value: str | None, default: list[str]) -> list[str]:
    if not value:
        return default
    items = [item.strip() for item in value.split(",") if item.strip()]
    return items or default


def resolve_path(value: str | None, default: Path, base_dir: Path) -> Path:
    if not value:
        return default
    candidate = Path(value).expanduser()
    if not candidate.is_absolute():
        candidate = base_dir / candidate
    return candidate


class Settings(BaseModel):
    app_name: str = "Math_JIHC API"
    api_prefix: str = "/api/v1"
    environment: str = "development"
    base_dir: Path = Field(default_factory=lambda: Path(__file__).resolve().parents[1])
    database_path: Path
    uploads_dir: Path
    token_ttl_seconds: int = 60 * 60 * 24
    cache_ttl_seconds: int = 20
    max_upload_size_bytes: int = 5 * 1024 * 1024
    secret_key: str = "math-jihc-local-secret"
    cors_allow_origins: list[str] = Field(default_factory=lambda: DEFAULT_LOCAL_ORIGINS.copy())

    @classmethod
    def from_env(cls) -> "Settings":
        base_dir = Path(os.getenv("BACKEND_BASE_DIR", Path(__file__).resolve().parents[1])).expanduser().resolve()
        database_path = resolve_path(os.getenv("DATABASE_PATH"), base_dir / "data.sqlite3", base_dir)
        uploads_dir = resolve_path(os.getenv("UPLOADS_DIR"), base_dir / "uploads", base_dir)
        settings = cls(
            app_name=os.getenv("APP_NAME", "Math_JIHC API"),
            api_prefix=os.getenv("API_PREFIX", "/api/v1"),
            environment=os.getenv("ENVIRONMENT", "development").strip().lower(),
            base_dir=base_dir,
            database_path=database_path,
            uploads_dir=uploads_dir,
            token_ttl_seconds=int(os.getenv("TOKEN_TTL_SECONDS", str(60 * 60 * 24))),
            cache_ttl_seconds=int(os.getenv("CACHE_TTL_SECONDS", "20")),
            max_upload_size_bytes=int(os.getenv("MAX_UPLOAD_SIZE_BYTES", str(5 * 1024 * 1024))),
            secret_key=os.getenv("SECRET_KEY", "math-jihc-local-secret"),
            cors_allow_origins=parse_csv(os.getenv("CORS_ALLOW_ORIGINS"), DEFAULT_LOCAL_ORIGINS),
        )
        return settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings.from_env()
    if settings.environment == "production" and settings.secret_key == "math-jihc-local-secret":
        msg = "SECRET_KEY must be set in production."
        raise ValueError(msg)
    settings.uploads_dir.mkdir(parents=True, exist_ok=True)
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
