"""Runtime configuration: env-based settings + YAML model routing."""
from __future__ import annotations

import functools
import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-driven app settings. Model/task routing lives in YAML."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Storage
    media_root: str = "/var/plume/media"

    # Celery / Redis
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"

    # Upstream Rails API (internal only)
    rails_api_url: str = "http://api:3000"
    internal_api_key: str | None = None

    # Usage-log DB (shared postgres with Rails; orchestrator owns ai_usage_logs)
    database_url: str | None = Field(default=None)

    # Observability
    log_level: str = "INFO"
    sentry_dsn: str | None = None

    # YAML file location (override in tests)
    model_config_path: str = str(
        Path(__file__).parent / "models.yaml"
    )


class ProviderConfig(BaseModel):
    kind: str
    api_key_env: str | None = None
    base_url_env: str | None = None


class ModelEntry(BaseModel):
    provider: str
    cost_per_1k: list[float]
    max_tokens: int = 4096
    model_id: str | None = None  # for openai-like, the actual HF/upstream id


class BudgetConfig(BaseModel):
    daily_cap_usd: float = 5.0
    fallback_task_key: str = "stub-chat"


class ModelConfig(BaseModel):
    providers: dict[str, ProviderConfig]
    models: dict[str, ModelEntry]
    tasks: dict[str, list[str]]
    budget: BudgetConfig

    def task_chain(self, task: str) -> list[str]:
        """Preferred-first list of model keys for a given task."""
        if task not in self.tasks:
            raise KeyError(f"Unknown task: {task}")
        return list(self.tasks[task])

    def resolve_provider_env(self, provider_name: str) -> dict[str, Any]:
        """Resolve environment variables for a provider's creds."""
        p = self.providers[provider_name]
        out: dict[str, Any] = {"kind": p.kind}
        if p.api_key_env:
            out["api_key"] = os.getenv(p.api_key_env)
        if p.base_url_env:
            out["base_url"] = os.getenv(p.base_url_env)
        return out


@functools.lru_cache
def get_settings() -> Settings:
    return Settings()


@functools.lru_cache
def load_model_config(path: str | None = None) -> ModelConfig:
    resolved = path or get_settings().model_config_path
    with open(resolved, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return ModelConfig.model_validate(data)
