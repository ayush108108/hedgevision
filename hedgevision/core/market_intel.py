"""Model-agnostic market intelligence tools and structured verdict logic."""

from __future__ import annotations

import json
import math
from typing import Any

import pandas as pd
import yfinance as yf

from hedgevision.config import SecureConfig
from hedgevision.llm import LLMRouter
from hedgevision.models import (
    MarketDataPayload,
    MarketIntelResponsePayload,
    QuantMetricsPayload,
    SentimentPayload,
    StructuredVerdictPayload,
    validate_json_object,
)


def _finite_or_none(value: Any) -> float | None:
    try:
        num = float(value)
    except Exception:
        return None
    if math.isnan(num) or math.isinf(num):
        return None
    return num


def fetch_market_data(ticker: str) -> MarketDataPayload:
    stock = yf.Ticker(ticker)
    merged: dict[str, Any] = {}
    try:
        fast = stock.fast_info or {}
        if isinstance(fast, dict):
            merged.update(fast)
    except Exception:
        pass
    try:
        info = stock.info or {}
        if isinstance(info, dict):
            merged.update(info)
    except Exception:
        pass

    payload = {
        "ticker": ticker,
        "price": _finite_or_none(
            merged.get("currentPrice")
            or merged.get("regularMarketPrice")
            or merged.get("lastPrice")
            or merged.get("last_close")
        ),
        "pe_ratio": _finite_or_none(merged.get("trailingPE")),
        "eps": _finite_or_none(merged.get("trailingEps")),
        "revenue_growth": _finite_or_none(merged.get("revenueGrowth")),
    }
    return MarketDataPayload.model_validate(payload)


def analyze_sentiment(url: str) -> SentimentPayload:
    """Analyze sentiment using optional newspaper3k + VADER dependencies."""
    try:
        from newspaper import Article  # type: ignore
        from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer  # type: ignore
    except Exception as e:
        return SentimentPayload.model_validate(
            {
                "sentiment": "neutral",
                "score": 0.0,
                "title": None,
                "error": f"Sentiment extras unavailable: {e}",
            }
        )

    article = Article(url)
    article.download()
    article.parse()
    analyzer = SentimentIntensityAnalyzer()
    scores = analyzer.polarity_scores(article.text or "")
    compound = float(scores.get("compound", 0.0))
    if compound > 0.05:
        sentiment = "positive"
    elif compound < -0.05:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return SentimentPayload.model_validate(
        {"sentiment": sentiment, "score": compound, "title": article.title}
    )


def compute_quant_metrics(ticker: str, period: str = "1y") -> QuantMetricsPayload:
    data = yf.download(ticker, period=period, auto_adjust=True, progress=False)
    if data is None or len(data) == 0 or "Close" not in data:
        return QuantMetricsPayload.model_validate(
            {
                "ticker": ticker,
                "sma_50": None,
                "ema_20": None,
                "volatility": None,
                "close": None,
            }
        )

    close = data["Close"].astype(float)
    if isinstance(close, pd.DataFrame):
        # yfinance may return a 1-column DataFrame for some symbols.
        close = close.iloc[:, 0]
    sma_50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else float("nan")
    ema_20 = close.ewm(span=20, adjust=False).mean().iloc[-1] if len(close) >= 20 else float("nan")
    volatility = close.pct_change().std() * (252**0.5)
    current = close.iloc[-1]
    return QuantMetricsPayload.model_validate(
        {
            "ticker": ticker,
            "sma_50": _finite_or_none(sma_50),
            "ema_20": _finite_or_none(ema_20),
            "volatility": _finite_or_none(volatility),
            "close": _finite_or_none(current),
        }
    )


def _rule_based_verdict(
    *,
    ticker: str,
    market_data: MarketDataPayload,
    quant_metrics: QuantMetricsPayload,
    sentiment: SentimentPayload | None,
    model_version: str,
) -> StructuredVerdictPayload:
    close = quant_metrics.close
    sma_50 = quant_metrics.sma_50
    volatility = quant_metrics.volatility or 0.0
    pe_ratio = market_data.pe_ratio
    sentiment_label = (sentiment.sentiment if sentiment else "neutral")

    score = 0.0
    rationale: list[str] = []

    if isinstance(close, float) and isinstance(sma_50, float) and not math.isnan(sma_50):
        if close > sma_50:
            score += 0.4
            rationale.append("Price is above 50-day SMA (bullish trend).")
        else:
            score -= 0.4
            rationale.append("Price is below 50-day SMA (weak trend).")

    if isinstance(pe_ratio, (int, float)):
        if pe_ratio < 20:
            score += 0.2
            rationale.append("Valuation is moderate (P/E below 20).")
        elif pe_ratio > 35:
            score -= 0.2
            rationale.append("Valuation is elevated (P/E above 35).")

    if sentiment_label == "positive":
        score += 0.2
        rationale.append("News sentiment is positive.")
    elif sentiment_label == "negative":
        score -= 0.2
        rationale.append("News sentiment is negative.")

    if isinstance(volatility, (int, float)):
        if volatility > 0.6:
            score -= 0.2
            rationale.append("Volatility is high; risk-adjusted outlook reduced.")
        elif volatility < 0.25:
            score += 0.1
            rationale.append("Volatility is moderate; signal stability is higher.")

    if score >= 0.25:
        stance = "bullish"
        headline = f"{ticker}: Bullish setup with trend confirmation"
    elif score <= -0.25:
        stance = "bearish"
        headline = f"{ticker}: Bearish setup with downside risk"
    else:
        stance = "neutral"
        headline = f"{ticker}: Mixed signal, no strong directional edge"

    confidence = min(0.95, max(0.5, 0.5 + abs(score)))
    return StructuredVerdictPayload.model_validate(
        {
            "stance": stance,
            "confidence": round(confidence, 3),
            "headline": headline,
            "rationale": (rationale[:3] if rationale else ["Insufficient evidence for directional conviction."]),
            "model_version": model_version,
            "model_provider": "rules",
        }
    )


