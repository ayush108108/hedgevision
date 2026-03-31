import asyncio
import builtins
import json
import sys
import types
from typing import Any

import pytest
from pydantic import ValidationError
from typer.testing import CliRunner

import hedgevision.cli as hv_cli
import hedgevision.mcp_server as hv_mcp
from hedgevision.broker.ccxt import _to_ccxt_symbol
from hedgevision.broker.router import get_broker
from hedgevision.config import SecureConfig
from hedgevision.core import market_intel as mi
from hedgevision.llm import router as llm_router
from hedgevision.models import (
    BrokerQuotePayload,
    MarketDataPayload,
    QuantMetricsPayload,
    SentimentPayload,
    StructuredVerdictPayload,
    validate_json_object,
)
from hedgevision.pipelines import daily_eod as daily_pipeline


def test_secure_config_rejects_invalid_provider(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "not-a-provider")
    with pytest.raises(ValidationError):
        SecureConfig.from_env()


def test_secure_config_override_validation():
    cfg = SecureConfig.from_env()
    with pytest.raises(ValidationError):
        cfg.with_overrides(llm_provider="definitely-invalid")


def test_strict_payloads_reject_invalid_shapes():
    with pytest.raises(ValidationError):
        StructuredVerdictPayload.model_validate(
            {
                "stance": "bullish",
                "confidence": 1.5,
                "headline": "x",
                "rationale": ["ok"],
                "model_version": "v1",
                "model_provider": "rules",
            }
        )

    with pytest.raises(ValidationError):
        BrokerQuotePayload.model_validate(
            {
                "symbol": "BTC-USD",
                "backend": "paper",
                "exchange": "paper",
                "last": 1.0,
                "timestamp_ms": -1,
            }
        )

    with pytest.raises(ValueError):
        validate_json_object(["not", "a", "dict"])


def test_ccxt_symbol_normalization():
    assert _to_ccxt_symbol("BTC-USD") == "BTC/USDT"
    assert _to_ccxt_symbol("eth/usdt") == "ETH/USDT"
    assert _to_ccxt_symbol("SOL-USDT") == "SOL/USDT"


def test_broker_router_invalid_backend():
    with pytest.raises(ValueError):
        get_broker(backend="invalid-backend")


def test_llm_router_sanitizes_payload():
    cfg = SecureConfig.from_env().with_overrides(llm_provider="ollama", llm_model="llama3.2")
    router = llm_router.LLMRouter(cfg)

    class DummyProvider:
        def __init__(self):
            self.messages = None
            self.model = None

        async def complete(self, messages: list[dict[str, str]], model: str) -> str:
            self.messages = messages
            self.model = model
            return '{"stance":"neutral","confidence":0.5,"headline":"ok","rationale":["r1"]}'

    dummy = DummyProvider()
    router._provider = dummy  # type: ignore[attr-defined]

    out = asyncio.run(
        router.chat(
            system_prompt="sys",
            user_payload={"api_key": "top-secret", "payload": "ok"},
        )
    )
    assert out.provider == "ollama"
    assert dummy.model == "llama3.2"
    assert dummy.messages is not None
    assert "***REDACTED***" in dummy.messages[1]["content"]


def test_market_intel_returns_validated_payload(monkeypatch):
    monkeypatch.setattr(
        mi,
        "fetch_market_data",
        lambda ticker: MarketDataPayload.model_validate(
            {"ticker": ticker, "price": 100.0, "pe_ratio": 15.0}
        ),
    )
    monkeypatch.setattr(
        mi,
        "compute_quant_metrics",
        lambda ticker, period="1y": QuantMetricsPayload.model_validate(
            {"ticker": ticker, "close": 120.0, "sma_50": 100.0, "volatility": 0.2}
        ),
    )
    result = asyncio.run(mi.run_market_intel("BTC-USD", use_llm=False))
    assert result["verdict"]["stance"] == "bullish"
    assert 0.0 <= result["verdict"]["confidence"] <= 1.0


