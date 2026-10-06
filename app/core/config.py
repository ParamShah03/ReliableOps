from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "ReliableOps"
    environment: str = "development"
    log_level: str = "INFO"

    database_url: str = "postgresql+psycopg://reliableops:reliableops@db:5432/reliableops"
    redis_url: str = "redis://redis:6379/0"

    llm_provider: str = "mock"
    llm_base_url: str = "https://api.openai.com/v1"
    llm_api_key: str | None = None
    llm_model: str = "gpt-5.6"
    llm_timeout_seconds: float = 30.0
    llm_max_retries: int = 2

    embedding_provider: str = "local"
    embedding_dimension: int = 64

    max_agent_steps: int = 12
    max_same_tool_signature: int = 2
    auto_seed_knowledge: bool = True
    celery_task_always_eager: bool = False

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", case_sensitive=False, extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