async def _llm_verdict(
    *,
    ticker: str,
    market_data: MarketDataPayload,
    quant_metrics: QuantMetricsPayload,
    sentiment: SentimentPayload | None,
    config: SecureConfig,
) -> StructuredVerdictPayload:
    router = LLMRouter(config)
    prompt = (
        "You are a quantitative analyst. Respond with strict JSON containing keys: "
        "stance (bullish|bearish|neutral), confidence (0-1), headline, rationale (array of max 3 items)."
    )
    payload = {
        "ticker": ticker,
        "market_data": market_data.model_dump(),
        "quant_metrics": quant_metrics.model_dump(),
        "sentiment": sentiment.model_dump() if sentiment else None,
        "model_version": config.model_version,
    }
    response = await router.chat(system_prompt=prompt, user_payload=payload)
    parsed = validate_json_object(json.loads(response.text))
    parsed["model_version"] = config.model_version
    parsed["model_provider"] = response.provider
    return StructuredVerdictPayload.model_validate(parsed)


def _cpu_bound_verdict(
    *,
    ticker: str,
    market_data: MarketDataPayload,
    quant_metrics: QuantMetricsPayload,
    sentiment: SentimentPayload | None,
    config: SecureConfig,
) -> StructuredVerdictPayload:
    """
    CPU-local deterministic model.
    Keeps inference fully local and bounded without external provider calls.
    """
    close = quant_metrics.close
    sma_50 = quant_metrics.sma_50
    volatility = quant_metrics.volatility
    pe_ratio = market_data.pe_ratio
    sentiment_score = float(sentiment.score) if sentiment else 0.0

    trend = 0.0
    if (
        isinstance(close, float)
        and isinstance(sma_50, float)
        and math.isfinite(sma_50)
        and sma_50 != 0.0
    ):
        trend = (close - sma_50) / sma_50

    valuation = 0.0
    if isinstance(pe_ratio, float) and math.isfinite(pe_ratio):
        if pe_ratio < 18:
            valuation = 0.18
        elif pe_ratio > 38:
            valuation = -0.18

    risk_penalty = float(volatility) if isinstance(volatility, float) and math.isfinite(volatility) else 0.35
    # Compact local score: positive trend + sentiment, penalize high vol.
    logit = (2.4 * trend) + (0.9 * sentiment_score) + valuation - (0.7 * risk_penalty)
    prob = 1.0 / (1.0 + math.exp(-logit))

    if prob > 0.58:
        stance = "bullish"
    elif prob < 0.42:
        stance = "bearish"
    else:
        stance = "neutral"

    confidence = min(0.95, max(0.5, 0.5 + abs(prob - 0.5) * 1.8))
    rationale = [
        f"CPU-local model backend: {config.local_ml_backend}",
        f"Trend delta vs SMA50: {trend:.3f}, volatility: {risk_penalty:.3f}",
        f"Sentiment score input: {sentiment_score:.3f}",
    ]
    if config.local_ml_model_path:
        rationale[0] = f"{rationale[0]} (model: {config.local_ml_model_path})"

    return StructuredVerdictPayload.model_validate(
        {
            "stance": stance,
            "confidence": round(confidence, 3),
            "headline": f"{ticker}: CPU-local signal ({stance})",
            "rationale": rationale[:3],
            "model_version": config.model_version,
            "model_provider": "cpu",
        }
    )


async def run_market_intel(
    ticker: str,
    *,
    news_url: str | None = None,
    period: str = "1y",
    use_llm: bool = False,
    llm_provider: str | None = None,
    llm_model: str | None = None,
    config: SecureConfig | None = None,
) -> dict[str, Any]:
    cfg = config or SecureConfig.from_env()
    if llm_provider or llm_model:
        cfg = cfg.with_overrides(llm_provider=llm_provider, llm_model=llm_model)

    market_data = MarketDataPayload.model_validate(fetch_market_data(ticker))
    quant_metrics = QuantMetricsPayload.model_validate(compute_quant_metrics(ticker, period=period))
    sentiment = (
        SentimentPayload.model_validate(analyze_sentiment(news_url)) if news_url else None
    )

    provider_is_external = cfg.llm_provider in {"openai", "anthropic"}
    llm_allowed = (
        use_llm
        and cfg.llm_provider != "rules"
        and (not provider_is_external or cfg.enable_external_llm)
    )

    if use_llm and cfg.llm_provider == "cpu":
        verdict = _cpu_bound_verdict(
            ticker=ticker,
            market_data=market_data,
            quant_metrics=quant_metrics,
            sentiment=sentiment,
            config=cfg,
        )
    elif llm_allowed:
        try:
            verdict = await _llm_verdict(
                ticker=ticker,
                market_data=market_data,
                quant_metrics=quant_metrics,
                sentiment=sentiment,
                config=cfg,
            )
        except Exception:
            verdict = _rule_based_verdict(
                ticker=ticker,
                market_data=market_data,
                quant_metrics=quant_metrics,
                sentiment=sentiment,
                model_version=cfg.model_version,
            )
    else:
        verdict = _rule_based_verdict(
            ticker=ticker,
            market_data=market_data,
            quant_metrics=quant_metrics,
            sentiment=sentiment,
            model_version=cfg.model_version,
        )

    response = MarketIntelResponsePayload.model_validate(
        {
            "ticker": ticker,
            "market_data": market_data,
            "quant_metrics": quant_metrics,
            "sentiment": sentiment,
            "verdict": verdict,
        }
    )
    return response.model_dump()
