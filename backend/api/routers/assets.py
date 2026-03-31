"""Assets endpoints for fetching available assets from the database."""

import logging
import sqlite3
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from api.utils.config import config
from api.utils.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/assets", tags=["assets"])


def _sqlite_assets_query(search: Optional[str], limit: int) -> List[dict]:
    db_path = str(config.get("DB_PATH"))
    try:
        with sqlite3.connect(db_path, timeout=5.0) as conn:
            conn.row_factory = sqlite3.Row
            if search:
                pattern = f"%{search}%"
                rows = conn.execute(
                    """
                    SELECT id, symbol, name
                    FROM assets
                    WHERE symbol LIKE ? OR name LIKE ?
                    ORDER BY symbol
                    LIMIT ?
                    """,
                    (pattern.upper(), pattern, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT id, symbol, name FROM assets ORDER BY symbol LIMIT ?",
                    (limit,),
                ).fetchall()
            return [dict(row) for row in rows]
    except sqlite3.OperationalError:
        return []


class Asset(BaseModel):
    """Model for an asset."""
    id: int
    symbol: str
    name: Optional[str] = None


class AssetsResponse(BaseModel):
    """Response model for assets list."""
    assets: List[Asset]
    total: int


@router.get("", response_model=AssetsResponse)
async def get_assets(
    search: Optional[str] = Query(None, description="Search by symbol or name"),
    limit: int = Query(1000, ge=1, le=5000, description="Maximum number of assets to return"),
) -> AssetsResponse:
    """
    Get list of available assets from the database.
    
    This endpoint returns assets that have price data available for testing.
    """
    try:
        if config.get("DATA_BACKEND") == "sqlite":
            rows = _sqlite_assets_query(search, limit)
            assets = [Asset(**asset) for asset in rows]
            return AssetsResponse(assets=assets, total=len(assets))

        supabase = get_supabase_client()
        if not supabase:
            raise RuntimeError("Supabase client unavailable")
        
        # Start building query
        query = supabase.client.table("assets").select("id, symbol, name")
        
        # Apply search filter
        if search:
            # Search in both symbol and name
            search_upper = search.upper()
            query = query.or_(f"symbol.ilike.%{search_upper}%,name.ilike.%{search}%")
        
        # Order by symbol and limit
        query = query.order("symbol").limit(limit)
        
        # Execute query
        response = query.execute()
        
        assets = [Asset(**asset) for asset in response.data]
        
        logger.info(f"✅ Retrieved {len(assets)} assets")
        
        return AssetsResponse(
            assets=assets,
            total=len(assets)
        )
        
    except Exception as e:
        logger.error(f"❌ Error fetching assets: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch assets: {str(e)}"
        )


@router.get("/popular", response_model=AssetsResponse)
async def get_popular_assets() -> AssetsResponse:
    """
    Get a curated list of popular assets commonly used for pairs trading.
    
    This returns assets that are known to have good liquidity and data availability.
    """
    try:
        if config.get("DATA_BACKEND") == "sqlite":
            rows = _sqlite_assets_query(None, 10000)
            popular_base = {
                "SPY", "QQQ", "IWM", "DIA", "GLD", "SLV", "TLT", "UUP",
                "XLE", "XLF", "XLK", "XLV", "XLP", "XLI", "XLB", "XLU",
                "XLY", "XLC", "VXX", "UVXY", "USO", "UNG", "DBA", "EWJ",
                "EWZ", "EEM", "FXI", "AGG", "LQD", "HYG",
            }
            filtered = []
            for row in rows:
                symbol = str(row.get("symbol") or "")
                base = symbol.split(".")[0]
                if symbol in popular_base or base in popular_base:
                    filtered.append(Asset(**row))
            filtered = filtered[:1000]
            return AssetsResponse(assets=filtered, total=len(filtered))

        supabase = get_supabase_client()
        if not supabase:
            raise RuntimeError("Supabase client unavailable")
        
        # Define popular symbols that are commonly used
        popular_symbols = [
            # Major ETFs
            "SPY.US", "QQQ.US", "IWM.US", "DIA.US",
            "GLD.US", "SLV.US", "TLT.US", "UUP.US",
            # Sector ETFs
            "XLE.US", "XLF.US", "XLK.US", "XLV.US",
            "XLP.US", "XLI.US", "XLB.US", "XLU.US",
            "XLY.US", "XLC.US",
            # Volatility/Strategy
            "VXX.US", "UVXY.US",
            # Commodities
            "USO.US", "UNG.US", "DBA.US",
            # International
            "EWJ.US", "EWZ.US", "EEM.US", "FXI.US",
            # Bonds
            "AGG.US", "LQD.US", "HYG.US",
        ]
        
        # Query for these specific symbols
        query = supabase.client.table("assets").select("id, symbol, name")
        query = query.in_("symbol", popular_symbols)
        query = query.order("symbol")
        
        response = query.execute()
        
        assets = [Asset(**asset) for asset in response.data]
        
        logger.info(f"✅ Retrieved {len(assets)} popular assets out of {len(popular_symbols)} requested")
        
        return AssetsResponse(
            assets=assets,
            total=len(assets)
        )
        
    except Exception as e:
        logger.error(f"❌ Error fetching popular assets: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch popular assets: {str(e)}"
        )


@router.get("/symbols", response_model=List[str])
async def get_asset_symbols(
    limit: int = Query(1000, ge=1, le=5000, description="Maximum number of symbols to return"),
) -> List[str]:
    """
    Get list of available asset symbols only (lightweight endpoint).
    
    Returns just the symbols for quick lookups and autocomplete functionality.
    """
    try:
        if config.get("DATA_BACKEND") == "sqlite":
            rows = _sqlite_assets_query(None, limit)
            symbols = [str(asset["symbol"]) for asset in rows if asset.get("symbol")]
            return symbols

        supabase = get_supabase_client()
        if not supabase:
            raise RuntimeError("Supabase client unavailable")
        
        query = supabase.client.table("assets").select("symbol")
        query = query.order("symbol").limit(limit)
        
        response = query.execute()
        
        symbols = [asset["symbol"] for asset in response.data]
        
        logger.info(f"✅ Retrieved {len(symbols)} asset symbols")
        
        return symbols
        
    except Exception as e:
        logger.error(f"❌ Error fetching asset symbols: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch asset symbols: {str(e)}"
        )
