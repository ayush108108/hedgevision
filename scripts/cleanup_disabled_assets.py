"""
Clean up disabled assets from Supabase database to free up storage.
Removes assets that are not in the VALIDATION_ASSETS list and all their associated data.
"""

import os
import sys
from pathlib import Path
from typing import List, Set
from dotenv import load_dotenv
from supabase import create_client

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backend.api.utils.assets import name_to_symbol
from backend.api.utils.assets_config import VALIDATION_ASSETS, get_validation_status

load_dotenv()

# Initialize Supabase client
supabase = create_client(
    os.getenv("SUPABASE_URL"),
    os.getenv("SUPABASE_SERVICE_KEY")
)

def get_disabled_asset_symbols() -> Set[str]:
    """Get symbols of assets that should be removed (not in validation list)."""
    # Get all asset symbols from name_to_symbol
    all_symbols = set(name_to_symbol.values())
    
    # Get validation asset symbols
    validation_symbols = {name_to_symbol[name] for name in VALIDATION_ASSETS if name in name_to_symbol}
    
    # Return the difference (assets to remove)
    disabled_symbols = all_symbols - validation_symbols
    
    print(f"Total assets defined: {len(all_symbols)}")
    print(f"Validation assets: {len(validation_symbols)}")
    print(f"Assets to remove: {len(disabled_symbols)}")
    
    return disabled_symbols

def get_disabled_asset_ids() -> tuple[List[int], List[str]]:
    """Get asset IDs from Supabase for disabled assets (not in validation list)."""
    # Get validation asset names
    validation_names = set(VALIDATION_ASSETS)
    
    # Query all assets from database
    response = supabase.table("assets").select("id, name, yfinance_ticker").execute()
    
    disabled_assets = []
    disabled_names = []
    
    for asset in response.data:
        # Check if asset name is NOT in validation list
        if asset["name"] not in validation_names:
            disabled_assets.append(asset["id"])
            disabled_names.append(f"{asset['name']} ({asset['yfinance_ticker']})")
    
    print(f"\nTotal assets in database: {len(response.data)}")
    print(f"Validation assets to keep: {len(validation_names)}")
    print(f"Assets to remove: {len(disabled_assets)}")
    
    if disabled_assets:
        print(f"\nFirst 10 assets to be removed:")
        for name in disabled_names[:10]:
            print(f"  - {name}")
        if len(disabled_names) > 10:
            print(f"  ... and {len(disabled_names) - 10} more")
    
    return disabled_assets, disabled_names

def cleanup_price_history(asset_ids: List[int]) -> int:
    """Delete price history data for disabled assets."""
    if not asset_ids:
        return 0
    
    print(f"\nCleaning up price_history for {len(asset_ids)} assets...")
    
    # Delete in batches to avoid timeout
    batch_size = 50
    total_deleted = 0
    
    for i in range(0, len(asset_ids), batch_size):
        batch = asset_ids[i:i + batch_size]
        response = supabase.table("price_history").delete().in_("asset_id", batch).execute()
        deleted_count = len(response.data) if response.data else 0
        total_deleted += deleted_count
        print(f"  Batch {i//batch_size + 1}: Deleted {deleted_count} price records")
    
    print(f"Total price_history records deleted: {total_deleted}")
    return total_deleted

def cleanup_correlation_matrices(asset_ids: List[int]) -> int:
    """Delete correlation matrix data involving disabled assets."""
    if not asset_ids:
        return 0
    
    print(f"\nCleaning up correlation_matrices...")
    
    # Delete correlations where either asset is disabled
    total_deleted = 0
    
    # Delete rows where asset1_id is disabled
    response1 = supabase.table("correlation_matrices").delete().in_("asset1_id", asset_ids).execute()
    count1 = len(response1.data) if response1.data else 0
    
    # Delete rows where asset2_id is disabled
    response2 = supabase.table("correlation_matrices").delete().in_("asset2_id", asset_ids).execute()
    count2 = len(response2.data) if response2.data else 0
    
    total_deleted = count1 + count2
    print(f"Total correlation_matrices records deleted: {total_deleted}")
    return total_deleted

