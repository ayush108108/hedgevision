"""
Direct database cleanup using PostgreSQL TRUNCATE (much faster than REST API).
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.api.utils.assets_config import VALIDATION_ASSETS

load_dotenv()

def truncate_tables():
    """Truncate tables using direct PostgreSQL connection."""
    db_url = os.getenv("SUPABASE_DB_URL")
    
    print("\n🔗 Connecting to database...")
    conn = psycopg2.connect(db_url)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    cur = conn.cursor()
    
    # Tables to truncate (in order to handle foreign keys)
    tables = [
        "correlation_matrix",
        "cointegration_tests",
        "rolling_metrics",
        "price_history",
        "assets"
    ]
    
    print("\n🗑️  Truncating tables...")
    for table in tables:
        try:
            print(f"  Truncating {table}...", end=" ")
            cur.execute(f"TRUNCATE TABLE {table} CASCADE")
            print("✅")
        except Exception as e:
            print(f"⚠️  Error: {e}")
    
    # Get row counts
    print("\n📊 Verifying cleanup:")
    for table in tables:
        try:
            cur.execute(f"SELECT COUNT(*) FROM {table}")
            count = cur.fetchone()[0]
            print(f"  {table}: {count} rows")
        except Exception as e:
            print(f"  {table}: Error - {e}")
    
    cur.close()
    conn.close()
    print("\n✅ Database cleaned!")

def main():
    print("=" * 80)
    print("SUPABASE DATABASE TRUNCATE - Fast Cleanup")
    print("=" * 80)
    
    print(f"\n📋 Will repopulate with {len(VALIDATION_ASSETS)} validation assets")
    print("\n" + "=" * 80)
    print("⚠️  WARNING: This will TRUNCATE all tables:")
    print("  - price_history")
    print("  - correlation_matrix")
    print("  - cointegration_tests")
    print("  - rolling_metrics")
    print("  - assets")
    print("\nAll data will be permanently deleted!")
    print("=" * 80)
    
    response = input("\nProceed with TRUNCATE? (yes/no): ")
    if response.lower() != "yes":
        print("Cleanup cancelled.")
        return
    
    truncate_tables()
    
    print("\n" + "=" * 80)
    print("✅ CLEANUP COMPLETE!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. python scripts/setup/populate_assets.py")
    print("2. python scripts/pipelines/daily_eod_pipeline.py")
    print("=" * 80)

if __name__ == "__main__":
    main()
