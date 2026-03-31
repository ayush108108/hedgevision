"""
Asset Repository

Handles all database operations related to assets.
Provides clean separation between data access and business logic.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from api.services.db_health_models import Asset

from supabase import Client

from .base_repository import BaseRepository

logger = logging.getLogger(__name__)


class AssetRepository(BaseRepository[Asset]):
    """Repository for asset-related database operations."""

    def __init__(self, supabase_client: Client):
        """
        Initialize asset repository.

        Args:
            supabase_client: Authenticated Supabase client
        """
        super().__init__(supabase_client, "assets")

    def get_active_assets(self) -> List[Dict[str, Any]]:
        """
        Get all active assets.

        Returns:
            List of active asset dicts
        """
        try:
            response = (
                self.supabase.table(self.table_name)
                .select("*")
                .eq("is_active", 1)
                .execute()
            )

            return response.data if response.data else []

        except Exception as e:
            self.logger.error(f"Error getting active assets: {e}")
            return []

    def get_by_symbol(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get asset by symbol.

        Args:
            symbol: Asset symbol (e.g., 'AAPL.US')

        Returns:
            Asset dict or None if not found
        """
        return self.find_one_by({"symbol": symbol})

    def get_by_exchange(
        self, exchange: str, active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get assets by exchange.

        Args:
            exchange: Exchange identifier (NYSE, NASDAQ, etc.)
            active_only: If True, only return active assets

        Returns:
            List of asset dicts
        """
        filters = {"exchange": exchange}
        if active_only:
            filters["is_active"] = True

        return self.find_by(filters, order_by="symbol", ascending=True)

    def get_by_asset_type(
        self, asset_type: str, active_only: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get assets by type.

        Args:
            asset_type: Asset type (stock, etf, crypto, forex)
            active_only: If True, only return active assets

        Returns:
            List of asset dicts
        """
        filters = {"asset_type": asset_type}
        if active_only:
            filters["is_active"] = True

        return self.find_by(filters, order_by="symbol", ascending=True)

    def get_stale_assets(self, stale_threshold_hours: int = 48) -> List[Dict[str, Any]]:
        """
        Get assets that haven't been updated recently.

        Args:
            stale_threshold_hours: Hours after which an asset is considered stale

        Returns:
            List of stale asset dicts
        """
        try:
            from datetime import timedelta

            stale_threshold = datetime.utcnow() - timedelta(hours=stale_threshold_hours)

            response = (
                self.supabase.table(self.table_name)
                .select("*")
                .eq("is_active", 1)
                .or_(
                    f"last_price_update.is.null,last_price_update.lt.{stale_threshold.isoformat()}"
                )
                .execute()
            )

            return response.data if response.data else []

        except Exception as e:
            self.logger.error(f"Error getting stale assets: {e}")
            return []

    def update_last_price_update(self, symbol: str) -> bool:
        """
        Update last_price_update timestamp for an asset.

        Args:
            symbol: Asset symbol

        Returns:
            True if updated, False on failure
        """
        try:
            self.supabase.table(self.table_name).update(
                {"last_price_update": datetime.utcnow().isoformat()}
            ).eq("symbol", symbol).execute()

            return True

        except Exception as e:
            self.logger.error(f"Error updating last_price_update for {symbol}: {e}")
            return False

    def update_quality_score(self, asset_id: int, quality_score: float) -> bool:
        """
        Update data quality score for an asset.

        Args:
            asset_id: Asset ID
            quality_score: Quality score (0-100)

        Returns:
            True if updated, False on failure
        """
        try:
            self.supabase.table(self.table_name).update(
                {"data_quality_score": quality_score}
            ).eq("id", asset_id).execute()

            return True

        except Exception as e:
            self.logger.error(f"Error updating quality score for asset {asset_id}: {e}")
            return False

    def get_by_provider_symbol(
        self, provider: str, provider_symbol: str
    ) -> Optional[Dict[str, Any]]:
        """
        Get asset by provider-specific symbol.

        Args:
            provider: Provider name (tiingo, polygon, binance, etc.)
            provider_symbol: Provider's symbol format

        Returns:
            Asset dict or None if not found
        """
        try:
            column_map = {
                "tiingo": "tiingo_symbol",
                "polygon": "polygon_symbol",
                "binance": "binance_symbol",
                "finnhub": "finnhub_symbol",
                "fmp": "fmp_symbol",
            }

            column = column_map.get(provider.lower())
            if not column:
                self.logger.warning(f"Unknown provider: {provider}")
                return None

            response = (
                self.supabase.table(self.table_name)
                .select("*")
                .eq(column, provider_symbol)
                .single()
                .execute()
            )

            return response.data if response.data else None

        except Exception as e:
            self.logger.error(
                f"Error getting asset by {provider} symbol {provider_symbol}: {e}"
            )
            return None

    def get_assets_by_symbols(self, symbols: List[str]) -> List[Dict[str, Any]]:
        """
        Get multiple assets by symbols.

        Args:
            symbols: List of asset symbols

        Returns:
            List of asset dicts
        """
        try:
            response = (
                self.supabase.table(self.table_name)
                .select("*")
                .in_("symbol", symbols)
                .execute()
            )

            return response.data if response.data else []

        except Exception as e:
            self.logger.error(f"Error getting assets by symbols: {e}")
            return []

    def to_entity(self, data: Dict[str, Any]) -> Asset:
        """
        Convert database dict to Asset entity.

        Args:
            data: Raw database record

        Returns:
            Asset entity object
        """
        return Asset(**data)

    def to_dict(self, entity: Asset) -> Dict[str, Any]:
        """
        Convert Asset entity to database dict.

        Args:
            entity: Asset entity object

        Returns:
            Database-compatible dict
        """
        # Using Pydantic's dict() method if Asset is a Pydantic model
        if hasattr(entity, "dict"):
            return entity.dict()
        # Fallback to __dict__ for regular classes
        return entity.__dict__
