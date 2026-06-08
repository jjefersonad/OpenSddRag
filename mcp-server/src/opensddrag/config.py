from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql://postgres:password@localhost:5432/opensddrag"
    embedding_model: str = "all-MiniLM-L6-v2"
    opensddrag_project: str = "default"
    auth_enabled: bool = True


settings = Settings()