def cleanup_cointegration_results(asset_ids: List[int]) -> int:
    """Delete cointegration results involving disabled assets."""
    if not asset_ids:
        return 0
    
    print(f"\nCleaning up cointegration_results...")
    
    # Delete cointegration pairs where either asset is disabled
    total_deleted = 0
    
    # Delete rows where asset1_id is disabled
    response1 = supabase.table("cointegration_results").delete().in_("asset1_id", asset_ids).execute()
    count1 = len(response1.data) if response1.data else 0
    
    # Delete rows where asset2_id is disabled
    response2 = supabase.table("cointegration_results").delete().in_("asset2_id", asset_ids).execute()
    count2 = len(response2.data) if response2.data else 0
    
    total_deleted = count1 + count2
    print(f"Total cointegration_results records deleted: {total_deleted}")
    return total_deleted

def cleanup_rolling_metrics(asset_ids: List[int]) -> int:
    """Delete rolling metrics for disabled assets."""
    if not asset_ids:
        return 0
    
    print(f"\nCleaning up rolling_metrics...")
    
    response = supabase.table("rolling_metrics").delete().in_("asset_id", asset_ids).execute()
    deleted_count = len(response.data) if response.data else 0
    
    print(f"Total rolling_metrics records deleted: {deleted_count}")
    return deleted_count

def cleanup_assets_table(asset_ids: List[int]) -> int:
    """Delete disabled assets from assets table."""
    if not asset_ids:
        return 0
    
    print(f"\nCleaning up assets table...")
    
    response = supabase.table("assets").delete().in_("id", asset_ids).execute()
    deleted_count = len(response.data) if response.data else 0
    
    print(f"Total assets deleted: {deleted_count}")
    return deleted_count

def main():
    """Main cleanup function."""
    print("=" * 80)
    print("SUPABASE DATABASE CLEANUP - Remove Disabled Assets")
    print("=" * 80)
    
    # Show validation configuration
    config = get_validation_status()
    print(f"\nValidation Configuration:")
    print(f"  Limit Enabled: {config['limit_enabled']}")
    print(f"  Max Assets: {config['max_assets']}")
    print(f"  Note: {config['note']}")
    
    # Get disabled asset symbols
    print("\n" + "-" * 80)
    
    # Get asset IDs from database
    asset_ids, disabled_names = get_disabled_asset_ids()
    
    if not asset_ids:
        print("\n✅ No disabled assets found in database. Nothing to clean up.")
        return
    
    # Confirm before deletion
    print("\n" + "=" * 80)
    print("⚠️  WARNING: This will permanently delete:")
    print(f"  - {len(asset_ids)} assets")
    print(f"  - All price history data for these assets")
    print(f"  - All correlation matrices involving these assets")
    print(f"  - All cointegration results involving these assets")
    print(f"  - All rolling metrics for these assets")
    print("=" * 80)
    
    response = input("\nProceed with cleanup? (yes/no): ")
    if response.lower() != "yes":
        print("Cleanup cancelled.")
        return
    
    # Perform cleanup in order (related data first, then assets)
    print("\n" + "=" * 80)
    print("STARTING CLEANUP...")
    print("=" * 80)
    
    stats = {
        "price_history": cleanup_price_history(asset_ids),
        "correlation_matrices": cleanup_correlation_matrices(asset_ids),
        "cointegration_results": cleanup_cointegration_results(asset_ids),
        "rolling_metrics": cleanup_rolling_metrics(asset_ids),
        "assets": cleanup_assets_table(asset_ids)
    }
    
    # Summary
    print("\n" + "=" * 80)
    print("CLEANUP SUMMARY")
    print("=" * 80)
    print(f"Assets removed: {stats['assets']}")
    print(f"Price history records deleted: {stats['price_history']}")
    print(f"Correlation matrices deleted: {stats['correlation_matrices']}")
    print(f"Cointegration results deleted: {stats['cointegration_results']}")
    print(f"Rolling metrics deleted: {stats['rolling_metrics']}")
    print(f"\nTotal records deleted: {sum(stats.values())}")
    print("\n✅ Cleanup complete! Database storage freed up.")
    print("=" * 80)

if __name__ == "__main__":
    main()
