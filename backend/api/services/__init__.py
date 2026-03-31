"""
API services package for HedgeVision.
Contains modular business logic services.
"""

# ============================================================================
# HIGH-LEVEL PUBLIC API (Use this in routers)
# ============================================================================
from .analytics_service import (
    get_analytics_service,
    get_screener_top_pairs,
    get_full_pair_report,
    get_rolling_correlation,
    get_rolling_beta,
    get_rolling_volatility,
    get_correlation_matrix,
    get_screener_status,
    trigger_precomputation,
    clear_screener_cache,
)

# ============================================================================
# LEGACY EXPORTS (For backward compatibility - phase out gradually)
# ============================================================================
from .asset_service import AssetService
from .correlation_service import calculate_rolling_correlation, get_correlation_data
from .data_quality_service import DataQualityService

# NOTE:
# The preferred public surface for routers is analytics_service exports below.
# Legacy exports are retained for backward compatibility with existing imports.

__all__ = [
    # === HIGH-LEVEL ANALYTICS API (PRIMARY) ===
    "get_analytics_service",
    "get_screener_top_pairs",
    "get_full_pair_report", 
    "get_rolling_correlation",
    "get_rolling_beta",
    "get_rolling_volatility",
    "get_correlation_matrix",
    "get_screener_status",
    "trigger_precomputation",
    "clear_screener_cache",
    
    # === LEGACY (For backward compatibility) ===
    "get_correlation_data",
    "calculate_rolling_correlation",
    "AssetService",
    "DataQualityService",
]
