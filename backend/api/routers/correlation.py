"""Correlation endpoints used by the React frontend."""

from __future__ import annotations

import logging
import math
import os
import sys
from datetime import datetime
from numbers import Real
from typing import Dict, List, Optional

import pandas as pd
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

# Add parent directory to path to import business logic modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.services import correlation_service
from api.utils.assets import asset_sectors, name_to_symbol, symbol_to_name
from api.utils.cache_adapter import get_cache_adapter
from api.utils.config import config
from api.utils.error_handlers import DatabaseError, DataNotFoundError, ValidationError
from api.utils.security import sanitize_error_message
from api.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/correlation", tags=["correlation"])

cache = get_cache_adapter(default_ttl=config["REDIS_TTL"])


class CorrelationMatrixResponse(BaseModel):
    """Correlation matrix formatted for the frontend heatmap."""

    assets: List[str] = Field(..., description="Assets included in the matrix")
    matrix: Dict[str, Dict[str, Optional[float]]] = Field(
        ..., description="Nested correlation matrix (null for NaN/Inf)"
    )
    missing_assets: List[str] = Field(
        default_factory=list, description="Assets without enough data"
    )
    metadata: Dict[str, str] = Field(
        default_factory=dict, description="Additional context about the calculation"
    )


class TopPair(BaseModel):
    """Representation of the strongest correlations."""

    asset1: str
    asset2: str
    correlation: float


class RollingCorrelationRequest(BaseModel):
    asset1: str = Field(..., description="Display name of the first asset")
    asset2: str = Field(..., description="Display name of the second asset")
    window: int = Field(30, ge=1, description="Rolling window size in periods")
    start_date: Optional[str] = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[str] = Field(None, description="End date (YYYY-MM-DD)")
    granularity: str = Field("daily", description="Data frequency (daily|hourly)")


class RollingCorrelationPoint(BaseModel):
    date: datetime
    correlation: Optional[float]


class RollingCorrelationResponse(BaseModel):
    asset1: str
    asset2: str
    window: int
    granularity: str
    data: List[RollingCorrelationPoint]


def _resolve_symbols(names: List[str]) -> List[str]:
    """Translate display names to symbols when possible."""

    symbols: List[str] = []
    for name in names:
        symbol = name_to_symbol.get(name)
        symbols.append(symbol or name)
    return sorted(set(symbols))


def _pick_assets(sector: Optional[str]) -> List[str]:
    """Derive an asset universe based on the optional sector filter."""

    if not sector or sector.lower() == "all":
        names = {asset for values in asset_sectors.values() for asset in values}
        return _resolve_symbols(list(names))

    for sector_name, assets_in_sector in asset_sectors.items():
        if sector_name.lower() == sector.lower():
            return _resolve_symbols(list(assets_in_sector))

    # Unknown sector – return an empty list so the caller can surface an informative error
    logger.warning(
        "Unknown sector filter '%s' supplied to correlation endpoint", sector
    )
    return []


