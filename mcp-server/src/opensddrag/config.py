from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://postgres:password@localhost:5432/opensddrag"
    embedding_model: str = "all-MiniLM-L6-v2"
    opensddrag_project: str = "default"
    auth_enabled: bool = True

    # Web management API (capability `web-api-management` of
    # `web-management-system`). `management_token` gates the /api/v1 REST
    # delivery adapter: when unset, /api/v1 fails closed (all 401). Alias
    # keeps the documented env name MANAGEMENT_API_TOKEN (the plain field
    # name would map to MANAGEMENT_TOKEN). `web_origin` allows the CORS
    # origin of the web dashboard.
    management_token: str | None = Field(
        default=None,
        validation_alias=AliasChoices("MANAGEMENT_API_TOKEN", "MANAGEMENT_TOKEN"),
    )
    web_origin: str = "http://localhost:3001"  # env: WEB_ORIGIN

    # Opt-in static serving of the built web dashboard (web/dist) at "/" in
    # SSE mode (mcp-server REQ-016). Default False: no static mount unless
    # enabled (or overridden by `opensddrag-server web --serve-ui`).
    serve_web_ui: bool = False  # env: SERVE_WEB_UI

    # Rate limiter selection and tuning (consumed by the composition root
    # in `infrastructure/composition.py`). `rate_limiter="memory"` forces
    # the in-memory adapter even when a database is configured; any other
    # value uses the Postgres-backed adapter when `database_url` is set.
    rate_limiter: str = "pg"  # env: RATE_LIMITER
    rate_limiter_quota: int = 60  # env: RATE_LIMITER_QUOTA
    rate_limiter_window_seconds: int = 60  # env: RATE_LIMITER_WINDOW_SECONDS

    # Hybrid search (capability `hybrid-search` of `improve-retrieval-accuracy`).
    # When enabled, `search_semantic` fuses a lexical (Postgres `tsvector` /
    # `ts_rank`) ranking with the existing vector (pgvector cosine) ranking
    # using Reciprocal Rank Fusion. When disabled, the pure-vector query is
    # used as a safe rollback without redeploy. CPU-only — no model change.
    hybrid_search_enabled: bool = True
    search_candidate_depth: int = 20
    rrf_k: int = 60


settings = Settings()
