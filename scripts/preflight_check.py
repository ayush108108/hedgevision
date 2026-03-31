"""
Pre-flight check for all-time workflow

This script verifies that:
1. Supabase connection works
2. Required tables exist
3. You have asset and price data
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from api.utils.supabase_client import get_supabase_client


def check_connection():
    """Check Supabase connection."""
    print("🔍 Checking Supabase connection...")
    try:
        client = get_supabase_client()
        if not client:
            print("❌ Failed to initialize Supabase client")
            print("   Check your .env file for SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY")
            return False
        print("✅ Supabase connected")
        return client
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return False


def check_table(client, table_name):
    """Check if table exists and get row count."""
    try:
        result = client.client.table(table_name).select("*", count="exact").limit(1).execute()
        count = result.count if hasattr(result, 'count') else len(result.data or [])
        print(f"✅ Table '{table_name}' exists (estimated rows: {count}+)")
        return True
    except Exception as e:
        print(f"❌ Table '{table_name}' check failed: {e}")
        return False


def check_assets(client):
    """Check asset data."""
    print("\n🔍 Checking assets...")
    try:
        result = client.client.table("assets").select("id,symbol,name", count="exact").limit(10).execute()
        count = result.count if hasattr(result, 'count') else len(result.data or [])
        
        if count == 0:
            print("❌ No assets found in database!")
            print("   You need to populate assets table first")
            return False
        
        print(f"✅ Found {count}+ assets")
        print("   Sample assets:")
        for asset in (result.data or [])[:5]:
            print(f"     - {asset.get('symbol', 'N/A'):<12} {asset.get('name', 'N/A')}")
        return True
    except Exception as e:
        print(f"❌ Error checking assets: {e}")
        return False


def check_price_history(client):
    """Check price history data."""
    print("\n🔍 Checking price history...")
    try:
        result = client.client.table("price_history").select("*", count="exact").limit(1).execute()
        count = result.count if hasattr(result, 'count') else len(result.data or [])
        
        if count == 0:
            print("❌ No price history found!")
            print("   Run: python scripts/pipelines/yfinance_daily_incremental.py")
            return False
        
        print(f"✅ Price history exists ({count}+ records)")
        return True
    except Exception as e:
        print(f"❌ Error checking price history: {e}")
        return False


def check_correlation_matrix(client):
    """Check if correlation_matrix table exists."""
    print("\n🔍 Checking correlation_matrix table...")
    try:
        result = client.client.table("correlation_matrix").select("*", count="exact").limit(1).execute()
        count = result.count if hasattr(result, 'count') else len(result.data or [])
        
        if count > 0:
            print(f"✅ correlation_matrix exists with {count}+ records")
            print("   (You can skip correlation computation with --skip-correlation)")
        else:
            print("✅ correlation_matrix table exists (empty)")
            print("   (Will be populated by workflow)")
        return True
    except Exception as e:
        print(f"⚠️  correlation_matrix table may not exist: {e}")
        print("   The workflow will try to create it")
        return True  # Non-critical


def check_cointegration_scores(client):
    """Check if cointegration_scores table exists."""
    print("\n🔍 Checking cointegration_scores table...")
    try:
        result = client.client.table("cointegration_scores").select("*", count="exact").limit(1).execute()
        count = result.count if hasattr(result, 'count') else len(result.data or [])
        
        if count > 0:
            print(f"✅ cointegration_scores exists with {count}+ records")
        else:
            print("✅ cointegration_scores table exists (empty)")
            print("   (Will be populated by workflow)")
        return True
    except Exception as e:
        print(f"❌ cointegration_scores table missing: {e}")
        print("\n   ⚠️  IMPORTANT: Run this SQL in Supabase SQL Editor:")
        print("   File: scripts/cointegration_tables_schema.sql")
        return False


def main():
    print("=" * 80)
    print("  PRE-FLIGHT CHECK: All-Time Workflow")
    print("=" * 80 + "\n")
    
    # Check connection
    client = check_connection()
    if not client:
        print("\n❌ FAILED: Cannot connect to Supabase")
        print("\nFix:")
        print("  1. Check your .env file exists")
        print("  2. Verify SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY are set")
        return 1
    
    # Check required tables
    print("\n🔍 Checking required tables...")
    tables_ok = True
    tables_ok &= check_table(client, "assets")
    tables_ok &= check_table(client, "price_history")
    
    # Check data
    assets_ok = check_assets(client)
    prices_ok = check_price_history(client)
    
    # Check optional tables (will be created/populated by workflow)
    check_correlation_matrix(client)
    coint_ok = check_cointegration_scores(client)
    
    # Summary
    print("\n" + "=" * 80)
    print("  SUMMARY")
    print("=" * 80)
    
    if not tables_ok:
        print("❌ FAILED: Some tables are missing")
        print("\nYour database schema may be incomplete.")
        print("Contact support or check database migrations.")
        return 1
    
    if not assets_ok:
        print("❌ FAILED: No assets in database")
        print("\nYou need to populate the assets table first.")
        return 1
    
    if not prices_ok:
        print("❌ FAILED: No price history")
        print("\nRun ingestion pipeline first:")
        print("  python scripts/pipelines/yfinance_daily_incremental.py")
        return 1
    
    if not coint_ok:
        print("⚠️  WARNING: cointegration_scores table missing")
        print("\nRun this SQL file in Supabase SQL Editor:")
        print("  scripts/cointegration_tables_schema.sql")
        print("\nThen re-run this check.")
        return 1
    
    print("✅ ALL CHECKS PASSED!")
    print("\nYou're ready to run the all-time workflow:")
    print("  python scripts/master_all_time_workflow.py --lookback-days 1260 --min-correlation 0.6")
    print("\nOr start with a dry-run:")
    print("  python scripts/master_all_time_workflow.py --dry-run")
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
