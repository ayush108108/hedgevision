"""
Asset configuration for validation testing.
Now loads from the master asset universe YAML configuration.
Temporarily limits asset universe to 50 assets for Supabase free tier validation.
"""

from .asset_universe_loader import get_all_assets, get_crypto_core_assets, get_macro_monitor_assets

# TEMPORARY: Limited to 50 assets for validation testing within Supabase FREE tier limits
# This helps ensure we don't exceed the 500MB storage limit during testing phase
# TODO: Remove this limit once migrated to production database or validated the workflows

# Set to True to enable the 50-asset limit for validation
ENABLE_ASSET_LIMIT = False
MAX_ASSETS_FOR_VALIDATION = 50

# Load all available assets from the master configuration
ALL_AVAILABLE_ASSETS = get_all_assets()
CRYPTO_CORE_ASSETS = get_crypto_core_assets()
MACRO_MONITOR_ASSETS = get_macro_monitor_assets()

# Priority assets for testing (50 most liquid and representative assets)
# Prioritize crypto core, then macro monitors, then others
VALIDATION_ASSETS = (
    CRYPTO_CORE_ASSETS[:30] +  # Top 30 crypto core
    MACRO_MONITOR_ASSETS[:20]   # Top 20 macro monitors
)[:MAX_ASSETS_FOR_VALIDATION]  # Limit to 50 total

def should_include_asset(asset_name: str) -> bool:
    """
    Check if an asset should be included based on validation configuration.
    
    Args:
        asset_name: Display name of the asset
        
    Returns:
        True if asset should be included in current configuration
    """
    if not ENABLE_ASSET_LIMIT:
        return True
    
    return asset_name in VALIDATION_ASSETS

def get_validation_status() -> dict:
    """Get current validation configuration status."""
    return {
        "limit_enabled": ENABLE_ASSET_LIMIT,
        "max_assets": MAX_ASSETS_FOR_VALIDATION if ENABLE_ASSET_LIMIT else "unlimited",
        "total_validation_assets": len(VALIDATION_ASSETS),
        "total_available_assets": len(ALL_AVAILABLE_ASSETS),
        "crypto_core_count": len(CRYPTO_CORE_ASSETS),
        "macro_monitor_count": len(MACRO_MONITOR_ASSETS),
        "note": "Assets loaded from config/asset_universe_master.yaml, limited to 50 for Supabase FREE tier validation testing"
    }
