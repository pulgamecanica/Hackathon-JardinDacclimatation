"""Wire YAML model config → concrete LLMProvider instances."""
from __future__ import annotations

from functools import lru_cache

from app.config import load_model_config
from app.llm.base import LLMProvider
from app.llm.providers import (
    AnthropicProvider,
    OpenAILikeProvider,
    OpenAIProvider,
    StubProvider,
)

_KIND_TO_CLASS = {
    "stub": StubProvider,
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "openai-like": OpenAILikeProvider,
}


@lru_cache
def _build_provider(provider_name: str) -> LLMProvider:
    cfg = load_model_config()
    if provider_name not in cfg.providers:
        raise KeyError(f"Unknown provider: {provider_name}")
    kind = cfg.providers[provider_name].kind
    cls = _KIND_TO_CLASS.get(kind)
    if cls is None:
        raise ValueError(f"Unsupported provider kind: {kind}")

    init_kwargs = cfg.resolve_provider_env(provider_name)
    init_kwargs.pop("kind")
    # Provider classes accept only the kwargs they need — filter quietly.
    if kind == "stub":
        return cls()  # type: ignore[call-arg]
    if kind in ("openai", "openai-like"):
        return cls(api_key=init_kwargs.get("api_key"), base_url=init_kwargs.get("base_url"))  # type: ignore[call-arg]
    if kind == "anthropic":
        return cls(api_key=init_kwargs.get("api_key"))  # type: ignore[call-arg]
    raise ValueError(f"Unhandled provider kind: {kind}")


def provider_for(model_key: str) -> LLMProvider:
    cfg = load_model_config()
    if model_key not in cfg.models:
        raise KeyError(f"Unknown model: {model_key}")
    return _build_provider(cfg.models[model_key].provider)


def provider_is_configured(provider_name: str) -> bool:
    """True if the provider has its credentials present (or doesn't need any)."""
    cfg = load_model_config()
    if provider_name not in cfg.providers:
        return False
    p = cfg.providers[provider_name]
    if p.kind == "stub":
        return True
    if p.api_key_env:
        import os

        if not os.getenv(p.api_key_env):
            return False
    if p.base_url_env:
        import os

        if not os.getenv(p.base_url_env):
            return False
    return True


def clear_cache() -> None:
    """Testing helper — drop cached provider instances (for env changes)."""
    _build_provider.cache_clear()
