"""
Database models for HedgeVision integrated with db-health architecture.
Supports both Supabase and local SQLAlchemy operations.
"""

import json
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

from pydantic import BaseModel
from sqlalchemy import Boolean, Column, DateTime
from sqlalchemy import Enum as SQLEnum
from sqlalchemy import Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship

Base = declarative_base()


class AssetType(Enum):
    """Standardized asset types for HedgeVision compatibility."""

    EQUITY = "equity"  # US stocks, ADRs
    ETF = "etf"  # Exchange-traded funds
    CRYPTO = "crypto"  # Cryptocurrencies
    FOREX = "forex"  # Currency pairs
    COMMODITY = "commodity"
    INDEX = "index"
    BOND = "bond"


class ExchangeType(Enum):
    """Supported exchanges."""

    US = "US"  # US Markets (NYSE, NASDAQ)
    FOREX = "FOREX"  # Forex markets
    CC = "CC"  # Cryptocurrency
    NSE = "NSE"  # India NSE
    CRYPTO = "CRYPTO"  # Alternative crypto designation


# ===== SQLAlchemy Models for Local Operations =====


class Asset(Base):
    """Asset model compatible with db-health and HedgeVision standards."""

    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    symbol = Column(
        String(20), unique=True, nullable=False, index=True
    )  # Format: AAPL.US
    name = Column(String(255), nullable=False)  # Display name: Apple
    asset_type = Column(SQLEnum(AssetType), nullable=False, index=True)
    exchange = Column(String(50), nullable=False)  # US, FOREX, CC, NSE
    currency = Column(String(3), default="USD", nullable=False)
    sector = Column(String(100))  # Technology, Financial, etc.
    description = Column(Text)
    market_cap = Column(Float)  # Market capitalization

    # HedgeVision specific fields
    hedgevision_display_name = Column(String(255))  # Original HedgeVision name
    hedgevision_category = Column(String(50))  # US Stocks, US ETFs, etc.

    # Data provider mapping
    eodhd_symbol = Column(String(20))  # AAPL.US
    polygon_symbol = Column(String(20))  # AAPL
    alpha_vantage_symbol = Column(String(20))  # AAPL
    binance_symbol = Column(String(20))  # BTCUSDT (for crypto)
    coinmarketcap_id = Column(Integer)  # CMC ID for crypto

    # Status and metadata
    is_active = Column(Boolean, default=True, nullable=False)
    data_quality_score = Column(Float, default=100.0)  # 0-100
    last_price_update = Column(DateTime)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    price_history = relationship(
        "PriceHistory", back_populates="asset", cascade="all, delete-orphan"
    )
    rolling_metrics = relationship(
        "RollingMetrics", back_populates="asset", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Asset(symbol='{self.symbol}', name='{self.name}', type='{self.asset_type}')>"


class PriceHistory(Base):
    """OHLCV price history with data source tracking."""

    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    timestamp = Column(DateTime, nullable=False, index=True)

    # OHLCV data
    open = Column(Float, nullable=False)
    high = Column(Float, nullable=False)
    low = Column(Float, nullable=False)
    close = Column(Float, nullable=False)
    volume = Column(Float)
    adjusted_close = Column(Float)

    # Data source and quality
    source = Column(String(50), nullable=False)  # eodhd, polygon, binance, etc.
    data_quality = Column(Float, default=100.0)  # Quality score 0-100

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    asset = relationship("Asset", back_populates="price_history")

    # Indexes for performance
    __table_args__ = (
        Index("idx_asset_timestamp", "asset_id", "timestamp"),
        Index("idx_timestamp_desc", "timestamp"),
        Index("idx_asset_source", "asset_id", "source"),
    )

    def __repr__(self):
        return f"<PriceHistory(asset_id={self.asset_id}, timestamp='{self.timestamp}', close={self.close}, source='{self.source}')>"


class RollingMetrics(Base):
    """Pre-computed rolling metrics for HedgeVision analytics."""

    __tablename__ = "rolling_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    benchmark_id = Column(Integer, ForeignKey("assets.id"))  # SPY for beta calculation

    # Rolling window specification
    window_days = Column(Integer, nullable=False)  # 30, 60, 90, etc.
    end_date = Column(DateTime, nullable=False)
    start_date = Column(DateTime, nullable=False)

    # Computed metrics
    rolling_beta = Column(Float)
    rolling_volatility = Column(Float)  # Annualized
    rolling_sharpe_ratio = Column(Float)
    rolling_sortino_ratio = Column(Float)
    rolling_max_drawdown = Column(Float)
    rolling_var_95 = Column(Float)  # Value at Risk
    rolling_cvar_95 = Column(Float)  # Conditional VaR
    rolling_hurst_exponent = Column(Float)  # Mean reversion indicator

    # Data quality and metadata
    sample_size = Column(Integer, nullable=False)
    data_quality_score = Column(Float, default=100.0)
    calculation_timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    asset = relationship("Asset", back_populates="rolling_metrics")
    benchmark = relationship("Asset", foreign_keys=[benchmark_id])

    # Indexes
    __table_args__ = (
        Index("idx_asset_end_date", "asset_id", "end_date"),
        Index("idx_window_end_date", "window_days", "end_date"),
    )

    def __repr__(self):
        return f"<RollingMetrics(asset_id={self.asset_id}, window={self.window_days}d, beta={self.rolling_beta:.3f})>"


class CorrelationMatrix(Base):
    """Correlation matrix snapshots for HedgeVision analytics."""

    __tablename__ = "correlation_matrix"

    id = Column(Integer, primary_key=True, autoincrement=True)
    matrix_date = Column(DateTime, nullable=False, index=True)
    window_days = Column(Integer, nullable=False)
    calculation_method = Column(
        String(20), default="pearson"
    )  # pearson, spearman, kendall

    # Correlation data (stored as JSON)
    correlation_matrix = Column(Text)  # JSON: {"AAPL.US": {"SPY.US": 0.85, ...}, ...}
    overlap_matrix = Column(Text)  # JSON: Sample counts per pair
    validity_matrix = Column(Text)  # JSON: Valid correlation flags

    # Summary statistics
    average_correlation = Column(Float)
    min_correlation = Column(Float)
    max_correlation = Column(Float)
    valid_pairs_count = Column(Integer)
    total_pairs_count = Column(Integer)
    data_quality_score = Column(Float, default=100.0)

    calculation_timestamp = Column(DateTime, default=datetime.utcnow)

    # Indexes
    __table_args__ = (Index("idx_matrix_date_window", "matrix_date", "window_days"),)

    def get_correlation_dict(self) -> Dict[str, Dict[str, float]]:
        """Parse correlation matrix from JSON."""
        if self.correlation_matrix:
            return json.loads(self.correlation_matrix)
        return {}

    def set_correlation_dict(self, correlation_data: Dict[str, Dict[str, float]]):
        """Store correlation matrix as JSON."""
        self.correlation_matrix = json.dumps(correlation_data)

    def __repr__(self):
        return f"<CorrelationMatrix(date='{self.matrix_date}', window={self.window_days}d, pairs={self.valid_pairs_count})>"


class IngestionLog(Base):
    """Log of data ingestion operations for monitoring and debugging."""

    __tablename__ = "ingestion_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    asset_id = Column(Integer, ForeignKey("assets.id"))
    source = Column(String(50), nullable=False)
    operation_type = Column(String(20))  # daily, hourly, backfill

    # Date range processed
    start_date = Column(DateTime)
    end_date = Column(DateTime)

    # Results
    records_inserted = Column(Integer, default=0)
    records_updated = Column(Integer, default=0)
    records_skipped = Column(Integer, default=0)
    status = Column(String(20), nullable=False)  # success, failed, partial
    error_message = Column(Text)

    # Performance metrics
    duration_seconds = Column(Float)
    api_calls_made = Column(Integer, default=0)
    rate_limit_delays = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def __repr__(self):
        return f"<IngestionLog(asset_id={self.asset_id}, source='{self.source}', status='{self.status}')>"


# ===== Pydantic Models for API and Supabase Operations =====


class AssetCreate(BaseModel):
    """Pydantic model for creating assets."""

    symbol: str
    name: str
    asset_type: AssetType
    exchange: str
    currency: str = "USD"
    sector: Optional[str] = None
    description: Optional[str] = None
    hedgevision_display_name: Optional[str] = None
    hedgevision_category: Optional[str] = None
    eodhd_symbol: Optional[str] = None
    polygon_symbol: Optional[str] = None
    alpha_vantage_symbol: Optional[str] = None
    binance_symbol: Optional[str] = None
    coinmarketcap_id: Optional[int] = None


class AssetResponse(BaseModel):
    """Pydantic model for asset API responses."""

    id: int
    symbol: str
    name: str
    asset_type: AssetType
    exchange: str
    currency: str
    sector: Optional[str]
    is_active: bool
    data_quality_score: float
    last_price_update: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True


class PriceDataPoint(BaseModel):
    """Single price data point."""

    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float] = None
    adjusted_close: Optional[float] = None
    source: str


