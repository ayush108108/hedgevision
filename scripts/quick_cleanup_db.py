"""
Quick database cleanup: Delete ALL data and keep only validation assets.
This is faster than selective deletion with 1M+ records.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
from supabase import create_client

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.api.utils.assets_config import VALIDATION_ASSETS

load_dotenv()

sb = create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_KEY"))

def truncate_all_data():
    """Truncate all data tables (faster than selective delete)."""
    tables_to_truncate = [
        "price_history",
        "correlation_matrices", 
        "cointegration_results",
        "rolling_metrics",
        "assets"
    ]
    
    print("\n🗑️  Truncating all data tables...")
    for table in tables_to_truncate:
        try:
            # Delete all rows (Supabase doesn't support TRUNCATE via REST API)
            sb.table(table).delete().neq("id", 0).execute()  # Delete all where id != 0 (catches everything)
            print(f"  ✅ {table}")
        except Exception as e:
            print(f"  ⚠️  {table}: {str(e)}")
    
    print("\n✅ All data cleared!")

def main():
    print("=" * 80)
    print("SUPABASE QUICK CLEANUP - Delete All & Keep Only Validation Assets")
    print("=" * 80)
    
    # Get current counts
    try:
        assets_count = sb.table("assets").select("id", count="exact").limit(1).execute().count
        price_count = sb.table("price_history").select("id", count="exact").limit(1).execute().count
    except:
        assets_count = "unknown"
        price_count = "unknown"
    
    print(f"\nCurrent database state:")
    print(f"  Assets: {assets_count}")
    print(f"  Price history records: {price_count}")
    
    print(f"\n📋 Will keep only {len(VALIDATION_ASSETS)} validation assets:")
    for i, name in enumerate(VALIDATION_ASSETS[:10], 1):
        print(f"  {i}. {name}")
    print(f"  ... and {len(VALIDATION_ASSETS) - 10} more")
    
    print("\n" + "=" * 80)
    print("⚠️  WARNING: This will:")
    print("  1. DELETE ALL data from price_history, correlations, cointegration, rolling_metrics")
    print("  2. DELETE ALL assets")
    print("  3. You will need to repopulate with only the 50 validation assets")
    print("=" * 80)
    
    response = input("\n Proceed with complete cleanup? (yes/no): ")
    if response.lower() != "yes":
        print("Cleanup cancelled.")
        return
    
    truncate_all_data()
    
    print("\n" + "=" * 80)
    print("✅ CLEANUP COMPLETE!")
    print("=" * 80)
    print("\nNext steps:")
    print("1. Run: python scripts/setup/populate_assets.py")
    print("   (This will populate only the 50 validation assets)")
    print("2. Run: python scripts/pipelines/daily_eod_pipeline.py")
    print("   (This will fetch price data for validation assets only)")
    print("=" * 80)

if __name__ == "__main__":
    main()