def test_market_intel_invalid_llm_payload_falls_back(monkeypatch):
    monkeypatch.setattr(
        mi,
        "fetch_market_data",
        lambda ticker: {"ticker": ticker, "price": 100.0, "pe_ratio": 15.0},
    )
    monkeypatch.setattr(
        mi,
        "compute_quant_metrics",
        lambda ticker, period="1y": {"ticker": ticker, "close": 120.0, "sma_50": 100.0, "volatility": 0.2},
    )

    async def _bad_llm_verdict(**_kwargs):
        raise ValueError("bad llm output")

    monkeypatch.setattr(mi, "_llm_verdict", _bad_llm_verdict)
    cfg = SecureConfig.from_env().with_overrides(llm_provider="openai", llm_model="gpt-4o-mini")
    result = asyncio.run(mi.run_market_intel("BTC-USD", use_llm=True, config=cfg))
    assert result["verdict"]["model_provider"] == "rules"


def test_mcp_server_missing_dependency(monkeypatch):
    original_import = builtins.__import__

    def _import(name: str, *args: Any, **kwargs: Any):
        if name == "mcp.server.fastmcp":
            raise ImportError("forced")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _import)
    with pytest.raises(RuntimeError):
        hv_mcp.run_mcp_server()


def test_mcp_server_registers_tools(monkeypatch):
    class FakeFastMCP:
        last: "FakeFastMCP | None" = None

        def __init__(self, _name: str):
            self.tools: dict[str, Any] = {}
            self.ran = False
            FakeFastMCP.last = self

        def tool(self):
            def _decorator(fn):
                self.tools[fn.__name__] = fn
                return fn

            return _decorator

        def run(self):
            self.ran = True

    monkeypatch.setattr(
        hv_mcp,
        "fetch_market_data",
        lambda ticker: MarketDataPayload.model_validate({"ticker": ticker, "price": 1.0}),
    )
    monkeypatch.setattr(
        hv_mcp,
        "compute_quant_metrics",
        lambda ticker, period="1y": QuantMetricsPayload.model_validate({"ticker": ticker}),
    )
    monkeypatch.setattr(
        hv_mcp,
        "analyze_sentiment",
        lambda url: SentimentPayload.model_validate(
            {"sentiment": "neutral", "score": 0.0, "title": None}
        ),
    )

    fake_module = types.ModuleType("mcp.server.fastmcp")
    fake_module.FastMCP = FakeFastMCP
    monkeypatch.setitem(sys.modules, "mcp", types.ModuleType("mcp"))
    monkeypatch.setitem(sys.modules, "mcp.server", types.ModuleType("mcp.server"))
    monkeypatch.setitem(sys.modules, "mcp.server.fastmcp", fake_module)

    hv_mcp.run_mcp_server()
    assert FakeFastMCP.last is not None
    assert FakeFastMCP.last.ran is True
    assert set(FakeFastMCP.last.tools.keys()) == {
        "hv_fetch_market_data",
        "hv_compute_quant_metrics",
        "hv_analyze_sentiment",
    }
    tool_out = FakeFastMCP.last.tools["hv_fetch_market_data"]("BTC-USD")
    assert tool_out["ticker"] == "BTC-USD"
    metrics_out = FakeFastMCP.last.tools["hv_compute_quant_metrics"]("BTC-USD", "1y")
    assert metrics_out["ticker"] == "BTC-USD"
    sent_out = FakeFastMCP.last.tools["hv_analyze_sentiment"]("https://example.com")
    assert sent_out["sentiment"] == "neutral"


