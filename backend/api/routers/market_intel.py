"""Market intelligence endpoints backed by HedgeVision core library."""

from __future__ import annotations

from fastapi import APIRouter, Query

from hedgevision.config import SecureConfig
from hedgevision.core.market_intel import run_market_intel
from hedgevision.models import MarketIntelResponsePayload

router = APIRouter(prefix="/market-intel", tags=["market-intel"])


@router.get("/verdict/{ticker}")
async def get_structured_verdict(
    ticker: str,
    period: str = Query("1y", description="History period for quant metrics"),
    news_url: str | None = Query(None, description="Optional news article URL"),
    use_llm: bool = Query(False, description="Use configured LLM provider for verdict"),
    provider: str | None = Query(
        None, description="Provider override: rules|openai|anthropic|ollama|cpu"
    ),
    model: str | None = Query(None, description="LLM model override"),
) -> MarketIntelResponsePayload:
    """Return structured bullish/bearish verdict card payload."""
    cfg = SecureConfig.from_env()
    if provider or model:
        cfg = cfg.with_overrides(llm_provider=provider, llm_model=model)

    raw = await run_market_intel(
        ticker=ticker,
        news_url=news_url,
        period=period,
        use_llm=use_llm,
        llm_provider=cfg.llm_provider,
        llm_model=cfg.llm_model,
        config=cfg,
    )
    return MarketIntelResponsePayload.model_validate(raw)