def _to_matrix(df: pd.DataFrame, assets: List[str]) -> CorrelationMatrixResponse:
    """Convert a pandas correlation frame into the JSON structure consumed by the UI.
    
    Handles two modes:
    1. Sector-level: DataFrame has sector names (e.g., 'US Stocks', 'Crypto')
    2. Asset-level: DataFrame has display names (e.g., 'Apple', 'Microsoft')
    
    Args:
        df: DataFrame with sector names OR display names as both index and columns
        assets: List of symbols that were requested (e.g., ['AAPL.US', 'MSFT.US'])
    
    Returns:
        CorrelationMatrixResponse with sector names or symbols as keys
    """
    logger.info(f"DataFrame index: {list(df.index)}")
    logger.info(f"DataFrame columns: {list(df.columns)}")
    logger.info(f"Requested assets (symbols): {assets}")

    # Detect if DataFrame contains sector names or individual asset display names
    if len(df.index) > 0:
        first_item = df.index[0]
        is_sector_level = first_item in asset_sectors
        logger.info(f"Detected {'SECTOR-LEVEL' if is_sector_level else 'ASSET-LEVEL'} DataFrame (first item: '{first_item}')")
    else:
        logger.warning("Empty DataFrame received")
        return CorrelationMatrixResponse(
            assets=[], 
            matrix={}, 
            missing_assets=assets, 
            metadata={"generated_at": datetime.utcnow().isoformat() + "Z"}
        )

    # SECTOR-LEVEL MODE: Return sectors as-is (no symbol conversion needed)
    if is_sector_level:
        sector_names = list(df.index)
        matrix: Dict[str, Dict[str, Optional[float]]] = {}
        
        for row_sector in sector_names:
            row_values: Dict[str, Optional[float]] = {}
            
            for col_sector in sector_names:
                value = df.loc[row_sector, col_sector]
                
                # Handle NaN, Inf, -Inf by converting to None (null in JSON)
                if pd.isna(value) or (isinstance(value, float) and (math.isinf(value) or math.isnan(value))):
                    row_values[col_sector] = None
                elif isinstance(value, Real):
                    row_values[col_sector] = float(value)
                else:
                    row_values[col_sector] = None
            
            matrix[row_sector] = row_values

        metadata = {
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "sectors": str(len(sector_names)),
            "mode": "sector",
        }

        return CorrelationMatrixResponse(
            assets=sector_names,  # Return sector names instead of symbols
            matrix=matrix,
            missing_assets=[],  # No missing assets in sector mode
            metadata=metadata
        )

    # ASSET-LEVEL MODE: Convert between display names and symbols
    asset_display_names = [symbol_to_name.get(asset, asset) for asset in assets]
    logger.info(f"Converted to display names: {asset_display_names}")

    # Find which display names are actually in the DataFrame
    available_display_names = [name for name in asset_display_names if name in df.index]
    missing_display_names = sorted(set(asset_display_names) - set(available_display_names))
    
    logger.info(f"Available display names: {available_display_names}")
    logger.info(f"Missing display names: {missing_display_names}")

    # Create reverse mapping: display name -> symbol
    name_to_symbol_map = {v: k for k, v in symbol_to_name.items()}
    
    # Convert missing display names back to symbols for API response
    missing_symbols = [name_to_symbol_map.get(name, name) for name in missing_display_names]

    if not available_display_names:
        # Return empty response with all assets marked as missing
        return CorrelationMatrixResponse(
            assets=[], 
            matrix={}, 
            missing_assets=assets, 
            metadata={"generated_at": datetime.utcnow().isoformat() + "Z"}
        )

    # Build correlation matrix using symbols as keys (for frontend) but display names for DataFrame access
    sub_frame = df.loc[available_display_names, available_display_names]
    matrix: Dict[str, Dict[str, Optional[float]]] = {}
    
    for row_name in available_display_names:
        row_symbol = name_to_symbol_map.get(row_name, row_name)
        row_values: Dict[str, Optional[float]] = {}
        
        for col_name in available_display_names:
            col_symbol = name_to_symbol_map.get(col_name, col_name)
            value = sub_frame.loc[row_name, col_name]
            
            # Handle NaN, Inf, -Inf by converting to None (null in JSON)
            if pd.isna(value) or (isinstance(value, float) and (math.isinf(value) or math.isnan(value))):
                row_values[col_symbol] = None
            elif isinstance(value, Real):
                row_values[col_symbol] = float(value)
            else:
                row_values[col_symbol] = None
        
        matrix[row_symbol] = row_values

    # Convert available display names back to symbols for assets list
    available_symbols = [name_to_symbol_map.get(name, name) for name in available_display_names]

    metadata = {
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "assets_requested": str(len(assets)),
        "assets_available": str(len(available_symbols)),
        "assets_missing": str(len(missing_symbols)),
        "mode": "asset",
    }

    return CorrelationMatrixResponse(
        assets=available_symbols,
        matrix=matrix,
        missing_assets=missing_symbols,
        metadata=metadata,
    )


