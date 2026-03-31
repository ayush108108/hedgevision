"""
Watchlist service for managing user watchlists.

This module provides functionality for creating, managing, and querying user watchlists
with support for personalized asset tracking.
"""

import logging
from datetime import datetime
from typing import List, Optional

from api.utils.config import config
from pydantic import BaseModel

logger = logging.getLogger(__name__)

try:
    from supabase import Client, create_client

    SUPABASE_AVAILABLE = True
except ImportError:
    SUPABASE_AVAILABLE = False
    logger.warning("Supabase client not available")


class WatchlistItem(BaseModel):
    """Watchlist item model."""

    id: Optional[int] = None
    watchlist_id: int
    asset_symbol: str
    asset_name: str
    added_at: datetime
    notes: Optional[str] = None
    alerts_enabled: bool = False
    target_correlation: Optional[float] = None


class Watchlist(BaseModel):
    """Watchlist model."""

    id: Optional[int] = None
    user_id: str
    name: str
    description: Optional[str] = None
    is_default: bool = False
    created_at: datetime
    updated_at: datetime
    items: List[WatchlistItem] = []


class CreateWatchlist(BaseModel):
    """Create watchlist request model."""

    name: str
    description: Optional[str] = None
    is_default: bool = False


class UpdateWatchlist(BaseModel):
    """Update watchlist request model."""

    name: Optional[str] = None
    description: Optional[str] = None
    is_default: Optional[bool] = None


class AddWatchlistItem(BaseModel):
    """Add item to watchlist request model."""

    asset_symbol: str
    asset_name: str
    notes: Optional[str] = None
    alerts_enabled: bool = False
    target_correlation: Optional[float] = None


class UpdateWatchlistItem(BaseModel):
    """Update watchlist item request model."""

    notes: Optional[str] = None
    alerts_enabled: Optional[bool] = None
    target_correlation: Optional[float] = None


