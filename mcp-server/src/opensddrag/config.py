from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://postgres:password@localhost:5432/opensddrag"
    embedding_model: str = "all-MiniLM-L6-v2"
    opensddrag_project: str = "default"
    auth_enabled: bool = True

    # Rate limiter selection and tuning (consumed by the composition root
    # in `infrastructure/composition.py`). `rate_limiter="memory"` forces
    # the in-memory adapter even when a database is configured; any other
    # value uses the Postgres-backed adapter when `database_url` is set.
    rate_limiter: str = "pg"  # env: RATE_LIMITER
    rate_limiter_quota: int = 60  # env: RATE_LIMITER_QUOTA
    rate_limiter_window_seconds: int = 60  # env: RATE_LIMITER_WINDOW_SECONDS


settings = Settings()
