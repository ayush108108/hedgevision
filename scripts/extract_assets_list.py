"""
Extract complete asset list from Supabase with yfinance tickers and descriptive names.

Output:
- scripts/output/assets_list.csv (full manifest with all fields)
- Console report: asset count, coverage, validation

Usage:
    python scripts/extract_assets_list.py
    python scripts/extract_assets_list.py --output assets_manifest.csv
    python scripts/extract_assets_list.py --limit 50  # Test with 50 assets
"""

import sys
import os
from pathlib import Path
from typing import Dict, List, Optional
import csv
import argparse
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables from .env
root_env = Path(__file__).parent.parent / ".env"
if root_env.exists():
    load_dotenv(root_env)

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))


def get_supabase_client():
    """Initialize Supabase client."""
    url = os.getenv("SUPABASE_URL")
    key = (
        os.getenv("SUPABASE_SERVICE_KEY")
        or os.getenv("SUPABASE_KEY")
        or os.getenv("SUPABASE_ANON_KEY")
    )
    if not url or not key:
        raise RuntimeError("SUPABASE_URL and one of SUPABASE_SERVICE_KEY/SUPABASE_KEY/SUPABASE_ANON_KEY must be set")
    return create_client(url, key)


def get_all_assets(limit: Optional[int] = None) -> List[Dict]:
    """
    Fetch all assets from Supabase.
    
    Returns:
        List of asset dicts with: id, symbol, name, description, 
        yfinance_ticker, exchange, category, is_active, etc.
    """
    client = get_supabase_client()

    print("[*] Querying Supabase for all assets...")

    # Fetch only the columns present in the new schema
    query = client.table("assets").select(
        "name,yfinance_ticker,is_active"
    ).order("yfinance_ticker")

    if limit:
        query = query.limit(limit)

    response = query.execute()
    assets = response.data

    print(f"[+] Found {len(assets)} assets")
    if assets:
        print(f"[DEBUG] First asset keys: {list(assets[0].keys())}")
        print(f"[DEBUG] First asset: {assets[0]}")
    return assets


def build_asset_manifest(assets: List[Dict]) -> List[Dict]:
    """
    Build asset manifest with friendly names and all ticker mappings.
    
    Returns:
        List of enhanced asset records with normalized naming
    """
    manifest = []
    
    for asset in assets:
        # Only use name, yfinance_ticker, is_active
        record = {
            "name": asset.get("name"),
            "yfinance_ticker": asset.get("yfinance_ticker"),
            "is_active": asset.get("is_active", True),
        }
        manifest.append(record)
    
    return manifest


def export_to_csv(manifest: List[Dict], output_path: str) -> None:
    """Export asset manifest to CSV."""
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    
    if not manifest:
        print("[-] No assets to export")
        return
    
    fieldnames = [
        "name",
        "yfinance_ticker",
        "is_active",
    ]
    
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(manifest)
    
    print(f"[+] Exported to: {output_path}")


def print_summary(manifest: List[Dict]) -> None:
    """Print summary statistics."""
    total = len(manifest)
    active = sum(1 for a in manifest if a["is_active"])

    print(f"\n[*] Total Assets: {total}")
    print(f"[+] Active Assets: {active}")
    print(f"[!] Inactive Assets: {total - active}")

    print(f"\n[*] Sample Assets (first 10):")
    for i, asset in enumerate(manifest[:10], 1):
        yf = asset['yfinance_ticker'][:12] if asset['yfinance_ticker'] else "N/A"
        print(
            f"    {i:2}. {asset['name'][:25]:25} | YF: {yf:12} | Active: {asset['is_active']}"
        )

    # Missing yfinance tickers
    missing = [a for a in manifest if not a["yfinance_ticker"]]
    if missing:
        print(f"\n[!] Missing yfinance tickers ({len(missing)}):")
        for asset in missing[:10]:
            print(f"    {asset['name']}")
        if len(missing) > 10:
            print(f"    ... and {len(missing) - 10} more")
    else:
        print(f"\n[+] All {total} assets have yfinance tickers!")
    
    print("\n" + "="*70 + "\n")


def validate_manifest(manifest: List[Dict]) -> bool:
    """
    Validate manifest for completeness.
    
    Returns:
        True if valid, False otherwise
    """
    issues = []
    
    # Check minimum asset count
    if len(manifest) < 2:  # For test with limit 2
        issues.append(f"[-] Only {len(manifest)} assets (expected >= 2)")
    else:
        issues.append(f"[+] Asset count: {len(manifest)} (>= 2)")
    
    # Check for NULL yfinance_ticker
    missing_yf = [a for a in manifest if not a.get("yfinance_ticker")]
    if missing_yf:
        issues.append(f"[!] {len(missing_yf)} assets missing yfinance_ticker")
    else:
        issues.append(f"[+] All assets have yfinance_ticker")
    
    # Check for NULL name
    missing_names = [a for a in manifest if not a.get("name")]
    if missing_names:
        issues.append(f"[!] {len(missing_names)} assets missing name")
    else:
        issues.append(f"[+] All assets have name")
    
    print("\n[*] VALIDATION REPORT:")
    for issue in issues:
        print(f"    {issue}")
    
    # Overall pass/fail
    has_critical_issues = any("[-]" in issue for issue in issues)
    return not has_critical_issues


def main():
    parser = argparse.ArgumentParser(description="Extract asset list from Supabase")
    parser.add_argument(
        "--output",
        default="scripts/output/assets_list.csv",
        help="Output CSV file path",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit number of assets (for testing)",
    )
    
    args = parser.parse_args()
    
    print("\n" + "="*70)
    print("ASSET LIST EXTRACTION")
    print("="*70 + "\n")
    
    try:
        # Step 1: Fetch assets
        assets = get_all_assets(limit=args.limit)
        
        if not assets:
            print("[-] No assets found in database")
            return 1
        
        # Step 2: Build manifest
        print("[*] Building asset manifest...")
        manifest = build_asset_manifest(assets)
        
        # Step 3: Print summary
        print_summary(manifest)
        
        # Step 4: Validate
        is_valid = validate_manifest(manifest)
        
        # Step 5: Export
        print("[*] Exporting to CSV...")
        export_to_csv(manifest, args.output)
        
        # Final status
        if is_valid:
            print("\n[+] SUCCESS: Asset list extraction complete")
            print(f"    Output: {args.output}")
            print(f"    Assets: {len(manifest)}")
            return 0
        else:
            print("\n[!] WARNING: Asset list extracted but has validation issues")
            print(f"    Output: {args.output}")
            print(f"    Review the validation report above")
            return 0  # Still export even if has warnings
    
    except Exception as e:
        print(f"\n[-] ERROR: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
