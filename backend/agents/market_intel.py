#!/usr/bin/env python3
"""
Market Intelligence Multi-Agent tools and simple orchestrator.

Provides:
- LangChain @tool functions for market data, sentiment, quant metrics, strategy.
- LangGraph agent composition (optional if OPENAI_API_KEY available).
- Sequential fallback runner that works without LLMs.

Environment:
- Reads `OPENAI_API_KEY` from env (optionally loads backend/api/.env).
"""

from __future__ import annotations

import os
import json
import asyncio
from dataclasses import dataclass
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# Load backend/api/.env if present for OPENAI_API_KEY convenience
try:
    from pathlib import Path

    env_path = Path(__file__).resolve().parents[1] / "api" / ".env"
    if env_path.exists():
        load_dotenv(env_path)
except Exception:
    pass


def _safe_import(name: str):
    try:
        module = __import__(name)
        return module
    except Exception as e:
        raise RuntimeError(f"Missing required dependency: {name}. Please install it. Original error: {e}")


# Third-party libs (imported lazily in tools where practical)
import yfinance as yf

try:
    from langchain.tools import tool
except Exception:
    # Lightweight fallback to keep this module usable without LangChain.
    def tool(func):  # type: ignore
        func.invoke = lambda kwargs: func(**kwargs)  # type: ignore[attr-defined]
        return func


@tool
def fetch_market_data(ticker: str) -> dict:
    """Fetch real-time stock data like price, P/E, EPS, revenue growth.

    Returns keys: price, pe_ratio, eps, revenue_growth.
    """
    stock = yf.Ticker(ticker)
    info = {}
    try:
        # Try fast_info for basic live-ish fields
        fast = getattr(stock, "fast_info", {}) or {}
        info.update(fast if isinstance(fast, dict) else {})
    except Exception:
        pass
    try:
        base_info = stock.info or {}
        info.update(base_info)
    except Exception:
        # yfinance info can fail if Yahoo blocks; tolerate gracefully
        base_info = {}

    price = info.get("currentPrice") or info.get("lastPrice") or info.get("last_close") or info.get("regularMarketPrice")
    pe_ratio = info.get("trailingPE")
    eps = info.get("trailingEps")
    revenue_growth = info.get("revenueGrowth")

    return {"price": price, "pe_ratio": pe_ratio, "eps": eps, "revenue_growth": revenue_growth}


@tool
def analyze_sentiment(url: str) -> dict:
    """Analyze sentiment from a news article URL using VADER.

    Returns keys: sentiment, score, title (if parsed).
    """
    # newspaper3k and vader are optional deps; import when used
    np3k = _safe_import("newspaper")
    vsent = _safe_import("vaderSentiment.vaderSentiment")

    Article = getattr(np3k, "Article")
    SentimentIntensityAnalyzer = getattr(vsent, "SentimentIntensityAnalyzer")

    article = Article(url)
    article.download()
    article.parse()
    analyzer = SentimentIntensityAnalyzer()
    scores = analyzer.polarity_scores(article.text or "")
    comp = scores.get("compound", 0.0)
    sentiment = "positive" if comp > 0.05 else ("negative" if comp < -0.05 else "neutral")
    return {"sentiment": sentiment, "score": comp, "title": getattr(article, "title", None)}


@tool
def compute_quant_metrics(ticker: str, period: str = "1y") -> dict:
    """Compute simple technicals: SMA(50), EMA(20), annualized volatility.

    Returns keys: sma_50, ema_20, volatility.
    """
    data = yf.download(ticker, period=period, auto_adjust=True, progress=False)
    if data is None or len(data) == 0 or "Close" not in data:
        return {"sma_50": None, "ema_20": None, "volatility": None}

    close = data["Close"].astype(float)
    sma_50 = close.rolling(50).mean().iloc[-1] if len(close) >= 50 else float("nan")
    ema_20 = close.ewm(span=20, adjust=False).mean().iloc[-1] if len(close) >= 20 else float("nan")
    volatility = close.pct_change().std() * (252 ** 0.5)
    return {"sma_50": float(sma_50), "ema_20": float(ema_20), "volatility": float(volatility)}


@tool
def generate_strategy(insights: dict) -> str:
    """Generate Buy/Sell/Hold decision from combined insights.

    Rule-based fallback used when no LLM; conservative defaults.
    """
    sentiment = insights.get("sentiment")
    pe_ratio = insights.get("pe_ratio")
    volatility = insights.get("volatility") or 0.0

    if sentiment == "positive" and (isinstance(pe_ratio, (int, float)) and pe_ratio < 20):
        return "Buy"
    if isinstance(volatility, (int, float)) and volatility > 0.3:
        return "Hold - High risk"
    return "Sell"


