import asyncio
import builtins
import importlib.util
import sys
import types

import pandas as pd
import pytest

from hedgevision.broker.ccxt import CCXTBroker
from hedgevision.broker.paper import PaperBroker
from hedgevision.config import SecureConfig
from hedgevision.core import market_intel as mi
from hedgevision.llm.router import LLMRouter
from hedgevision.models import MarketDataPayload, QuantMetricsPayload, SentimentPayload
from hedgevision.pipelines import daily_eod as daily_pipeline
from hedgevision.security import sanitize_for_llm


def test_sanitize_for_llm_handles_collections_and_truncation():
    out = sanitize_for_llm(
        {
            "list": [{"token": "secret"}],
            "tuple": ({"password": "x"},),
            "long": "a" * 20,
        },
        max_chars=10,
    )
    assert out["list"][0]["token"] == "***REDACTED***"
    assert out["tuple"][0]["password"] == "***REDACTED***"
    assert "[TRUNCATED" in out["long"]

    # Serializable scalar branch
    assert sanitize_for_llm(42) == 42

    # Non-serializable object branch
    class _Obj:
        def __str__(self):
            return "token=abc"

    out_obj = sanitize_for_llm(_Obj(), max_chars=100)
    assert "token=***REDACTED***" in out_obj


def test_paper_broker_missing_yfinance(monkeypatch):
    original_import = builtins.__import__

    def _import(name, *args, **kwargs):
        if name == "yfinance":
            raise ImportError("forced")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _import)
    with pytest.raises(RuntimeError):
        PaperBroker().get_quote("BTC-USD")


def test_paper_broker_quote_success(monkeypatch):
    class _FakeTs:
        def timestamp(self):
            return 123.0

    class _Ticker:
        fast_info = {"lastPrice": 10.5, "bid": 10.0, "ask": 11.0, "lastTradeDate": _FakeTs()}
        info = {"regularMarketPrice": 10.4}

    fake_mod = types.ModuleType("yfinance")
    fake_mod.Ticker = lambda _symbol: _Ticker()
    monkeypatch.setitem(sys.modules, "yfinance", fake_mod)

    out = PaperBroker().get_quote("BTC-USD")
    assert out.last == 10.5
    assert out.timestamp_ms == 123000


def test_paper_broker_handles_partial_failures(monkeypatch):
    class _BadTicker:
        @property
        def fast_info(self):
            raise RuntimeError("fast fail")

        @property
        def info(self):
            raise RuntimeError("info fail")

    fake_mod = types.ModuleType("yfinance")
    fake_mod.Ticker = lambda _symbol: _BadTicker()
    monkeypatch.setitem(sys.modules, "yfinance", fake_mod)
    out = PaperBroker().get_quote("BTC-USD")
    assert out.last is None
    assert out.timestamp_ms is None


def test_ccxt_broker_init_import_error(monkeypatch):
    original_import = builtins.__import__

    def _import(name, *args, **kwargs):
        if name == "ccxt":
            raise ImportError("forced")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _import)
    with pytest.raises(RuntimeError):
        CCXTBroker(exchange_id="binance")


def test_ccxt_broker_quote_success(monkeypatch):
    class _Exchange:
        def __init__(self, _cfg):
            self.apiKey = None
            self.secret = None

        def fetch_ticker(self, _symbol):
            return {"last": 100.0, "bid": 99.0, "ask": 101.0, "timestamp": 123}

    fake_ccxt = types.ModuleType("ccxt")
    fake_ccxt.binance = _Exchange
    monkeypatch.setitem(sys.modules, "ccxt", fake_ccxt)

    broker = CCXTBroker(exchange_id="binance")
    out = broker.get_quote("BTC-USD")
    assert out.backend == "ccxt"
    assert out.exchange == "binance"
    assert out.last == 100.0


def test_get_broker_ccxt_branch(monkeypatch):
    import hedgevision.broker.router as router_mod

    class _Dummy:
        backend = "ccxt"

    monkeypatch.setattr(router_mod, "CCXTBroker", lambda **_kwargs: _Dummy())
    out = router_mod.get_broker(backend="ccxt", exchange="binance")
    assert out.backend == "ccxt"