class RollingMetricsResponse(BaseModel):
    """Rolling metrics API response."""

    asset_id: int
    window_days: int
    end_date: datetime
    rolling_beta: Optional[float]
    rolling_volatility: Optional[float]
    rolling_sharpe_ratio: Optional[float]
    rolling_max_drawdown: Optional[float]
    sample_size: int
    data_quality_score: float

    class Config:
        from_attributes = True


# ===== Symbol Standardization Utilities =====


def standardize_symbol(raw_symbol: str, provider: str = None) -> str:
    """
    Standardize symbols to HedgeVision format (SYMBOL.EXCHANGE).

    Args:
        raw_symbol: Raw symbol from provider
        provider: Data provider name (eodhd, polygon, etc.)

    Returns:
        Standardized symbol in SYMBOL.EXCHANGE format
    """
    # Already in standard format
    if "." in raw_symbol and raw_symbol.count(".") == 1:
        return raw_symbol.upper()

    # Provider-specific conversions
    if provider == "polygon":
        return f"{raw_symbol.upper()}.US"
    elif provider == "binance":
        if raw_symbol.endswith("USDT"):
            base = raw_symbol.replace("USDT", "")
            return f"{base}-USD.CC"
        return f"{raw_symbol}.CC"
    elif provider == "coinmarketcap":
        # CMC uses cryptocurrency names, need mapping
        crypto_mapping = {
            "bitcoin": "BTC-USD.CC",
            "solana": "SOL-USD.CC",
            "ripple": "XRP-USD.CC",
            "ethereum": "ETH-USD.CC",
        }
        return crypto_mapping.get(raw_symbol.lower(), f"{raw_symbol.upper()}-USD.CC")

    # Default: assume US stock
    return f"{raw_symbol.upper()}.US"


def get_provider_symbol(standard_symbol: str, provider: str) -> str:
    """
    Convert standardized symbol to provider-specific format.

    Args:
        standard_symbol: SYMBOL.EXCHANGE format
        provider: Target provider (polygon, binance, etc.)

    Returns:
        Provider-specific symbol format
    """
    symbol, exchange = standard_symbol.split(".")

    if provider == "polygon":
        if exchange == "US":
            return symbol
        return standard_symbol  # Keep as-is for non-US
    elif provider == "binance":
        if exchange == "CC" and "-USD" in symbol:
            base = symbol.replace("-USD", "")
            return f"{base}USDT"
        return symbol
    elif provider == "alpha_vantage":
        if exchange == "US":
            return symbol
        return standard_symbol
    elif provider == "eodhd":
        return standard_symbol  # EODHD uses our standard format

    return symbol  # Default: return base symbol
