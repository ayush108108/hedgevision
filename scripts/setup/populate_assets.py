"""
Asset population script for HedgeVision with standardized symbols.
Populates Supabase with all HedgeVision assets using standardized naming.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Tuple
import os
import sys
from pathlib import Path

# Add project root and backend directory to path
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"
for path in (project_root, backend_dir):
    path_str = str(path)
    if path_str not in sys.path:
        sys.path.insert(0, path_str)

from api.utils.assets import asset_sectors, name_to_symbol
from api.utils.assets_config import should_include_asset, get_validation_status
from api.services.db_health_models import AssetType, AssetCreate
from api.utils.asset_universe_loader import asset_universe, TICKER_TO_NAME_MAPPING
from supabase import create_client
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class AssetStandardizer:
    """Standardizes and manages HedgeVision asset definitions."""

    def __init__(self, supabase_client=None):
        if supabase_client:
            self.supabase = supabase_client
        else:
            self.supabase = create_client(
                os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY")
            )
        self.standardized_assets = []

    def get_asset_type(self, category: str, symbol: str) -> AssetType:
        """Determine asset type from HedgeVision category and symbol."""
        category_lower = category.lower()
        symbol_upper = symbol.upper()

        if "stock" in category_lower:
            return AssetType.EQUITY
        elif "etf" in category_lower:
            return AssetType.ETF
        elif "crypto" in category_lower or ".CC" in symbol_upper:
            return AssetType.CRYPTO
        elif "forex" in category_lower or ".FOREX" in symbol_upper:
            return AssetType.FOREX
        elif "adr" in category_lower:
            return AssetType.EQUITY  # ADRs are equities
        elif "index" in category_lower:
            return AssetType.INDEX
        else:
            # Default classification by symbol
            if ".US" in symbol_upper:
                return (
                    AssetType.ETF
                    if any(etf_term in category_lower for etf_term in ["etf", "fund"])
                    else AssetType.EQUITY
                )
            elif ".CC" in symbol_upper:
                return AssetType.CRYPTO
            elif ".FOREX" in symbol_upper:
                return AssetType.FOREX
            else:
                return AssetType.EQUITY  # Default

    def get_exchange(self, symbol: str) -> str:
        """Extract exchange from standardized symbol."""
        if "." in symbol:
            return symbol.split(".")[1]
        return "US"  # Default

    def get_sector(self, category: str, name: str) -> str:
        """Determine sector from category and asset name."""
        name_lower = name.lower()
        category_lower = category.lower()

        # Technology companies
        if any(
            tech in name_lower
            for tech in [
                "apple",
                "microsoft",
                "nvidia",
                "meta",
                "alphabet",
                "netflix",
                "c3.ai",
            ]
        ):
            return "Technology"
        elif "amazon" in name_lower:
            return "Consumer Discretionary"
        elif "tesla" in name_lower:
            return "Consumer Discretionary"  # Electric vehicles
        elif "microstrategy" in name_lower:
            return "Technology"

        # ETF sectors
        elif "tech" in name_lower:
            return "Technology"
        elif "financial" in name_lower:
            return "Financial Services"
        elif "energy" in name_lower:
            return "Energy"
        elif "healthcare" in name_lower:
            return "Healthcare"
        elif "utility" in name_lower or "utilities" in name_lower:
            return "Utilities"
        elif "industrial" in name_lower:
            return "Industrials"
        elif "material" in name_lower:
            return "Materials"
        elif "consumer" in name_lower:
            if "disc" in name_lower or "discretionary" in name_lower:
                return "Consumer Discretionary"
            elif "staples" in name_lower:
                return "Consumer Staples"
            else:
                return "Consumer"
        elif "reit" in name_lower or "real estate" in name_lower:
            return "Real Estate"
        elif "treasury" in name_lower or "bond" in name_lower:
            return "Government Bonds"
        elif (
            "gold" in name_lower
            or "silver" in name_lower
            or "commodity" in name_lower
            or "oil" in name_lower
        ):
            return "Commodities"
        elif "volatility" in name_lower or "vix" in name_lower:
            return "Volatility"

        # Crypto
        elif category_lower == "crypto":
            return "Cryptocurrency"

        # Forex
        elif category_lower == "forex pairs":
            return "Currency"

        # Geographic ETFs
        elif any(
            geo in name_lower
            for geo in ["emerging", "china", "japan", "europe", "india"]
        ):
            return "International Equity"

        # Broad market
        elif any(broad in name_lower for broad in ["s&p 500", "nasdaq", "dow jones"]):
            return "Broad Market"

        return "Other"

    def get_provider_symbols(self, standard_symbol: str) -> Dict[str, str]:
        """Generate provider-specific symbol mappings."""
        symbol, exchange = standard_symbol.split(".")

        mappings = {
            "eodhd_symbol": standard_symbol,  # EODHD uses our standard format
        }

        # Polygon (US stocks only, no exchange suffix)
        if exchange == "US":
            mappings["polygon_symbol"] = symbol
            mappings["alpha_vantage_symbol"] = symbol

        # Binance (crypto only)
        if exchange == "CC" and "-USD" in symbol:
            base_symbol = symbol.replace("-USD", "")
            mappings["binance_symbol"] = f"{base_symbol}USDT"

        # CoinMarketCap (crypto only, need to map manually)
        if exchange == "CC":
            cmc_mapping = {
                "BTC-USD": 1,  # Bitcoin
                "ETH-USD": 1027,  # Ethereum
                "SOL-USD": 5426,  # Solana
                "XRP-USD": 52,  # XRP
            }
            if symbol in cmc_mapping:
                mappings["coinmarketcap_id"] = cmc_mapping[symbol]

        return mappings

    def standardize_all_assets(self) -> List[AssetCreate]:
        """Convert all HedgeVision assets to standardized format."""
        standardized = []
        
        # Log validation configuration status
        validation_status = get_validation_status()
        logger.info(f"Asset validation config: {validation_status}")

        # Combine all categories from YAML
        all_categories = {}
        all_categories.update(asset_universe.get_crypto_core_by_category())
        all_categories.update(asset_universe.get_macro_monitor_by_category())
        all_categories.update(asset_universe.get_gap_assets_by_category())

        for category, tickers in all_categories.items():
            for ticker in tickers:
                # Standardize ticker format for EODHD (our DB standard)
                if '-' in ticker and ticker.endswith('-USD'):
                    standard_symbol = f"{ticker}.CC"
                elif '.' in ticker:
                    standard_symbol = ticker # Already standardized
                elif ticker in ['SPY', 'QQQ', 'DIA', 'TLT', 'IEF', 'SHY', 'NVDA', 'AAPL', 'MSFT', 'TSLA', 'META', 'GOOGL', 'AMZN', 'NFLX', 'MSTR', 'AI']:
                    standard_symbol = f"{ticker}.US"
                else:
                    # Fallback or special mapping
                    standard_symbol = f"{ticker}.US" if len(ticker) <= 5 else f"{ticker}.CC"

                display_name = TICKER_TO_NAME_MAPPING.get(ticker, ticker)
                asset_type = self.get_asset_type(category, standard_symbol)
                exchange = self.get_exchange(standard_symbol)
                sector = self.get_sector(category, display_name)
                provider_symbols = self.get_provider_symbols(standard_symbol)

                # Create standardized asset
                asset = AssetCreate(
                    symbol=standard_symbol,
                    name=display_name,
                    asset_type=asset_type,
                    exchange=exchange,
                    currency="USD",  # Default currency
                    sector=sector,
                    description=f"{category} - {display_name}",
                    hedgevision_display_name=display_name,
                    hedgevision_category=category,
                    **provider_symbols,
                )

                standardized.append(asset)

        logger.info(
            f"Standardized {len(standardized)} assets from HedgeVision definitions"
        )
        return standardized

    async def populate_supabase(self, assets: List[AssetCreate]) -> Dict[str, int]:
        """Populate Supabase with standardized assets."""
        results = {"inserted": 0, "updated": 0, "errors": 0}

        for asset in assets:
            try:
                # Check if asset already exists
                existing = (
                    self.supabase.table("assets")
                    .select("id")
                    .eq("symbol", asset.symbol)
                    .execute()
                )

                asset_data = {
                    "symbol": asset.symbol,
                    "name": asset.name,
                    "asset_type": asset.asset_type.value,
                    "exchange": asset.exchange,
                    "currency": asset.currency,
                    "sector": asset.sector,
                    "description": asset.description,
                    "hedgevision_display_name": asset.hedgevision_display_name,
                    "hedgevision_category": asset.hedgevision_category,
                    "eodhd_symbol": asset.eodhd_symbol,
                    "polygon_symbol": asset.polygon_symbol,
                    "alpha_vantage_symbol": asset.alpha_vantage_symbol,
                    "binance_symbol": asset.binance_symbol,
                    "coinmarketcap_id": asset.coinmarketcap_id,
                    "yfinance_ticker": asset.symbol.split('.')[0] if '.' in asset.symbol else asset.symbol,
                    "is_active": 1,
                    "data_quality_score": 100.0,
                }

                if existing.data:
                    # Update existing asset
                    result = (
                        self.supabase.table("assets")
                        .update(asset_data)
                        .eq("symbol", asset.symbol)
                        .execute()
                    )
                    results["updated"] += 1
                    logger.info(f"Updated asset: {asset.symbol} - {asset.name}")
                else:
                    # Insert new asset
                    result = self.supabase.table("assets").insert(asset_data).execute()
                    results["inserted"] += 1
                    logger.info(f"Inserted asset: {asset.symbol} - {asset.name}")

            except Exception as e:
                results["errors"] += 1
                logger.error(f"Error processing {asset.symbol}: {e}")

        return results

    async def verify_assets(self) -> Dict[str, int]:
        """Verify assets were populated correctly."""
        try:
            # Get all assets from Supabase
            response = (
                self.supabase.table("assets")
                .select("symbol, name, asset_type, exchange, hedgevision_category")
                .eq("is_active", 1)
                .execute()
            )

            assets = response.data

            # Group by category
            category_counts = {}
            for asset in assets:
                category = asset.get("hedgevision_category", "Unknown")
                category_counts[category] = category_counts.get(category, 0) + 1

            logger.info("Asset verification results:")
            for category, count in category_counts.items():
                logger.info(f"  {category}: {count} assets")

            return {
                "total_assets": len(assets),
                "categories": len(category_counts),
                "category_breakdown": category_counts,
            }

        except Exception as e:
            logger.error(f"Verification failed: {e}")
            return {"error": str(e)}

    def print_symbol_standardization_report(self, assets: List[AssetCreate]):
        """Print a report of symbol standardization."""
        print("\n" + "=" * 80)
        print("HEDGEVISION SYMBOL STANDARDIZATION REPORT")
        print("=" * 80)

        by_category = {}
        by_exchange = {}
        by_asset_type = {}

        for asset in assets:
            # Group by category
            category = asset.hedgevision_category
            if category not in by_category:
                by_category[category] = []
            by_category[category].append(asset)

            # Group by exchange
            exchange = asset.exchange
            by_exchange[exchange] = by_exchange.get(exchange, 0) + 1

            # Group by asset type
            asset_type = asset.asset_type.value
            by_asset_type[asset_type] = by_asset_type.get(asset_type, 0) + 1

        # Print by category
        print(f"\nASSETS BY CATEGORY ({len(by_category)} categories):")
        print("-" * 50)
        for category, assets_in_category in by_category.items():
            print(f"\n{category} ({len(assets_in_category)} assets):")
            for asset in assets_in_category:
                providers = []
                if asset.polygon_symbol:
                    providers.append(f"Polygon:{asset.polygon_symbol}")
                if asset.binance_symbol:
                    providers.append(f"Binance:{asset.binance_symbol}")
                if asset.coinmarketcap_id:
                    providers.append(f"CMC:{asset.coinmarketcap_id}")

                provider_str = f" [{', '.join(providers)}]" if providers else ""
                print(
                    f"  {asset.symbol:20} → {asset.name:30} ({asset.sector}){provider_str}"
                )

        # Print summary statistics
        print(f"\nSUMMARY STATISTICS:")
        print("-" * 50)
        print(f"Total Assets: {len(assets)}")
        print(f"Categories: {len(by_category)}")

        print(f"\nBy Exchange:")
        for exchange, count in sorted(by_exchange.items()):
            print(f"  {exchange}: {count}")

        print(f"\nBy Asset Type:")
        for asset_type, count in sorted(by_asset_type.items()):
            print(f"  {asset_type}: {count}")

        print("\n" + "=" * 80)


async def main():
    """Main function to populate HedgeVision assets."""
    logger.info("Starting HedgeVision asset population")

    # Check environment
    if not os.getenv("SUPABASE_URL") or not os.getenv("SUPABASE_KEY"):
        logger.error("Missing SUPABASE_URL or SUPABASE_KEY environment variables")
        return

    standardizer = AssetStandardizer()

    try:
        # Standardize assets
        logger.info("Standardizing HedgeVision assets...")
        standardized_assets = standardizer.standardize_all_assets()

        # Print standardization report
        standardizer.print_symbol_standardization_report(standardized_assets)

        # Populate Supabase
        logger.info("Populating Supabase with standardized assets...")
        results = await standardizer.populate_supabase(standardized_assets)

        logger.info("Population results:")
        logger.info(f"  Inserted: {results['inserted']}")
        logger.info(f"  Updated: {results['updated']}")
        logger.info(f"  Errors: {results['errors']}")

        # Verify population
        logger.info("Verifying asset population...")
        verification = await standardizer.verify_assets()

        if "error" not in verification:
            logger.info(
                f"Verification successful: {verification['total_assets']} assets in {verification['categories']} categories"
            )
        else:
            logger.error(f"Verification failed: {verification['error']}")

        logger.info("Asset population complete!")

    except Exception as e:
        logger.error(f"Asset population failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
