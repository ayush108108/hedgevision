#!/usr/bin/env python3
"""
Validate yfinance tickers in TimescaleDB and identify unsupported ones.

This script checks each asset's symbol against yfinance to see if it's valid.
It reports which assets are not supported and suggests alternatives.

Usage:
    python scripts/validate_yfinance_tickers.py [--fix] [--commit]
"""

import os
import sys
import time
from pathlib import Path
from typing import List, Tuple

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

try:
    import psycopg2
    import yfinance as yf
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Missing required packages: {e}")
    print("Install with: pip install psycopg2-binary yfinance python-dotenv")
    sys.exit(1)

# Load environment variables
load_dotenv()

def get_database_connection():
    """Get TimescaleDB connection from environment variables."""
    db_url = os.getenv('DATABASE_URL') or os.getenv('TIMESCALEDB_URL') or os.getenv('HEROKU_DB_URL')

    if not db_url:
        raise ValueError("No database URL found. Set DATABASE_URL, TIMESCALEDB_URL, or HEROKU_DB_URL environment variable.")

    try:
        conn = psycopg2.connect(db_url)
        return conn
    except Exception as e:
        print(f"Failed to connect to database: {e}")
        sys.exit(1)

def get_all_assets(conn) -> List[Tuple[int, str, str]]:
    """Get all assets from database."""
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT id, symbol, name FROM assets WHERE is_active = true ORDER BY symbol")
            assets = cursor.fetchall()
        return assets
    except Exception as e:
        print(f"Error fetching assets: {e}")
        return []

def validate_ticker(ticker: str) -> Tuple[bool, str]:
    """
    Validate a yfinance ticker.

    Returns:
        (is_valid, error_message)
    """
    try:
        # Try to create ticker object and get basic info
        stock = yf.Ticker(ticker)

        # Try to get basic info (this will fail for invalid tickers)
        info = stock.info

        # Check if we got valid data
        if info and 'symbol' in info:
            return True, ""

        # Some tickers might not have 'symbol' but are still valid
        # Try getting recent data as fallback
        hist = stock.history(period="1d")
        if not hist.empty:
            return True, ""

        return False, "No data available"

    except Exception as e:
        error_msg = str(e)
        if "No data found" in error_msg:
            return False, "No data found for this symbol"
        elif "404" in error_msg:
            return False, "Symbol not found"
        else:
            return False, f"Error: {error_msg}"

def validate_all_tickers(assets: List[Tuple[int, str, str]], delay: float = 0.5) -> Tuple[List, List]:
    """
    Validate all tickers against yfinance.

    Returns:
        (valid_assets, invalid_assets)
    """
    valid_assets = []
    invalid_assets = []

    print(f"🔍 Validating {len(assets)} tickers against yfinance...")
    print("This may take a few minutes. Please wait...\n")

    for i, (asset_id, symbol, name) in enumerate(assets):
        if (i + 1) % 20 == 0:
            print(f"Validated {i + 1}/{len(assets)} tickers...")

        is_valid, error = validate_ticker(symbol)

        if is_valid:
            valid_assets.append((asset_id, symbol, name))
        else:
            invalid_assets.append((asset_id, symbol, name, error))

        # Rate limiting to be respectful to yfinance
        if delay > 0:
            time.sleep(delay)

    return valid_assets, invalid_assets

def suggest_alternatives(symbol: str) -> List[str]:
    """Suggest alternative ticker formats for common issues."""
    suggestions = []

    # Common patterns that might need adjustment
    if symbol.endswith('=X') and 'USD' in symbol:
        # Forex pairs - try different formats
        base = symbol.replace('=X', '').replace('USD', '')
        suggestions.extend([
            f"{base}=X",
            f"{base}USD=X",
            f"{symbol.replace('USD', '')}=X"
        ])
    elif symbol.endswith('-USD'):
        # Crypto - try different formats
        base = symbol.replace('-USD', '')
        suggestions.extend([
            f"{base}-USD",
            f"{base}USD=X",
            f"{base}-USDT"  # Sometimes USDT works when USD doesn't
        ])
    elif not symbol.endswith('.US') and len(symbol) <= 5 and symbol.isupper():
        # US stocks might need .US suffix
        suggestions.append(f"{symbol}.US")

    return suggestions[:3]  # Limit to 3 suggestions

def update_ticker(conn, asset_id: int, old_symbol: str, new_symbol: str, commit: bool = False) -> bool:
    """Update an asset's ticker symbol."""
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE assets SET symbol = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s",
                (new_symbol, asset_id)
            )

            if commit:
                conn.commit()
                print(f"✅ Updated {old_symbol} → {new_symbol}")
                return True
            else:
                conn.rollback()
                print(f"🔍 Would update {old_symbol} → {new_symbol}")
                return True

    except Exception as e:
        conn.rollback()
        print(f"❌ Error updating {old_symbol}: {e}")
        return False

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Validate yfinance tickers in TimescaleDB")
    parser.add_argument('--fix', action='store_true',
                       help='Attempt to fix invalid tickers with suggestions')
    parser.add_argument('--commit', action='store_true',
                       help='Actually perform updates (default is dry-run)')
    parser.add_argument('--delay', type=float, default=0.5,
                       help='Delay between API calls in seconds (default: 0.5)')

    args = parser.parse_args()

    # Connect to database
    conn = get_database_connection()
    print("🔌 Connected to TimescaleDB")

    try:
        # Get all assets
        assets = get_all_assets(conn)
        if not assets:
            print("❌ No assets found in database")
            return

        print(f"📊 Found {len(assets)} active assets to validate")

        # Validate all tickers
        valid_assets, invalid_assets = validate_all_tickers(assets, args.delay)

        print(f"\n✅ Valid tickers: {len(valid_assets)}")
        print(f"❌ Invalid tickers: {len(invalid_assets)}")

        # Report invalid assets
        if invalid_assets:
            print(f"\n🚨 Invalid Tickers ({len(invalid_assets)}):")
            print("-" * 80)
            for asset_id, symbol, name, error in invalid_assets:
                print(f"ID {asset_id}: {symbol} ({name})")
                print(f"  Error: {error}")

                if args.fix:
                    suggestions = suggest_alternatives(symbol)
                    if suggestions:
                        print(f"  Suggestions: {', '.join(suggestions)}")

                        # Try suggestions
                        for suggestion in suggestions:
                            is_valid, _ = validate_ticker(suggestion)
                            if is_valid:
                                print(f"  ✅ Found working alternative: {suggestion}")
                                update_ticker(conn, asset_id, symbol, suggestion, args.commit)
                                break
                        else:
                            print("  ❌ No working alternatives found")
                    print()

        # Summary
        if args.commit:
            print("✅ Validation and fixes completed!")
        else:
            print("🔍 This was a dry run.")
            if invalid_assets:
                print(f"Use --fix --commit to attempt automatic fixes for {len(invalid_assets)} invalid tickers")

    finally:
        conn.close()
        print("🔌 Database connection closed")

if __name__ == "__main__":
    main()