@router.get("", response_model=CorrelationMatrixResponse)
async def get_correlation_matrix(
    start_date: Optional[str] = Query(
        None, description="Correlation window start (YYYY-MM-DD)"
    ),
    end_date: Optional[str] = Query(
        None, description="Correlation window end (YYYY-MM-DD)"
    ),
    method: str = Query(
        "spearman", description="Correlation method (spearman|pearson)"
    ),
    sector: Optional[str] = Query(
        "US Stocks", description="Optional sector filter (defaults to US Stocks)"
    ),
    granularity: str = Query("daily", description="Data frequency (daily|hourly)"),
    min_periods: int = Query(60, description="Minimum overlapping observations"),
    view_mode: str = Query("asset", description="View mode (asset|sector)"),
) -> CorrelationMatrixResponse:
    """Expose the correlation matrix that powers the heatmap view."""

    # Validate date format if provided
    if start_date:
        try:
            pd.to_datetime(start_date)
        except Exception:
            raise ValidationError("start_date", "Must be in YYYY-MM-DD format")

    if end_date:
        try:
            pd.to_datetime(end_date)
        except Exception:
            raise ValidationError("end_date", "Must be in YYYY-MM-DD format")

    # Validate method
    if method not in ["spearman", "pearson"]:
        raise ValidationError("method", "Must be 'spearman' or 'pearson'")

    # Validate granularity
    if granularity not in ["daily", "hourly", "4h"]:
        raise ValidationError("granularity", "Must be 'daily', 'hourly', or '4h'")

    assets = _pick_assets(sector)
    if not assets:
        raise DataNotFoundError("Assets", f"sector={sector}")

    logger.info(
        f"Computing correlation matrix: sector={sector}, method={method}, granularity={granularity}, view_mode={view_mode}, assets={len(assets)}"
    )

    try:
        corr_frame = correlation_service.get_correlation_data(
            cache,
            start_date=start_date,
            end_date=end_date,
            method=method,
            granularity=granularity,
            min_periods=min_periods,
            view_mode=view_mode,
        )
    except Exception as e:
        logger.error(f"Database error: {sanitize_error_message(e)}")
        raise DatabaseError("fetch correlation data")

    if corr_frame is None:
        logger.warning(
            "Correlation calculation returned no data; attempting precomputed fallback"
        )
        # Fallback: try precomputed matrix from Supabase
        try:
            supa = get_supabase_client()
            if supa:
                mc = supa.get_correlation_matrix(granularity=granularity, method=method)
                if mc and mc.get("correlation_matrix"):
                    cm = mc["correlation_matrix"]
                    # Convert to DataFrame for reuse of formatting logic
                    try:
                        df = pd.DataFrame(cm)
                        # Ensure symmetric by aligning indexes/columns
                        all_keys = sorted(set(df.index.astype(str)) | set(df.columns.astype(str)))
                        df = df.reindex(index=all_keys, columns=all_keys)

                        # Rename symbols -> display names to match _to_matrix expectations
                        df = df.rename(index=symbol_to_name, columns=symbol_to_name)

                        logger.info("Served correlation from precomputed fallback")
                        return _to_matrix(df, assets)
                    except Exception:
                        # If DataFrame construction fails, reply empty
                        pass
        except Exception as fe:
            logger.warning(f"Precomputed fallback failed: {sanitize_error_message(fe)}")

        # If fallback fails, return empty structure
        return _to_matrix(pd.DataFrame(), assets)

    if not isinstance(corr_frame, pd.DataFrame):
        logger.error(f"Unexpected correlation output type: {type(corr_frame)}")
        raise DatabaseError("correlation calculation", "Unexpected data type")

    logger.info(
        f"Successfully computed correlation matrix: {corr_frame.shape[0]}x{corr_frame.shape[1]} assets"
    )
    logger.info(f"DataFrame index before _to_matrix: {list(corr_frame.index)[:10]}")
    logger.info(f"DataFrame columns before _to_matrix: {list(corr_frame.columns)[:10]}")
    logger.info(f"Assets passed to _to_matrix: {assets}")
    response = _to_matrix(corr_frame, assets)

    # If result is effectively empty, try precomputed fallback once
    if not response.assets and not response.matrix:
        try:
            supa = get_supabase_client()
            if supa:
                mc = supa.get_correlation_matrix(granularity=granularity, method=method)
                if mc and mc.get("correlation_matrix"):
                    cm = mc["correlation_matrix"]
                    df = pd.DataFrame(cm)
                    all_keys = sorted(set(df.index.astype(str)) | set(df.columns.astype(str)))
                    df = df.reindex(index=all_keys, columns=all_keys)
                    df = df.rename(index=symbol_to_name, columns=symbol_to_name)
                    logger.info("Dynamic result empty; served precomputed fallback")
                    return _to_matrix(df, assets)
        except Exception as fe:
            logger.warning(f"Precomputed fallback after dynamic empty failed: {sanitize_error_message(fe)}")

    return response
