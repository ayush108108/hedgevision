"""
News API Router

Endpoints for fetching and managing market news with sentiment analysis.
"""

import logging
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from api.services.news_service import get_news_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/news", tags=["news"])


class NewsArticle(BaseModel):
    """News article response model."""

    id: str
    title: str
    summary: str
    source: str
    url: str
    timestamp: str
    sentiment: str
    sentiment_score: float
    sentiment_scores: dict
    relatedAssets: List[str] = Field(default_factory=list)


class NewsResponse(BaseModel):
    """News feed response."""

    articles: List[NewsArticle]
    total: int
    sources: List[str]


@router.get("/", response_model=NewsResponse)
async def get_news(
    sources: Optional[str] = Query(None, description="Comma-separated list of sources"),
    sentiment: Optional[str] = Query(
        None, description="Filter by sentiment: positive, negative, neutral"
    ),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of articles"),
):
    """
    Get market news with sentiment analysis.

    Args:
        sources: Comma-separated source names (bloomberg, reuters, cnbc, etc.)
        sentiment: Filter by sentiment
        limit: Maximum articles to return

    Returns:
        News feed with articles and metadata
    """
    try:
        news_service = get_news_service()

        # Parse sources
        source_list = None
        if sources:
            source_list = [s.strip() for s in sources.split(",")]

        # Fetch news
        articles = await news_service.fetch_news(
            sources=source_list, limit=limit, sentiment_filter=sentiment
        )

        # Convert datetime to string for JSON serialization
        for article in articles:
            article["timestamp"] = article["timestamp"].isoformat()

        return NewsResponse(
            articles=articles,
            total=len(articles),
            sources=source_list or ["all"],
        )

    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        raise HTTPException(status_code=500, detail=f"Error fetching news: {str(e)}")


@router.get("/asset/{symbol}", response_model=NewsResponse)
async def get_asset_news(
    symbol: str,
    limit: int = Query(10, ge=1, le=50, description="Maximum number of articles"),
):
    """
    Get news articles related to a specific asset.

    Args:
        symbol: Asset ticker symbol (e.g., BTC, AAPL, SPY)
        limit: Maximum articles to return

    Returns:
        News articles mentioning the asset
    """
    try:
        news_service = get_news_service()

        articles = await news_service.get_asset_news(
            asset_symbol=symbol.upper(), limit=limit
        )

        # Convert datetime to string
        for article in articles:
            article["timestamp"] = article["timestamp"].isoformat()

        return NewsResponse(
            articles=articles, total=len(articles), sources=["filtered"]
        )

    except Exception as e:
        logger.error(f"Error fetching asset news for {symbol}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Error fetching asset news: {str(e)}"
        )


@router.post("/cache/clear")
async def clear_cache():
    """
    Clear the news cache.

    Returns:
        Success message
    """
    try:
        news_service = get_news_service()
        news_service.clear_cache()
        return {"message": "News cache cleared successfully"}

    except Exception as e:
        logger.error(f"Error clearing cache: {e}")
        raise HTTPException(status_code=500, detail=f"Error clearing cache: {str(e)}")


@router.get("/sources")
async def get_sources():
    """
    Get available news sources.

    Returns:
        List of available news sources
    """
    from api.services.news_service import NEWS_SOURCES

    return {
        "sources": list(NEWS_SOURCES.keys()),
        "total": len(NEWS_SOURCES),
    }
