"""Asset management service - handles asset lifecycle and metadata."""

import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List

from supabase import create_client

from ..utils.config import config

logger = logging.getLogger(__name__)


class AssetService:
    """Manages asset metadata, synchronization, and status tracking."""

    def __init__(self, supabase_client=None):
        self.supabase = supabase_client or create_client(
            config.get("SUPABASE_URL"), config.get("SUPABASE_KEY")
        )

    async def sync_assets_from_hedgevision(self) -> Dict[str, Any]:
        """Sync HedgeVision assets to Supabase assets table."""
        logger.info("Syncing HedgeVision assets to Supabase")

        try:
            from scripts.setup.populate_assets import AssetStandardizer

            standardizer = AssetStandardizer(supabase_client=self.supabase)
            standardized_assets = standardizer.standardize_all_assets()
            results = await standardizer.populate_supabase(standardized_assets)

            logger.info(f"Asset sync complete: {results}")
            return results

        except Exception as e:
            logger.error(f"Asset sync failed: {e}")
            return {"error": str(e)}

    async def get_active_assets(self) -> List[Dict[str, Any]]:
        """Get all active assets from Supabase."""
        try:
            response = (
                self.supabase.table("assets").select("*").eq("is_active", 1).execute()
            )
            return response.data
        except Exception as e:
            logger.error(f"Failed to get active assets: {e}")
            return []

    async def get_assets_needing_data(
        self, days_stale: int = 2
    ) -> List[Dict[str, Any]]:
        """Get assets that need fresh data."""
        try:
            stale_threshold = datetime.now() - timedelta(days=days_stale)

            response = (
                self.supabase.table("assets")
                .select("*")
                .eq("is_active", 1)
                .or_(
                    f"last_price_update.is.null,last_price_update.lt.{stale_threshold.isoformat()}"
                )
                .execute()
            )

            return response.data
        except Exception as e:
            logger.error(f"Failed to get stale assets: {e}")
            return []

    async def update_asset_last_updated(self, asset_ids: List[int]):
        """Update last_price_update timestamp for processed assets."""
        try:
            for asset_id in asset_ids:
                self.supabase.table("assets").update(
                    {"last_price_update": datetime.now().isoformat()}
                ).eq("id", asset_id).execute()
        except Exception as e:
            logger.error(f"Failed to update asset timestamps: {e}")

    async def update_quality_score(self, asset_id: int, quality_score: float):
        """Update asset data quality score."""
        try:
            self.supabase.table("assets").update(
                {"data_quality_score": quality_score}
            ).eq("id", asset_id).execute()
        except Exception as e:
            logger.error(f"Failed to update quality score for asset {asset_id}: {e}")
