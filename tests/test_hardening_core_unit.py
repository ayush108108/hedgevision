import asyncio

from hedgevision.broker import get_broker
from hedgevision.config import SecureConfig
from hedgevision.security import sanitize_for_llm
from hedgevision.core import market_intel as mi


def test_sanitize_for_llm_masks_sensitive_values():
    payload = {
        "api_key": "secret123",
        "nested": {"token": "abc"},
        "url": "https://example.com/data?apikey=foo",
    }
    out = sanitize_for_llm(payload, max_chars=500)
    assert out["api_key"] == "***REDACTED***"
    assert out["nested"]["token"] == "***REDACTED***"
    assert "apikey=***REDACTED***" in out["url"]


def test_run_market_intel_rule_based(monkeypatch):
    monkeypatch.setattr(
        mi,
        "fetch_market_data",
        lambda ticker: {"ticker": ticker, "pe_ratio": 15, "price": 100},
    )
    monkeypatch.setattr(
        mi,
        "compute_quant_metrics",
        lambda ticker, period="1y": {"ticker": ticker, "close": 120.0, "sma_50": 100.0, "volatility": 0.2},
    )

    result = asyncio.run(mi.run_market_intel("BTC-USD", use_llm=False))
    verdict = result["verdict"]
    assert verdict["stance"] == "bullish"
    assert 0.5 <= verdict["confidence"] <= 0.95


def test_external_llm_blocked_when_disabled(monkeypatch):
    monkeypatch.setattr(
        mi,
        "fetch_market_data",
        lambda ticker: {"ticker": ticker, "pe_ratio": 15, "price": 100},
    )
    monkeypatch.setattr(
        mi,
        "compute_quant_metrics",
        lambda ticker, period="1y": {"ticker": ticker, "close": 120.0, "sma_50": 100.0, "volatility": 0.2},
    )

    async def _should_not_call(**_kwargs):
        raise AssertionError("_llm_verdict should not be called when external LLM is disabled")

    monkeypatch.setattr(mi, "_llm_verdict", _should_not_call)
    cfg = SecureConfig(
        llm_provider="openai",
        llm_model="gpt-4o-mini",
        llm_timeout_seconds=5,
        enable_external_llm=False,
        openai_api_key="test",
        anthropic_api_key=None,
        ollama_base_url="http://localhost:11434",
        broker_backend="paper",
        ccxt_exchange="binance",
        ccxt_api_key=None,
        ccxt_api_secret=None,
        sanitize_llm_payloads=True,
        max_prompt_chars=20000,
        local_ml_backend="numpy",
        local_ml_model_path=None,
        model_version="test-v1",
    )
    result = asyncio.run(mi.run_market_intel("BTC-USD", use_llm=True, config=cfg))
    assert result["verdict"]["model_provider"] == "rules"


def test_broker_router_defaults_to_paper():
    broker = get_broker(backend="paper")
    assert broker.backend == "paper"