# Optional: LangGraph agent composition
def build_agents():
    """Build LangGraph agents using LangChain tools. Requires langgraph + langchain_openai."""
    # Import only if available
    try:
        from langchain_openai import ChatOpenAI
        from langgraph.prebuilt import create_react_agent
    except Exception as e:
        raise RuntimeError(
            "LangGraph or LangChain OpenAI not installed. Install 'langgraph' and 'langchain-openai'."
        ) from e

    model = ChatOpenAI(model="gpt-4o", api_key=os.getenv("OPENAI_API_KEY"))

    market_data_agent = create_react_agent(
        model=model,
        tools=[fetch_market_data],
        state_modifier="You are a market data expert. Fetch and return stock fundamentals.",
    )

    sentiment_agent = create_react_agent(
        model=model,
        tools=[analyze_sentiment],
        state_modifier="You analyze news sentiment. If URL not provided, ask the user for one.",
    )

    quant_agent = create_react_agent(
        model=model,
        tools=[compute_quant_metrics],
        state_modifier="You compute technical indicators for trends and risk.",
    )

    strategy_agent = create_react_agent(
        model=model,
        tools=[generate_strategy],
        state_modifier="You provide investment recommendations using the provided insights.",
    )

    return {
        "model": model,
        "market_data_agent": market_data_agent,
        "sentiment_agent": sentiment_agent,
        "quant_agent": quant_agent,
        "strategy_agent": strategy_agent,
    }


@dataclass
class MarketIntelResult:
    ticker: str
    market_data: Dict[str, Any]
    sentiment: Optional[Dict[str, Any]]
    quant: Dict[str, Any]
    decision: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "market_data": self.market_data,
            "sentiment": self.sentiment,
            "quant": self.quant,
            "decision": self.decision,
        }


def run_sequential(ticker: str, news_url: Optional[str] = None, period: str = "1y") -> MarketIntelResult:
    """Run a simple sequential pipeline without requiring LLM routing.

    - Always fetch market data and quant metrics
    - If news_url provided, analyze sentiment; else neutral
    - Generate rule-based strategy
    """
    md = fetch_market_data.invoke({"ticker": ticker})  # LangChain @tool signature expects dict
    qm = compute_quant_metrics.invoke({"ticker": ticker, "period": period})

    sent = None
    if news_url:
        try:
            sent = analyze_sentiment.invoke({"url": news_url})
        except Exception as e:
            sent = {"sentiment": "neutral", "score": 0.0, "error": str(e)}
    else:
        sent = {"sentiment": "neutral", "score": 0.0}

    insights = {
        "sentiment": sent.get("sentiment"),
        "pe_ratio": md.get("pe_ratio"),
        "volatility": qm.get("volatility"),
    }
    decision = generate_strategy.invoke({"insights": insights})

    return MarketIntelResult(
        ticker=ticker, market_data=md, sentiment=sent, quant=qm, decision=decision
    )


async def run_with_router(
    ticker: str, news_url: Optional[str] = None, period: str = "1y", use_llm: bool = False
) -> Dict[str, Any]:
    """BYOK-compatible verdict runner using the hardened hedgevision core module."""
    from hedgevision.core.market_intel import run_market_intel

    return await run_market_intel(
        ticker=ticker,
        news_url=news_url,
        period=period,
        use_llm=use_llm,
    )


def _main_cli():
    import argparse

    parser = argparse.ArgumentParser(description="Run Market Intelligence pipeline")
    parser.add_argument("--ticker", required=True, help="Ticker symbol, e.g. AAPL")
    parser.add_argument("--url", required=False, help="News article URL for sentiment")
    parser.add_argument("--period", default="1y", help="History period for quant metrics")
    parser.add_argument("--use-llm", action="store_true", help="Use BYOK LLM router for verdict")
    parser.add_argument("--json", action="store_true", help="Print JSON output")
    args = parser.parse_args()

    if args.use_llm:
        result = asyncio.run(run_with_router(args.ticker, args.url, args.period, use_llm=True))
        print(json.dumps(result, indent=2))
    else:
        result = run_sequential(args.ticker, args.url, args.period)
        if args.json:
            print(json.dumps(result.to_dict(), indent=2))
        else:
            print(f"Ticker: {result.ticker}")
            print(f"Market: {result.market_data}")
            print(f"Sentiment: {result.sentiment}")
            print(f"Quant: {result.quant}")
            print(f"Decision: {result.decision}")


if __name__ == "__main__":
    _main_cli()
