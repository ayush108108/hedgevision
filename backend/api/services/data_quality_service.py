"""Data quality service - validates and scores data integrity."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import pandas as pd

from supabase import create_client

from ..utils.config import config

logger = logging.getLogger(__name__)


class DataQualityService:
    """Assesses and monitors data quality across all assets."""

    def __init__(self, supabase_client=None):
        self.supabase = supabase_client or create_client(
            config.get("SUPABASE_URL"), config.get("SUPABASE_KEY")
        )

    async def compute_quality_scores(self, assets: List[Dict]) -> Dict[str, Any]:
        """Compute data quality scores for all assets."""
        logger.info("Computing data quality scores")
        processed = 0

        for asset in assets:
            try:
                symbol, asset_id = asset["symbol"], asset["id"]
                price_data = await self._get_price_data(symbol, days=30)

                quality_score = (
                    self._calculate_quality_score(price_data) if price_data else 0.0
                )

                # Update asset quality score
                self.supabase.table("assets").update(
                    {"data_quality_score": quality_score}
                ).eq("id", asset_id).execute()

                processed += 1
            except Exception as e:
                logger.error(
                    f"Error computing quality score for {asset['symbol']}: {e}"
                )

        return {"processed": processed}

    async def get_system_status(self) -> Dict[str, Any]:
        """Get current system status and health metrics."""
        try:
            # Asset counts
            assets_response = (
                self.supabase.table("assets")
                .select("id", count="exact")
                .eq("is_active", 1)
                .execute()
            )

            # Latest correlation matrix
            latest_correlation = (
                self.supabase.table("correlation_matrix")
                .select("matrix_date", "valid_pairs_count")
                .order("matrix_date", desc=True)
                .limit(1)
                .execute()
            )

            return {
                "timestamp": datetime.now().isoformat(),
                "active_assets": assets_response.count,
                "latest_correlation_date": (
                    latest_correlation.data[0]["matrix_date"]
                    if latest_correlation.data
                    else None
                ),
                "system_health": "healthy",
            }
        except Exception as e:
            logger.error(f"Failed to get system status: {e}")
            return {
                "timestamp": datetime.now().isoformat(),
                "system_health": "error",
                "error": str(e),
            }

    async def _get_price_data(self, symbol: str, days: int) -> Optional[List[Dict]]:
        """Get price data for symbol. Uses shared utility."""
        from .shared_data_utils import get_price_data_from_db

        return await get_price_data_from_db(
            self.supabase, symbol, days, granularity="daily"
        )

    def _calculate_quality_score(self, price_data: List[Dict]) -> float:
        """Calculate comprehensive quality score (0-100)."""
        if not price_data:
            return 0.0

        try:
            expected_points = 30
            actual_points = len(price_data)
            completeness = min(actual_points / expected_points, 1.0)

            consistency_score = self._assess_consistency(price_data)

            return (completeness * 0.7 + consistency_score * 0.3) * 100
        except Exception:
            return 0.0

    def _assess_consistency(self, price_data: List[Dict]) -> float:
        """Assess data consistency (0-1 score)."""
        if len(price_data) < 2:
            return 0.0

        try:
            prices = [float(point["close"]) for point in price_data]

            # Check for invalid prices
            if any(p <= 0 for p in prices):
                return 0.0

            # Check for extreme price movements (>50% daily change)
            returns = pd.Series(prices).pct_change().dropna()
            extreme_moves = (returns.abs() > 0.5).sum()

            return max(0.0, 1.0 - (extreme_moves / len(returns)))
        except Exception:
            return 0.0
