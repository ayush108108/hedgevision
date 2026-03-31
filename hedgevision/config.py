"""Configuration helpers for BYOK model routing and runtime behavior."""

from __future__ import annotations

import os
from typing import Literal

from pydantic import ConfigDict, Field, field_validator

from hedgevision.models import StrictModel


class SecureConfig(StrictModel):
    """Runtime configuration loaded and validated from environment variables."""

    model_config = ConfigDict(
        extra="forbid",
        frozen=True,
        validate_assignment=True,
        str_strip_whitespace=True,
    )

    llm_provider: Literal["rules", "openai", "anthropic", "ollama", "cpu"] = "ollama"
    llm_model: str = Field(default="llama3.2", min_length=1)
    llm_timeout_seconds: float = Field(default=30.0, gt=0.0)
    enable_external_llm: bool = False

    openai_api_key: str | None = None
    anthropic_api_key: str | None = None
    ollama_base_url: str = "http://localhost:11434"

    broker_backend: Literal["paper", "ccxt"] = "paper"
    ccxt_exchange: str = Field(default="binance", min_length=1)
    ccxt_api_key: str | None = None
    ccxt_api_secret: str | None = None

    sanitize_llm_payloads: bool = True
    max_prompt_chars: int = Field(default=20000, ge=256)

    local_ml_backend: Literal["numpy", "sklearn", "onnx"] = "numpy"
    local_ml_model_path: str | None = None

    model_version: str = Field(default="prod-v1", min_length=1)

    @field_validator("ollama_base_url")
    @classmethod
    def _normalize_ollama_url(cls, value: str) -> str:
        return value.rstrip("/")

    @classmethod
    def from_env(cls) -> "SecureConfig":
        return cls.model_validate(
            {
                "llm_provider": os.getenv("LLM_PROVIDER", "rules").strip().lower(),
                "llm_model": os.getenv("LLM_MODEL", "llama3.2").strip(),
                "llm_timeout_seconds": float(os.getenv("LLM_TIMEOUT_SECONDS", "30")),
                "enable_external_llm": os.getenv("ENABLE_EXTERNAL_LLM", "false").lower()
                in ("1", "true", "yes"),
                "openai_api_key": os.getenv("OPENAI_API_KEY"),
                "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY"),
                "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                "broker_backend": os.getenv("BROKER_BACKEND", "paper").strip().lower(),
                "ccxt_exchange": os.getenv("CCXT_EXCHANGE", "binance").strip().lower(),
                "ccxt_api_key": os.getenv("CCXT_API_KEY") or os.getenv("BINANCE_API_KEY"),
                "ccxt_api_secret": os.getenv("CCXT_API_SECRET")
                or os.getenv("BINANCE_API_SECRET")
                or os.getenv("BINANCE_SECRET_KEY"),
                "sanitize_llm_payloads": os.getenv("SANITIZE_LLM_PAYLOADS", "true").lower()
                in ("1", "true", "yes"),
                "max_prompt_chars": int(os.getenv("LLM_MAX_PROMPT_CHARS", "20000")),
                "local_ml_backend": os.getenv("LOCAL_ML_BACKEND", "numpy").strip().lower(),
                "local_ml_model_path": os.getenv("LOCAL_ML_MODEL_PATH"),
                "model_version": os.getenv("MODEL_VERSION", "prod-v1").strip(),
            }
        )

    def with_overrides(
        self, *, llm_provider: str | None = None, llm_model: str | None = None
    ) -> "SecureConfig":
        updates: dict[str, str] = {}
        if llm_provider is not None:
            updates["llm_provider"] = llm_provider
        if llm_model is not None:
            updates["llm_model"] = llm_model
        if not updates:
            return self
        merged = self.model_dump()
        merged.update(updates)
        return SecureConfig.model_validate(merged)
