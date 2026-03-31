"""
Master All-Time Workflow: Correlation → Filter → Cointegration

This script orchestrates the complete all-time pair analysis workflow:
1. Compute correlation matrix for all 20,000 pairs (200 × 199 / 2) using maximum available history
2. Filter pairs by correlation threshold (default >= 0.6)
3. Run cointegration tests ONLY on the filtered pairs (typically 5,000+ pairs)
4. Store results in cointegration_scores table

Strategy:
- "All-time" = use maximum available historical data (e.g., 5-10 years)
- Reduces cointegration workload from 20,000 pairs → ~5,000 correlated pairs
- Results can be used for incremental updates later

Usage (PowerShell):
  # Full all-time run with default settings
  python scripts/master_all_time_workflow.py

  # Custom threshold and lookback
  python scripts/master_all_time_workflow.py --min-correlation 0.7 --lookback-days 2520

  # Dry-run to see filtered pairs without running cointegration
  python scripts/master_all_time_workflow.py --dry-run

Examples:
  # Standard 5-year all-time analysis (200+ assets, 5K+ pairs)
  python scripts/master_all_time_workflow.py --lookback-days 1260 --min-correlation 0.6

  # Quick test with 2 years (20 assets, screening)
  python scripts/master_all_time_workflow.py --lookback-days 504 --limit-assets 20
"""

from __future__ import annotations

import sys
import os
import argparse
import subprocess
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, List, Tuple

import pandas as pd
import numpy as np

# Add repo root to path
repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, repo_root)

from api.utils.supabase_client import get_supabase_client
from api.utils.assets import name_to_symbol


def print_header(message: str):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f"  {message}")
    print("=" * 80 + "\n")


def print_step(step: int, total: int, message: str):
    """Print a formatted step."""
    print(f"\n[STEP {step}/{total}] {message}")
    print("-" * 80)