def test_llm_router_provider_paths(monkeypatch):
    # OpenAI path
    class _OpenAICreate:
        async def create(self, **_kwargs):
            msg = types.SimpleNamespace(content="openai-ok")
            choice = types.SimpleNamespace(message=msg)
            return types.SimpleNamespace(choices=[choice])

    class _OpenAIClient:
        def __init__(self, **_kwargs):
            self.chat = types.SimpleNamespace(completions=_OpenAICreate())

    fake_openai = types.ModuleType("openai")
    fake_openai.AsyncOpenAI = _OpenAIClient
    monkeypatch.setitem(sys.modules, "openai", fake_openai)

    cfg_openai = SecureConfig.model_validate(
        {**SecureConfig.from_env().model_dump(), "llm_provider": "openai", "openai_api_key": "k"}
    )
    openai_router = LLMRouter(cfg_openai)
    openai_resp = asyncio.run(openai_router.chat(system_prompt="s", user_payload="u"))
    assert openai_resp.text == "openai-ok"

    # Anthropic path
    class _Block:
        type = "text"
        text = "anthropic-ok"

    class _AnthropicMessages:
        async def create(self, **_kwargs):
            return types.SimpleNamespace(content=[_Block()])

    class _AnthropicClient:
        def __init__(self, **_kwargs):
            self.messages = _AnthropicMessages()

    fake_anthropic = types.ModuleType("anthropic")
    fake_anthropic.AsyncAnthropic = _AnthropicClient
    monkeypatch.setitem(sys.modules, "anthropic", fake_anthropic)

    cfg_anthropic = SecureConfig.model_validate(
        {
            **SecureConfig.from_env().model_dump(),
            "llm_provider": "anthropic",
            "anthropic_api_key": "k",
        }
    )
    anth_router = LLMRouter(cfg_anthropic)
    anth_resp = asyncio.run(anth_router.chat(system_prompt="s", user_payload="u"))
    assert anth_resp.text == "anthropic-ok"

    # Ollama path
    class _Resp:
        def raise_for_status(self):
            return None

        def json(self):
            return {"message": {"content": "ollama-ok"}}

    class _Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def post(self, *_args, **_kwargs):
            return _Resp()

    monkeypatch.setattr("hedgevision.llm.router.httpx.AsyncClient", lambda **_kwargs: _Client())
    cfg_ollama = SecureConfig.model_validate(
        {**SecureConfig.from_env().model_dump(), "llm_provider": "ollama"}
    )
    ollama_router = LLMRouter(cfg_ollama)
    ollama_resp = asyncio.run(ollama_router.chat(system_prompt="s", user_payload={"api_key": "x"}))
    assert ollama_resp.text == "ollama-ok"


def test_llm_router_rules_provider_works():
    """rules provider should now return a stub — no ValueError."""
    cfg = SecureConfig.model_validate(
        {**SecureConfig.from_env().model_dump(), "llm_provider": "rules"}
    )
    router = LLMRouter(cfg)  # Must not raise
    assert router is not None


def test_market_intel_source_functions_and_sentiment(monkeypatch):
    class _Ticker:
        fast_info = {"lastPrice": 100.0}
        info = {"trailingPE": 20.0, "trailingEps": 3.0, "revenueGrowth": 0.2}

    monkeypatch.setattr(mi.yf, "Ticker", lambda _ticker: _Ticker())
    md = mi.fetch_market_data("AAPL")
    assert isinstance(md, MarketDataPayload)
    assert md.ticker == "AAPL"

    close = pd.Series([float(x) for x in range(1, 100)])
    monkeypatch.setattr(
        mi.yf,
        "download",
        lambda *args, **kwargs: pd.DataFrame({"Close": close}),
    )
    qm = mi.compute_quant_metrics("AAPL")
    assert isinstance(qm, QuantMetricsPayload)
    assert qm.close is not None

    # Trigger "Close as DataFrame" branch
    multi = pd.DataFrame(
        {("Close", "AAPL"): [float(x) for x in range(1, 55)]}
    )
    monkeypatch.setattr(mi.yf, "download", lambda *args, **kwargs: multi)
    qm_multi = mi.compute_quant_metrics("AAPL")
    assert qm_multi.sma_50 is not None

    monkeypatch.setattr(mi.yf, "download", lambda *args, **kwargs: pd.DataFrame())
    qm_empty = mi.compute_quant_metrics("AAPL")
    assert qm_empty.close is None

    class _Article:
        def __init__(self, _url):
            self.text = "good"
            self.title = "t"

        def download(self):
            return None

        def parse(self):
            return None

    class _Analyzer:
        def polarity_scores(self, _text):
            return {"compound": 0.6}

    news_mod = types.ModuleType("newspaper")
    news_mod.Article = _Article
    vader_mod = types.ModuleType("vaderSentiment.vaderSentiment")
    vader_mod.SentimentIntensityAnalyzer = _Analyzer

    monkeypatch.setitem(sys.modules, "newspaper", news_mod)
    monkeypatch.setitem(sys.modules, "vaderSentiment", types.ModuleType("vaderSentiment"))
    monkeypatch.setitem(sys.modules, "vaderSentiment.vaderSentiment", vader_mod)
    sent = mi.analyze_sentiment("http://x")
    assert isinstance(sent, SentimentPayload)
    assert sent.sentiment == "positive"


def test_market_intel_sentiment_import_fallback(monkeypatch):
    original_import = builtins.__import__

    def _import(name, *args, **kwargs):
        if name in ("newspaper", "vaderSentiment.vaderSentiment"):
            raise ImportError("forced")
        return original_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _import)
    sent = mi.analyze_sentiment("http://x")
    assert sent.sentiment == "neutral"
    assert sent.error is not None


