#!/usr/bin/env python3
"""
Bootstrap assets into TimescaleDB from assets_mapping_yfi file.

This script reads the assets_mapping_yfi file and inserts all assets
into the TimescaleDB assets table. It handles duplicates gracefully.

Usage:
    python scripts/bootstrap_assets_timescale.py [--commit]

Without --commit it runs a dry-run preview.
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Add backend to path
backend_dir = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_dir))

try:
    import psycopg2
    from psycopg2.extras import execute_values
    from dotenv import load_dotenv
except ImportError as e:
    print(f"Missing required packages: {e}")
    print("Install with: pip install psycopg2-binary python-dotenv")
    sys.exit(1)

# Load environment variables
load_dotenv()

def parse_assets_mapping(file_path: str) -> List[Tuple[str, str]]:
    """
    Parse the assets_mapping_yfi file to extract asset names and yfinance tickers.

    Returns:
        List of tuples (name, yfinance_ticker)
    """
    assets = []

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Find the INSERT statement and extract values
        insert_match = re.search(r"INSERT INTO assets \(name, yfinance_ticker, is_active\)\s*VALUES\s*(.*?);", content, re.DOTALL)
        if not insert_match:
            print("Could not find INSERT statement in assets_mapping_yfi file")
            return assets

        values_str = insert_match.group(1)

        # Parse individual value tuples
        # This regex handles the complex SQL value format
        value_pattern = r"\(\s*'([^']*(?:''[^']*)*)'\s*,\s*'([^']*(?:''[^']*)*)'\s*,\s*1\s*\)"
        matches = re.findall(value_pattern, values_str)

        for match in matches:
            name = match[0].replace("''", "'")  # Unescape single quotes
            ticker = match[1].replace("''", "'")  # Unescape single quotes
            assets.append((name, ticker))

        print(f"Parsed {len(assets)} assets from mapping file")

    except Exception as e:
        print(f"Error parsing assets mapping file: {e}")
        return assets

    return assets

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

def check_existing_assets(conn) -> set:
    """Get set of existing symbol values."""
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT symbol FROM assets WHERE symbol IS NOT NULL")
            existing = {row[0] for row in cursor.fetchall()}
        return existing
    except Exception as e:
        print(f"Error checking existing assets: {e}")
        return set()

def insert_assets(conn, assets: List[Tuple[str, str]], commit: bool = False) -> int:
    """Insert assets into database using upsert."""
    if not assets:
        print("No assets to insert")
        return 0

    inserted_count = 0

    try:
        with conn.cursor() as cursor:
            # Prepare data for bulk insert
            # Using upsert to handle duplicates
            values = [(name, ticker, True) for name, ticker in assets]

            query = """
            INSERT INTO assets (name, symbol, is_active)
            VALUES %s
            ON CONFLICT (symbol)
            DO UPDATE SET
                name = EXCLUDED.name,
                is_active = EXCLUDED.is_active,
                updated_at = CURRENT_TIMESTAMP
            """

            execute_values(cursor, query, values)
            inserted_count = len(values)

            if commit:
                conn.commit()
                print(f"✅ Successfully inserted/updated {inserted_count} assets")
            else:
                conn.rollback()
                print(f"🔍 Dry run: Would insert/update {inserted_count} assets")

    except Exception as e:
        conn.rollback()
        print(f"❌ Error inserting assets: {e}")
        return 0

    return inserted_count

def main():
    parser = argparse.ArgumentParser(description="Bootstrap assets into TimescaleDB")
    parser.add_argument('--commit', action='store_true',
                       help='Actually perform the insertions (default is dry-run)')
    parser.add_argument('--mapping-file', default='assets_mapping_yfi',
                       help='Path to assets mapping file (default: assets_mapping_yfi)')

    args = parser.parse_args()

    # Check if mapping file exists
    mapping_file = Path(args.mapping_file)
    if not mapping_file.exists():
        print(f"❌ Assets mapping file not found: {mapping_file}")
        sys.exit(1)

    print(f"📁 Using assets mapping file: {mapping_file}")

    # Parse assets from file
    assets = parse_assets_mapping(str(mapping_file))
    if not assets:
        print("❌ No assets found in mapping file")
        sys.exit(1)

    print(f"📊 Found {len(assets)} assets to process")

    # Connect to database
    conn = get_database_connection()
    print("🔌 Connected to TimescaleDB")

    try:
        # Check existing assets
        existing_tickers = check_existing_assets(conn)
        print(f"📈 Found {len(existing_tickers)} existing assets in database")

        # Filter out existing assets
        new_assets = [(name, ticker) for name, ticker in assets if ticker not in existing_tickers]
        existing_count = len(assets) - len(new_assets)

        print(f"🆕 {len(new_assets)} new assets to insert")
        print(f"🔄 {existing_count} existing assets (will be updated)")

        if new_assets:
            print("\n📝 New assets to be inserted:")
            for name, ticker in new_assets[:10]:  # Show first 10
                print(f"  - {name} ({ticker})")
            if len(new_assets) > 10:
                print(f"  ... and {len(new_assets) - 10} more")

        # Insert assets
        inserted = insert_assets(conn, assets, args.commit)

        if args.commit:
            print("✅ Assets bootstrap completed successfully!")
        else:
            print("🔍 This was a dry run. Use --commit to actually insert the assets.")

    finally:
        conn.close()
        print("🔌 Database connection closed")

if __name__ == "__main__":
    main()