def run_command(command: str, description: str) -> bool:
    """Run a shell command and return success status."""
    print(f"\n▶ Running: {description}")
    print(f"  Command: {command}")
    
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            capture_output=True,
            text=True
        )
        print(f"✅ {description} - SUCCESS")
        if result.stdout:
            # Print last 30 lines of output
            lines = result.stdout.strip().split('\n')
            if len(lines) > 30:
                print("  [Output truncated - showing last 30 lines]")
                for line in lines[-30:]:
                    print(f"  {line}")
            else:
                for line in lines:
                    print(f"  {line}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(f"  Error: {e}")
        if e.stdout:
            print(f"  Stdout: {e.stdout[-1000:]}")  # Last 1000 chars
        if e.stderr:
            print(f"  Stderr: {e.stderr[-1000:]}")
        return False


def extract_pairs_from_correlation_matrix(
    supabase,
    min_correlation: float,
    method: str = "spearman",
    granularity: str = "daily"
) -> List[Tuple[str, str, float]]:
    """
    Extract pairs from stored correlation_matrix that meet the threshold.
    
    Returns:
        List of tuples: (asset1_symbol, asset2_symbol, correlation_value)
    """
    print(f"  Fetching correlation matrix (method={method}, granularity={granularity})...")
    
    try:
        # Get latest correlation matrix
        matrix_row = supabase.get_correlation_matrix(
            granularity=granularity,
            method=method,
            max_age_hours=24 * 365  # Accept up to 1 year old for all-time
        )
        
        if not matrix_row:
            print("  ❌ No correlation matrix found in database!")
            print("  Run: python scripts/precompute_correlations.py --method spearman --lookback 1260")
            return []
        
        correlation_matrix = matrix_row.get("correlation_matrix", {})
        if not correlation_matrix:
            print("  ❌ Empty correlation matrix!")
            return []
        
        # Extract pairs meeting threshold
        pairs = []
        processed_pairs = set()
        
        for asset1, correlations in correlation_matrix.items():
            if not isinstance(correlations, dict):
                continue
            
            for asset2, corr_value in correlations.items():
                if asset1 == asset2:
                    continue
                
                # Avoid duplicates (A-B vs B-A)
                pair_key = tuple(sorted([asset1, asset2]))
                if pair_key in processed_pairs:
                    continue
                processed_pairs.add(pair_key)
                
                # Check threshold
                try:
                    corr_float = float(corr_value)
                    # Skip NaN
                    if corr_float != corr_float:
                        continue
                    
                    abs_corr = abs(corr_float)
                    # Include both positively and negatively correlated pairs (including inversely correlated)
                    if abs_corr >= min_correlation:
                        pairs.append((asset1, asset2, corr_float))
                except (ValueError, TypeError):
                    continue
        
        # Sort by absolute correlation descending
        pairs.sort(key=lambda x: abs(x[2]), reverse=True)
        
        print(f"  ✅ Found {len(pairs)} pairs with |correlation| >= {min_correlation}")
        return pairs
        
    except Exception as e:
        print(f"  ❌ Error extracting pairs: {e}")
        return []


def save_filtered_pairs_manifest(
    pairs: List[Tuple[str, str, float]],
    output_path: Path,
    metadata: Dict
):
    """Save filtered pairs to a JSON manifest file."""
    manifest = {
        "metadata": metadata,
        "pairs": [
            {
                "asset1": p[0],
                "asset2": p[1],
                "correlation": p[2],
                "abs_correlation": abs(p[2])
            }
            for p in pairs
        ]
    }
    
    with open(output_path, "w") as f:
        json.dump(manifest, f, indent=2)
    
    print(f"  ✅ Saved filtered pairs manifest to: {output_path}")


def main():
    parser = argparse.ArgumentParser(
        description="Master all-time workflow: correlation → filter → cointegration"
    )
    
    # Correlation parameters
    parser.add_argument("--lookback-days", type=int, default=1260,
                       help="Lookback period in days for all-time analysis (default: 1260 = ~5 years)")
    parser.add_argument("--limit-assets", type=int, default=50,
                       help="Max number of assets to include (default: 50)")
    parser.add_argument("--symbol-suffix", type=str, default=".US",
                       help="Filter assets by symbol suffix (default: .US)")
    parser.add_argument("--granularity", type=str, default="daily",
                       choices=["daily"], help="Data granularity (default: daily)")
    
    # Filtering parameters
        parser.add_argument("--min-correlation", type=float, default=0.3,
                           help="Minimum absolute correlation to include pair (default: 0.3)")
    parser.add_argument("--correlation-method", type=str, default="spearman",
                       choices=["pearson", "spearman"],
                       help="Correlation method to use for filtering (default: spearman)")
    
    # Cointegration parameters
    parser.add_argument("--cointegration-lookback", type=int, default=None,
                       help="Lookback for cointegration tests (default: same as --lookback-days)")
    parser.add_argument("--batch-insert", type=int, default=50,
                       help="Batch size for cointegration inserts (default: 50)")
    parser.add_argument("--sleep", type=float, default=0.1,
                       help="Sleep between batches in seconds (default: 0.1)")
    
    # Workflow control
    parser.add_argument("--skip-correlation", action="store_true",
                       help="Skip correlation computation (use existing matrix)")
    parser.add_argument("--skip-cointegration", action="store_true",
                       help="Skip cointegration tests (only compute correlations)")
    parser.add_argument("--dry-run", action="store_true",
                       help="Show filtered pairs without running cointegration")
    parser.add_argument("--output-manifest", type=str,
                       default="filtered_pairs_manifest.json",
                       help="Output file for filtered pairs manifest")
    
    args = parser.parse_args()
    
    # Set cointegration lookback to match correlation if not specified
    if args.cointegration_lookback is None:
        args.cointegration_lookback = args.lookback_days
    
    # Track workflow start time (UTC) for accurate per-run summaries
    workflow_started_at = datetime.now(timezone.utc)

    print_header("MASTER ALL-TIME WORKFLOW")
    print(f"Started at: {workflow_started_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\nConfiguration:")
    print(f"  Lookback period:        {args.lookback_days} days (~{args.lookback_days/252:.1f} years)")
    print(f"  Asset limit:            {args.limit_assets} symbols (suffix: {args.symbol_suffix})")
        print(f"  Correlation threshold:  >= 0.3 for pairs, >= 0.6 for cointegration ({args.correlation_method})")
    print(f"  Cointegration lookback: {args.cointegration_lookback} days")
    print(f"  Batch size:             {args.batch_insert}")
    print(f"  Dry run:                {args.dry_run}")
    
    total_steps = 3
    if args.skip_correlation:
        total_steps -= 1
    if args.skip_cointegration or args.dry_run:
        total_steps -= 1
    
    current_step = 0
    
    # Initialize Supabase
    print("\n📋 Checking environment...")
    supabase = get_supabase_client()
    if not supabase:
        print("❌ Failed to connect to Supabase")
        return 1
    print("✅ Supabase connected")
    
    # STEP 1: Compute correlation matrix (all pairs, all-time)
    if not args.skip_correlation:
        current_step += 1
        print_step(current_step, total_steps, "Compute All-Time Correlation Matrix")
        
        # Compute both Spearman and Pearson for all-time
        for method in ["spearman", "pearson"]:
            cmd = (
                f"python scripts/precompute_correlations.py "
                f"--method {method} "
                f"--lookback {args.lookback_days} "
                f"--granularity {args.granularity}"
            )
            success = run_command(
                cmd,
                f"Correlation matrix ({method}, {args.lookback_days}d lookback)"
            )
            if not success:
                print(f"\n⚠️  WARNING: {method} correlation failed")
    
    # STEP 2: Extract and filter pairs from correlation matrix
    current_step += 1
    print_step(current_step, total_steps, f"Filter Pairs (correlation >= {args.min_correlation})")
    
    filtered_pairs = extract_pairs_from_correlation_matrix(
        supabase,
        min_correlation=args.min_correlation,
        method=args.correlation_method,
        granularity=args.granularity
    )
    
    if not filtered_pairs:
        print("\n❌ No pairs found meeting correlation threshold!")
        print(f"Try lowering --min-correlation (current: {args.min_correlation})")
        return 1
    
    print(f"\n📊 Filtered pairs summary:")
    print(f"  Total pairs meeting threshold: {len(filtered_pairs)}")
    print(f"  Top 10 by absolute correlation:")
    for i, (a1, a2, corr) in enumerate(filtered_pairs[:10], 1):
        print(f"    {i:2d}. {a1:<12} vs {a2:<12} : {corr:+.4f}")
    
    # Save manifest
    manifest_path = Path(repo_root) / "scripts" / args.output_manifest
    save_filtered_pairs_manifest(
        filtered_pairs,
        manifest_path,
        metadata={
            "created_at": datetime.now(timezone.utc).isoformat(),
            "lookback_days": args.lookback_days,
            "min_correlation": args.min_correlation,
            "correlation_method": args.correlation_method,
            "granularity": args.granularity,
            "total_pairs": len(filtered_pairs),
            "symbol_suffix": args.symbol_suffix,
            "limit_assets": args.limit_assets
        }
    )
    
    if args.dry_run:
        print("\n✅ Dry-run complete! Filtered pairs saved to manifest.")
        print(f"To run cointegration on these {len(filtered_pairs)} pairs, remove --dry-run flag")
        return 0
    
    if args.skip_cointegration:
        print("\n⏭️  Skipping cointegration tests (--skip-cointegration flag)")
        return 0
    
    # STEP 3: Run cointegration tests on filtered pairs only
    current_step += 1
    print_step(current_step, total_steps, f"Run Cointegration Tests on {len(filtered_pairs)} Filtered Pairs")
    
    # Build a temp file with pair list for populate_cointegration to use
    # IMPORTANT: Need to map names to symbols
    pairs_file = Path(repo_root) / "scripts" / ".filtered_pairs_temp.txt"
    pairs_written = 0
    with open(pairs_file, "w") as f:
        for a1_name, a2_name, _ in filtered_pairs:
            # Map names to symbols
            a1_symbol = name_to_symbol.get(a1_name, a1_name)
            a2_symbol = name_to_symbol.get(a2_name, a2_name)
            f.write(f"{a1_symbol},{a2_symbol}\n")
            pairs_written += 1
    
    print(f"  Created temporary pairs file: {pairs_file} ({pairs_written} pairs)")
    
    cmd = (
        f"python scripts/populate_cointegration.py "
        f"--from-pairs-file {pairs_file} "
        f"--lookback-days {args.cointegration_lookback} "
        f"--granularity {args.granularity} "
        f"--store-all-pairs "
        f"--batch-insert {args.batch_insert} "
        f"--sleep {args.sleep}"
    )
    
    success = run_command(
        cmd,
        f"Cointegration tests on {len(filtered_pairs)} filtered pairs"
    )
    
    # Cleanup temp file
    try:
        pairs_file.unlink()
        print(f"  Cleaned up temporary pairs file")
    except Exception:
        pass
    
    if not success:
        print("\n⚠️  WARNING: Cointegration computation failed")
        return 1
    
    # STEP 4: Summary and verification
    print_header("WORKFLOW SUMMARY")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Query results
    try:
        # Restrict counts to JUST this workflow run using created_at >= workflow_started_at
        started_iso = workflow_started_at.isoformat()

        # All records created in this run
        run_all = (
            supabase.client
            .table("cointegration_scores")
            .select("*", count="exact")
            .gte("created_at", started_iso)
            .execute()
        )
        run_total_records = run_all.count if hasattr(run_all, 'count') else len(run_all.data or [])

        # Cointegrated records (eg_is_cointegrated = True) created in this run
        run_coint_true = (
            supabase.client
            .table("cointegration_scores")
            .select("*", count="exact")
            .gte("created_at", started_iso)
            .eq("eg_is_cointegrated", 1)
            .execute()
        )
        run_coint_true_count = run_coint_true.count if hasattr(run_coint_true, 'count') else len(run_coint_true.data or [])

        # Use tested count from DB if available (with --store-all-pairs), else fall back to filtered_pairs length
        tested_count = run_total_records if run_total_records > 0 else len(filtered_pairs)
        rate = (run_coint_true_count / tested_count * 100.0) if tested_count else 0.0

        print(f"\n📊 Results (this run):")
        print(f"  Total pairs tested:       {tested_count}")
        print(f"  Cointegration records:    {run_total_records}")
        print(f"  Cointegrated pairs:       {run_coint_true_count}")
        print(f"  Cointegration rate:       {rate:.1f}%")
    except Exception as e:
        print(f"\n⚠️  Could not verify results: {e}")
    
    print(f"\n📝 Next Steps:")
    print(f"  1. Review results in Supabase cointegration_scores table")
    print(f"  2. Check filtered pairs manifest: {manifest_path}")
    print(f"  3. Start API server: python backend/api/run.py")
    print(f"  4. View screener: http://localhost:8000/api/screener/status")
    print(f"\n📄 For incremental updates, save this configuration:")
    print(f"  - Lookback: {args.lookback_days} days")
    print(f"  - Threshold: {args.min_correlation}")
    print(f"  - Method: {args.correlation_method}")
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
