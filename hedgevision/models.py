"""Shared strict Pydantic models for HedgeVision core boundaries."""

from __future__ import annotations

import math
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class StrictModel(BaseModel):
    """Base model with strict boundary validation defaults."""

    model_config = ConfigDict(
        extra="forbid",
        validate_assignment=True,
        str_strip_whitespace=True,
    )


class MarketDataPayload(StrictModel):
    ticker: str = Field(min_length=1)
    price: float | None = None
    pe_ratio: float | None = None
    eps: float | None = None
    revenue_growth: float | None = None

    @field_validator("price", "pe_ratio", "eps", "revenue_growth")
    @classmethod
    def _finite_float_or_none(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if not math.isfinite(value):
            return None
        return value


class SentimentPayload(StrictModel):
    sentiment: Literal["positive", "negative", "neutral"]
    score: float = 0.0
    title: str | None = None
    error: str | None = None

    @field_validator("score")
    @classmethod
    def _finite_score(cls, value: float) -> float:
        if not math.isfinite(value):
            return 0.0
        return value


class QuantMetricsPayload(StrictModel):
    ticker: str = Field(min_length=1)
    sma_50: float | None = None
    ema_20: float | None = None
    volatility: float | None = None
    close: float | None = None

    @field_validator("sma_50", "ema_20", "volatility", "close")
    @classmethod
    def _finite_metric_or_none(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if not math.isfinite(value):
            return None
        return value


class StructuredVerdictPayload(StrictModel):
    stance: Literal["bullish", "bearish", "neutral"]
    confidence: float = Field(ge=0.0, le=1.0)
    headline: str = Field(min_length=1)
    rationale: list[str] = Field(min_length=1, max_length=3)
    model_version: str = Field(min_length=1)
    model_provider: str = Field(min_length=1)

    @field_validator("rationale")
    @classmethod
    def _normalize_rationale(cls, value: list[str]) -> list[str]:
        cleaned = [item.strip() for item in value if item and item.strip()]
        if not cleaned:
            raise ValueError("rationale cannot be empty")
        return cleaned[:3]


class MarketIntelResponsePayload(StrictModel):
    ticker: str = Field(min_length=1)
    market_data: MarketDataPayload
    quant_metrics: QuantMetricsPayload
    sentiment: SentimentPayload | None = None
    verdict: StructuredVerdictPayload


class LLMResponsePayload(StrictModel):
    provider: Literal["openai", "anthropic", "ollama", "rules", "cpu"]
    model: str = Field(min_length=1)
    text: str


class BrokerQuotePayload(StrictModel):
    symbol: str = Field(min_length=1)
    backend: Literal["paper", "ccxt"]
    exchange: str = Field(min_length=1)
    last: float | None = None
    bid: float | None = None
    ask: float | None = None
    timestamp_ms: int | None = None

    @field_validator("last", "bid", "ask")
    @classmethod
    def _finite_quote_or_none(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if not math.isfinite(value):
            return None
        return value

    @field_validator("timestamp_ms")
    @classmethod
    def _timestamp_non_negative(cls, value: int | None) -> int | None:
        if value is None:
            return None
        if value < 0:
            raise ValueError("timestamp_ms must be >= 0")
        return value


class BrokerOrderPayload(StrictModel):
    order_id: str = Field(min_length=1)
    symbol: str = Field(min_length=1)
    side: Literal["buy", "sell"]
    quantity: float = Field(gt=0)
    price: float | None = None
    status: Literal["open", "filled", "cancelled", "rejected"] = "open"
    backend: Literal["paper", "ccxt"] = "paper"
    filled_quantity: float = 0.0
    average_fill_price: float | None = None

    @field_validator("quantity", "filled_quantity", "price", "average_fill_price")
    @classmethod
    def _finite_or_none(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if not math.isfinite(value):
            return None
        return value


class BrokerPositionPayload(StrictModel):
    symbol: str = Field(min_length=1)
    quantity: float
    average_cost: float | None = None
    current_price: float | None = None
    unrealised_pnl: float | None = None
    backend: Literal["paper", "ccxt"] = "paper"

    @field_validator("quantity", "average_cost", "current_price", "unrealised_pnl")
    @classmethod
    def _finite_or_none(cls, value: float | None) -> float | None:
        if value is None:
            return None
        if not math.isfinite(value):
            return None
        return value


def validate_json_object(payload: Any) -> dict[str, Any]:
    """Validate that parsed JSON is a dictionary object."""
    if not isinstance(payload, dict):
        raise ValueError("Expected JSON object payload")
    return payload
