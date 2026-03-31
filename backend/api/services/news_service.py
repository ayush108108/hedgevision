"""
News and Sentiment Analysis Service

Provides real-time market news with sentiment analysis using:
- Multiple news sources (RSS feeds, APIs)
- Sentiment analysis via VADER and optional FinBERT
- Asset correlation and impact assessment
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import asyncio
import hashlib
import os

import feedparser
import requests
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

logger = logging.getLogger(__name__)

# News source RSS feeds (free sources)
NEWS_SOURCES = {
    "bloomberg": "https://www.bloomberg.com/feed/podcast/etf-report.xml",
    "reuters": "https://www.reutersagency.com/feed/?taxonomy=best-topics&post_type=best",
    "cnbc": "https://www.cnbc.com/id/100003114/device/rss/rss.html",
    "marketwatch": "https://feeds.marketwatch.com/marketwatch/topstories/",
    "seekingalpha": "https://seekingalpha.com/market_currents.xml",
}


class NewsService:
    """Service for fetching and analyzing financial news."""

    def __init__(self, cache_ttl: int = 300):
        """
        Initialize NewsService.

        Args:
            cache_ttl: Cache time-to-live in seconds (default 5 minutes)
        """
        self.cache_ttl = cache_ttl
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        self.cache: Dict[str, Dict[str, Any]] = {}

        # Optional: Initialize FinBERT if available
        self.finbert_available = False
        try:
            from transformers import AutoTokenizer, AutoModelForSequenceClassification
            import torch

            self.finbert_tokenizer = AutoTokenizer.from_pretrained(
                "ProsusAI/finbert"
            )
            self.finbert_model = AutoModelForSequenceClassification.from_pretrained(
                "ProsusAI/finbert"
            )
            self.finbert_available = True
            logger.info("FinBERT model loaded successfully")
        except Exception as e:
            logger.info(f"FinBERT not available, using VADER only: {e}")

    def _get_cache_key(self, source: str, filters: Optional[Dict] = None) -> str:
        """Generate cache key."""
        key_parts = [source]
        if filters:
            key_parts.append(str(sorted(filters.items())))
        return hashlib.md5("_".join(key_parts).encode()).hexdigest()

    def _is_cache_valid(self, cache_entry: Dict) -> bool:
        """Check if cache entry is still valid."""
        if not cache_entry:
            return False
        timestamp = cache_entry.get("timestamp", 0)
        return (datetime.now().timestamp() - timestamp) < self.cache_ttl

    async def fetch_news(
        self,
        sources: Optional[List[str]] = None,
        limit: int = 50,
        sentiment_filter: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Fetch news from multiple sources.

        Args:
            sources: List of source names to fetch from (None = all sources)
            limit: Maximum number of articles to return
            sentiment_filter: Filter by sentiment ('positive', 'negative', 'neutral', None)

        Returns:
            List of news articles with sentiment analysis
        """
        if sources is None:
            sources = list(NEWS_SOURCES.keys())

        all_articles = []

        # Fetch from each source
        for source in sources:
            cache_key = self._get_cache_key(source)
            cached = self.cache.get(cache_key)

            if cached and self._is_cache_valid(cached):
                articles = cached["data"]
            else:
                articles = await self._fetch_from_source(source)
                self.cache[cache_key] = {
                    "data": articles,
                    "timestamp": datetime.now().timestamp(),
                }

            all_articles.extend(articles)

        # Sort by timestamp (newest first)
        all_articles.sort(key=lambda x: x["timestamp"], reverse=True)

        # Apply sentiment filter
        if sentiment_filter:
            all_articles = [
                a for a in all_articles if a["sentiment"] == sentiment_filter
            ]

        # Limit results
        return all_articles[:limit]

    async def _fetch_from_source(self, source: str) -> List[Dict[str, Any]]:
        """
        Fetch articles from a single news source.

        Args:
            source: Source name

        Returns:
            List of parsed articles
        """
        url = NEWS_SOURCES.get(source)
        if not url:
            logger.warning(f"Unknown news source: {source}")
            return []

        try:
            # Fetch RSS feed
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, feedparser.parse, url)

            articles = []
            for entry in feed.entries[:20]:  # Limit per source
                article = self._parse_article(entry, source)
                if article:
                    articles.append(article)

            return articles

        except Exception as e:
            logger.error(f"Error fetching from {source}: {e}")
            return []

    def _parse_article(self, entry: Any, source: str) -> Optional[Dict[str, Any]]:
        """
        Parse RSS entry into article dict with sentiment.

        Args:
            entry: RSS feed entry
            source: Source name

        Returns:
            Parsed article dict or None
        """
        try:
            # Extract basic info
            title = entry.get("title", "")
            summary = entry.get("summary", entry.get("description", ""))
            url = entry.get("link", "")

            # Parse timestamp
            published = entry.get("published_parsed") or entry.get("updated_parsed")
            if published:
                timestamp = datetime(*published[:6])
            else:
                timestamp = datetime.now()

            # Analyze sentiment
            text = f"{title}. {summary}"
            sentiment_scores = self._analyze_sentiment(text)

            # Extract related assets from title/summary
            related_assets = self._extract_related_assets(text)

            return {
                "id": hashlib.md5(url.encode()).hexdigest()[:16],
                "title": title,
                "summary": summary[:500],  # Limit summary length
                "source": source,
                "url": url,
                "timestamp": timestamp,
                "sentiment": sentiment_scores["label"],
                "sentiment_score": sentiment_scores["score"],
                "sentiment_scores": sentiment_scores["scores"],
                "relatedAssets": related_assets,
            }

        except Exception as e:
            logger.error(f"Error parsing article: {e}")
            return None

    def _analyze_sentiment(self, text: str) -> Dict[str, Any]:
        """
        Analyze sentiment of text using VADER (and optionally FinBERT).

        Args:
            text: Text to analyze

        Returns:
            Dict with sentiment label, score, and raw scores
        """
        # VADER sentiment analysis
        vader_scores = self.sentiment_analyzer.polarity_scores(text)
        compound = vader_scores["compound"]

        # Determine label based on compound score
        if compound >= 0.05:
            label = "positive"
        elif compound <= -0.05:
            label = "negative"
        else:
            label = "neutral"

        result = {
            "label": label,
            "score": compound,
            "scores": {
                "positive": vader_scores["pos"],
                "negative": vader_scores["neg"],
                "neutral": vader_scores["neu"],
                "compound": compound,
            },
        }

        # Use FinBERT if available (more accurate for financial text)
        if self.finbert_available:
            try:
                import torch

                inputs = self.finbert_tokenizer(
                    text, return_tensors="pt", truncation=True, max_length=512
                )
                outputs = self.finbert_model(**inputs)
                probs = torch.nn.functional.softmax(outputs.logits, dim=-1)

                # FinBERT labels: [positive, negative, neutral]
                finbert_label_idx = torch.argmax(probs).item()
                finbert_labels = ["positive", "negative", "neutral"]

                # Override VADER with FinBERT for financial text
                result["label"] = finbert_labels[finbert_label_idx]
                result["score"] = probs[0][finbert_label_idx].item()
                result["scores"]["finbert"] = {
                    "positive": probs[0][0].item(),
                    "negative": probs[0][1].item(),
                    "neutral": probs[0][2].item(),
                }

            except Exception as e:
                logger.debug(f"FinBERT analysis failed, using VADER: {e}")

        return result

    def _extract_related_assets(self, text: str) -> List[str]:
        """
        Extract related asset tickers from text.

        Args:
            text: Article text

        Returns:
            List of asset tickers
        """
        # Common tickers to look for
        common_tickers = [
            "SPY",
            "QQQ",
            "DIA",
            "IWM",
            "TLT",
            "GLD",
            "SLV",
            "USO",
            "BTC",
            "ETH",
            "AAPL",
            "MSFT",
            "GOOGL",
            "AMZN",
            "TSLA",
            "NVDA",
            "META",
            "XLE",
            "XLF",
            "XLK",
            "VIX",
        ]

        # Also check for common company/asset names
        asset_keywords = {
            "bitcoin": "BTC",
            "ethereum": "ETH",
            "apple": "AAPL",
            "microsoft": "MSFT",
            "google": "GOOGL",
            "amazon": "AMZN",
            "tesla": "TSLA",
            "nvidia": "NVDA",
            "meta": "META",
            "gold": "GLD",
            "oil": "USO",
            "treasury": "TLT",
            "s&p 500": "SPY",
            "nasdaq": "QQQ",
        }

        text_lower = text.lower()
        related = []

        # Check for ticker mentions
        for ticker in common_tickers:
            if ticker in text or ticker.lower() in text_lower:
                related.append(ticker)

        # Check for keyword mentions
        for keyword, ticker in asset_keywords.items():
            if keyword in text_lower and ticker not in related:
                related.append(ticker)

        return related[:5]  # Limit to top 5 related assets

    async def get_asset_news(
        self, asset_symbol: str, limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get news articles related to a specific asset.

        Args:
            asset_symbol: Asset ticker symbol
            limit: Maximum number of articles

        Returns:
            List of related news articles
        """
        all_news = await self.fetch_news()

        # Filter for articles mentioning this asset
        related_news = [
            article
            for article in all_news
            if asset_symbol in article["relatedAssets"]
            or asset_symbol.lower() in article["title"].lower()
            or asset_symbol.lower() in article["summary"].lower()
        ]

        return related_news[:limit]

    def clear_cache(self):
        """Clear the news cache."""
        self.cache.clear()
        logger.info("News cache cleared")


# Global instance
_news_service: Optional[NewsService] = None


def get_news_service() -> NewsService:
    """Get or create global NewsService instance."""
    global _news_service
    if _news_service is None:
        _news_service = NewsService()
    return _news_service
