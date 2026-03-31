"""
Repository Layer

This package implements the Repository Pattern for clean separation
of data access logic from business logic.

Benefits:
- Single source of truth for database queries
- Easy to test with mock repositories
- Centralized query optimization
- Clear separation of concerns
- Reduced code duplication

Usage:
    from repositories import AssetRepository, PriceRepository
    from api.utils.supabase_client import get_supabase_client
    
    supabase = get_supabase_client()
    asset_repo = AssetRepository(supabase)
    
    # Use repository methods
    active_assets = asset_repo.get_active_assets()
"""

from .asset_repository import AssetRepository
from .base_repository import BaseRepository

__all__ = [
    "BaseRepository",
    "AssetRepository",
]