class WatchlistService:
    """Service for managing user watchlists."""

    def __init__(self):
        if not SUPABASE_AVAILABLE:
            raise ImportError("Supabase client not available")

        self.url = config.get("SUPABASE_URL")
        self.key = config.get("SUPABASE_ANON_KEY")

        if not self.url or not self.key:
            raise ValueError("SUPABASE_URL and SUPABASE_ANON_KEY must be set")

        self.client: Client = create_client(self.url, self.key)
        logger.info("WatchlistService initialized successfully")

    async def create_watchlist(
        self, user_id: str, watchlist_data: CreateWatchlist
    ) -> Watchlist:
        """Create a new watchlist for user."""
        try:
            # If this is set as default, unset other defaults first
            if watchlist_data.is_default:
                self.client.table("watchlists").update({"is_default": False}).eq(
                    "user_id", user_id
                ).execute()

            # Create watchlist
            now = datetime.utcnow()
            watchlist_record = {
                "user_id": user_id,
                "name": watchlist_data.name,
                "description": watchlist_data.description,
                "is_default": watchlist_data.is_default,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
            }

            result = self.client.table("watchlists").insert(watchlist_record).execute()

            if not result.data:
                raise Exception("Failed to create watchlist")

            watchlist = Watchlist(**result.data[0])
            logger.info(f"Watchlist created: {watchlist.name} for user {user_id}")

            return watchlist

        except Exception as e:
            logger.error(f"Error creating watchlist: {str(e)}", exc_info=True)
            raise

    async def get_user_watchlists(self, user_id: str) -> List[Watchlist]:
        """Get all watchlists for a user."""
        try:
            # Get watchlists
            watchlists_result = (
                self.client.table("watchlists")
                .select("*")
                .eq("user_id", user_id)
                .order("is_default", desc=True)
                .order("created_at", desc=False)
                .execute()
            )

            watchlists = []

            for watchlist_data in watchlists_result.data:
                # Get items for each watchlist
                items_result = (
                    self.client.table("watchlist_items")
                    .select("*")
                    .eq("watchlist_id", watchlist_data["id"])
                    .order("added_at", desc=False)
                    .execute()
                )

                items = [WatchlistItem(**item) for item in items_result.data]

                watchlist = Watchlist(**watchlist_data, items=items)
                watchlists.append(watchlist)

            return watchlists

        except Exception as e:
            logger.error(f"Error getting user watchlists: {str(e)}", exc_info=True)
            raise

    async def get_watchlist(
        self, user_id: str, watchlist_id: int
    ) -> Optional[Watchlist]:
        """Get a specific watchlist with items."""
        try:
            # Get watchlist
            watchlist_result = (
                self.client.table("watchlists")
                .select("*")
                .eq("id", watchlist_id)
                .eq("user_id", user_id)
                .single()
                .execute()
            )

            if not watchlist_result.data:
                return None

            # Get items
            items_result = (
                self.client.table("watchlist_items")
                .select("*")
                .eq("watchlist_id", watchlist_id)
                .order("added_at", desc=False)
                .execute()
            )

            items = [WatchlistItem(**item) for item in items_result.data]

            return Watchlist(**watchlist_result.data, items=items)

        except Exception as e:
            logger.error(f"Error getting watchlist: {str(e)}", exc_info=True)
            raise

    async def update_watchlist(
        self, user_id: str, watchlist_id: int, updates: UpdateWatchlist
    ) -> Optional[Watchlist]:
        """Update a watchlist."""
        try:
            update_data = updates.dict(exclude_unset=True)
            update_data["updated_at"] = datetime.utcnow().isoformat()

            # If setting as default, unset other defaults first
            if updates.is_default:
                self.client.table("watchlists").update({"is_default": False}).eq(
                    "user_id", user_id
                ).execute()

            result = (
                self.client.table("watchlists")
                .update(update_data)
                .eq("id", watchlist_id)
                .eq("user_id", user_id)
                .execute()
            )

            if not result.data:
                return None

            logger.info(f"Watchlist updated: {watchlist_id} for user {user_id}")

            # Return updated watchlist with items
            return await self.get_watchlist(user_id, watchlist_id)

        except Exception as e:
            logger.error(f"Error updating watchlist: {str(e)}", exc_info=True)
            raise

    async def delete_watchlist(self, user_id: str, watchlist_id: int) -> bool:
        """Delete a watchlist and all its items."""
        try:
            # Delete items first
            self.client.table("watchlist_items").delete().eq(
                "watchlist_id", watchlist_id
            ).execute()

            # Delete watchlist
            result = (
                self.client.table("watchlists")
                .delete()
                .eq("id", watchlist_id)
                .eq("user_id", user_id)
                .execute()
            )

            success = len(result.data) > 0

            if success:
                logger.info(f"Watchlist deleted: {watchlist_id} for user {user_id}")

            return success

        except Exception as e:
            logger.error(f"Error deleting watchlist: {str(e)}", exc_info=True)
            raise

    async def add_item_to_watchlist(
        self, user_id: str, watchlist_id: int, item_data: AddWatchlistItem
    ) -> Optional[WatchlistItem]:
        """Add an item to a watchlist."""
        try:
            # Verify watchlist belongs to user
            watchlist = await self.get_watchlist(user_id, watchlist_id)
            if not watchlist:
                return None

            # Check if item already exists
            existing_result = (
                self.client.table("watchlist_items")
                .select("*")
                .eq("watchlist_id", watchlist_id)
                .eq("asset_symbol", item_data.asset_symbol)
                .execute()
            )

            if existing_result.data:
                logger.warning(
                    f"Item {item_data.asset_symbol} already exists in watchlist {watchlist_id}"
                )
                return WatchlistItem(**existing_result.data[0])

            # Add item
            item_record = {
                "watchlist_id": watchlist_id,
                "asset_symbol": item_data.asset_symbol,
                "asset_name": item_data.asset_name,
                "notes": item_data.notes,
                "alerts_enabled": item_data.alerts_enabled,
                "target_correlation": item_data.target_correlation,
                "added_at": datetime.utcnow().isoformat(),
            }

            result = self.client.table("watchlist_items").insert(item_record).execute()

            if not result.data:
                raise Exception("Failed to add item to watchlist")

            # Update watchlist timestamp
            self.client.table("watchlists").update(
                {"updated_at": datetime.utcnow().isoformat()}
            ).eq("id", watchlist_id).execute()

            item = WatchlistItem(**result.data[0])
            logger.info(
                f"Item added to watchlist: {item_data.asset_symbol} -> {watchlist_id}"
            )

            return item

        except Exception as e:
            logger.error(f"Error adding item to watchlist: {str(e)}", exc_info=True)
            raise

    async def update_watchlist_item(
        self, user_id: str, item_id: int, updates: UpdateWatchlistItem
    ) -> Optional[WatchlistItem]:
        """Update a watchlist item."""
        try:
            # Verify item belongs to user's watchlist
            item_result = (
                self.client.table("watchlist_items")
                .select("*, watchlists!inner(user_id)")
                .eq("id", item_id)
                .eq("watchlists.user_id", user_id)
                .single()
                .execute()
            )

            if not item_result.data:
                return None

            update_data = updates.dict(exclude_unset=True)

            result = (
                self.client.table("watchlist_items")
                .update(update_data)
                .eq("id", item_id)
                .execute()
            )

            if not result.data:
                return None

            logger.info(f"Watchlist item updated: {item_id} for user {user_id}")

            return WatchlistItem(**result.data[0])

        except Exception as e:
            logger.error(f"Error updating watchlist item: {str(e)}", exc_info=True)
            raise

    async def remove_item_from_watchlist(self, user_id: str, item_id: int) -> bool:
        """Remove an item from a watchlist."""
        try:
            # Verify item belongs to user's watchlist and get watchlist_id
            item_result = (
                self.client.table("watchlist_items")
                .select("watchlist_id, watchlists!inner(user_id)")
                .eq("id", item_id)
                .eq("watchlists.user_id", user_id)
                .single()
                .execute()
            )

            if not item_result.data:
                return False

            watchlist_id = item_result.data["watchlist_id"]

            # Delete item
            result = (
                self.client.table("watchlist_items")
                .delete()
                .eq("id", item_id)
                .execute()
            )

            success = len(result.data) > 0

            if success:
                # Update watchlist timestamp
                self.client.table("watchlists").update(
                    {"updated_at": datetime.utcnow().isoformat()}
                ).eq("id", watchlist_id).execute()

                logger.info(
                    f"Item removed from watchlist: {item_id} for user {user_id}"
                )

            return success

        except Exception as e:
            logger.error(f"Error removing item from watchlist: {str(e)}", exc_info=True)
            raise


# Global watchlist service instance
_watchlist_service = None


def get_watchlist_service() -> Optional[WatchlistService]:
    """Get the global watchlist service instance."""
    global _watchlist_service

    if not SUPABASE_AVAILABLE:
        logger.warning("Supabase not available for watchlist service")
        return None

    if _watchlist_service is None:
        try:
            _watchlist_service = WatchlistService()
        except Exception as e:
            logger.error(f"Failed to initialize watchlist service: {str(e)}")
            return None

    return _watchlist_service