def test_market_intel_finite_and_bearish_branches(monkeypatch):
    assert mi._finite_or_none("bad") is None
    assert mi._finite_or_none(float("inf")) is None

    bearish = mi._rule_based_verdict(
        ticker="BTC-USD",
        market_data=MarketDataPayload.model_validate({"ticker": "BTC-USD", "pe_ratio": 50}),
        quant_metrics=QuantMetricsPayload.model_validate(
            {"ticker": "BTC-USD", "close": 10, "sma_50": 20, "volatility": 0.9}
        ),
        sentiment=SentimentPayload.model_validate({"sentiment": "negative", "score": -0.7}),
        model_version="v1",
    )
    assert bearish.stance == "bearish"


def test_market_intel_llm_verdict_parsing(monkeypatch):
    class _FakeLLMRouter:
        def __init__(self, _cfg):
            pass

        async def chat(self, **_kwargs):
            return types.SimpleNamespace(
                provider="ollama",
                text='{"stance":"bullish","confidence":0.8,"headline":"h","rationale":["r1"]}',
            )

    monkeypatch.setattr(mi, "LLMRouter", _FakeLLMRouter)
    cfg = SecureConfig.from_env().with_overrides(llm_provider="ollama")
    verdict = asyncio.run(
        mi._llm_verdict(
            ticker="BTC-USD",
            market_data=MarketDataPayload.model_validate({"ticker": "BTC-USD"}),
            quant_metrics=QuantMetricsPayload.model_validate({"ticker": "BTC-USD"}),
            sentiment=None,
            config=cfg,
        )
    )
    assert verdict.stance == "bullish"
    assert verdict.model_provider == "ollama"


def test_run_market_intel_llm_success_path(monkeypatch):
    monkeypatch.setattr(
        mi,
        "fetch_market_data",
        lambda ticker: {"ticker": ticker, "price": 1.0, "pe_ratio": 10.0},
    )
    monkeypatch.setattr(
        mi,
        "compute_quant_metrics",
        lambda ticker, period="1y": {"ticker": ticker, "close": 2.0, "sma_50": 1.0, "volatility": 0.1},
    )

    async def _good_llm(**_kwargs):
        from hedgevision.models import StructuredVerdictPayload

        return StructuredVerdictPayload.model_validate(
            {
                "stance": "bullish",
                "confidence": 0.8,
                "headline": "h",
                "rationale": ["r1"],
                "model_version": "v1",
                "model_provider": "ollama",
            }
        )

    monkeypatch.setattr(mi, "_llm_verdict", _good_llm)
    cfg = SecureConfig.from_env().with_overrides(llm_provider="ollama", llm_model="llama3.2")
    out = asyncio.run(
        mi.run_market_intel(
            "BTC-USD",
            use_llm=True,
            llm_provider="ollama",
            llm_model="llama3.2",
            config=cfg,
        )
    )
    assert out["verdict"]["model_provider"] == "ollama"


def test_run_market_intel_cpu_provider_path(monkeypatch):
    monkeypatch.setattr(
        mi,
        "fetch_market_data",
        lambda ticker: {"ticker": ticker, "price": 100.0, "pe_ratio": 15.0},
    )
    monkeypatch.setattr(
        mi,
        "compute_quant_metrics",
        lambda ticker, period="1y": {"ticker": ticker, "close": 110.0, "sma_50": 100.0, "volatility": 0.2},
    )
    cfg = SecureConfig.from_env().with_overrides(llm_provider="cpu", llm_model="cpu-linear-v1")
    out = asyncio.run(mi.run_market_intel("BTC-USD", use_llm=True, config=cfg))
    assert out["verdict"]["model_provider"] == "cpu"


def test_daily_pipeline_loader_internal_branches(monkeypatch):
    # Missing script path branch
    monkeypatch.setattr("pathlib.Path.exists", lambda _self: False)
    with pytest.raises(FileNotFoundError):
        daily_pipeline._load_daily_module()

    # Spec failure branch
    monkeypatch.setattr("pathlib.Path.exists", lambda _self: True)
    monkeypatch.setattr(importlib.util, "spec_from_file_location", lambda *_args, **_kwargs: None)
    with pytest.raises(RuntimeError):
        daily_pipeline._load_daily_module()

    # Success branch with fake module execution
    class _Loader:
        def create_module(self, _spec):
            return None

        def exec_module(self, module):
            async def _main():
                return True

            module.main = _main

    spec = importlib.util.spec_from_loader("fake_daily_mod", _Loader())
    monkeypatch.setattr(importlib.util, "spec_from_file_location", lambda *_args, **_kwargs: spec)
    mod = daily_pipeline._load_daily_module()
    assert hasattr(mod, "main")