def test_cli_intel_and_broker_quote_commands(monkeypatch):
    runner = CliRunner()
    captured: dict[str, Any] = {}

    async def _fake_intel(**kwargs):
        captured.update(kwargs)
        return {
            "ticker": kwargs["ticker"],
            "market_data": {"ticker": kwargs["ticker"], "price": 1.0, "pe_ratio": None, "eps": None, "revenue_growth": None},
            "quant_metrics": {"ticker": kwargs["ticker"], "sma_50": None, "ema_20": None, "volatility": None, "close": None},
            "sentiment": None,
            "verdict": {
                "stance": "neutral",
                "confidence": 0.5,
                "headline": "ok",
                "rationale": ["r1"],
                "model_version": "prod-v1",
                "model_provider": "rules",
            },
        }

    class _FakeBroker:
        def get_quote(self, symbol: str):
            return BrokerQuotePayload.model_validate(
                {
                    "symbol": symbol,
                    "backend": "paper",
                    "exchange": "paper",
                    "last": 100.0,
                    "bid": 99.0,
                    "ask": 101.0,
                    "timestamp_ms": 1,
                }
            )

    monkeypatch.setattr(hv_cli, "run_market_intel", _fake_intel)
    monkeypatch.setattr(hv_cli, "get_broker", lambda **_kwargs: _FakeBroker())

    intel = runner.invoke(
        hv_cli.app,
        ["intel", "BTC-USD", "--use-llm", "--provider", "ollama", "--model", "llama3.2"],
    )
    assert intel.exit_code == 0
    intel_json = json.loads(intel.stdout)
    assert intel_json["ticker"] == "BTC-USD"
    assert captured["llm_provider"] == "ollama"
    assert captured["llm_model"] == "llama3.2"

    quote = runner.invoke(hv_cli.app, ["broker-quote", "BTC-USD"])
    assert quote.exit_code == 0
    quote_json = json.loads(quote.stdout)
    assert quote_json["backend"] == "paper"


def test_cli_sync_and_mcp_and_main(monkeypatch):
    runner = CliRunner()

    # sync --dry-run path
    dry = runner.invoke(hv_cli.app, ["sync", "--dry-run"])
    assert dry.exit_code == 0
    assert "sync_dry_run_ok" in dry.stdout

    # sync failure path
    monkeypatch.setattr(hv_cli, "run_daily_eod_sync", lambda: False)
    fail = runner.invoke(hv_cli.app, ["sync"])
    assert fail.exit_code == 1

    # mcp command path
    called = {"mcp": False}
    monkeypatch.setattr(hv_cli, "run_mcp_server", lambda: called.__setitem__("mcp", True))
    mcp = runner.invoke(hv_cli.app, ["mcp"])
    assert mcp.exit_code == 0
    assert called["mcp"] is True

    # main() path
    invoked = {"app": False}
    monkeypatch.setattr(hv_cli, "app", lambda: invoked.__setitem__("app", True))
    hv_cli.main()
    assert invoked["app"] is True


def test_cli_onboard_wizard_writes_env(tmp_path):
    runner = CliRunner()
    env_file = tmp_path / ".env"
    result = runner.invoke(
        hv_cli.app,
        ["onboard", "--env-file", str(env_file)],
        input="1\n3\n\n1\n1\ny\ny\n",
    )
    assert result.exit_code == 0
    text = env_file.read_text(encoding="utf-8")
    assert "DATA_BACKEND=sqlite" in text
    assert "LLM_PROVIDER=cpu" in text
    assert "LOCAL_ML_BACKEND=numpy" in text
    assert "BROKER_BACKEND=paper" in text


def test_daily_pipeline_wrapper_behaviors(monkeypatch):
    class _ModuleOK:
        @staticmethod
        async def main():
            return True

    class _ModuleBad:
        pass

    monkeypatch.setattr(daily_pipeline, "_load_daily_module", lambda: _ModuleOK)
    assert daily_pipeline.run_daily_eod_sync() is True

    monkeypatch.setattr(daily_pipeline, "_load_daily_module", lambda: _ModuleBad)
    with pytest.raises(RuntimeError):
        daily_pipeline.run_daily_eod_sync()
