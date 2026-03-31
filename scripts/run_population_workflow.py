"""
Master Workflow: Populate Database with All Metrics

This script orchestrates the complete data population workflow:
1. Precompute correlation matrices (daily/hourly, pearson/spearman)
2. Compute cointegration scores for top correlated pairs
3. Verify data integrity

Usage:
    python scripts/run_population_workflow.py [--quick]

Options:
    --quick : Run quick mode (fewer pairs, faster)
    --full  : Run full comprehensive population (default)
"""

import sys
import os
import asyncio
import argparse
from datetime import datetime
from pathlib import Path

# Add backend to path
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root / "backend"))

from dotenv import load_dotenv

# Load environment variables
load_dotenv(repo_root / ".env")
load_dotenv(repo_root / "backend" / "api" / ".env")


def print_header(message: str):
    """Print a formatted header."""
    print("\n" + "=" * 80)
    print(f"  {message}")
    print("=" * 80 + "\n")


def print_step(step: int, total: int, message: str):
    """Print a formatted step."""
    print(f"\n[{step}/{total}] {message}")
    print("-" * 80)


def run_command(command: str, description: str) -> bool:
    """Run a shell command and return success status."""
    import subprocess
    
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
            # Print last 20 lines of output
            lines = result.stdout.strip().split('\n')
            if len(lines) > 20:
                print("  [Output truncated - showing last 20 lines]")
                for line in lines[-20:]:
                    print(f"  {line}")
            else:
                for line in lines:
                    print(f"  {line}")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(f"  Error: {e}")
        if e.stdout:
            print(f"  Stdout: {e.stdout}")
        if e.stderr:
            print(f"  Stderr: {e.stderr}")
        return False


async def main():
    parser = argparse.ArgumentParser(
        description="Populate database with correlation and cointegration metrics"
    )
    parser.add_argument(
        "--mode",
        choices=["quick", "full"],
        default="full",
        help="Quick mode (10 pairs) or full mode (all pairs)"
    )
    parser.add_argument(
        "--skip-correlations",
        action="store_true",
        help="Skip correlation precomputation"
    )
    parser.add_argument(
        "--skip-cointegration",
        action="store_true",
        help="Skip cointegration computation"
    )
    parser.add_argument(
        "--run-tests",
        action="store_true",
        help="Run API E2E tests after population (default on in full mode)"
    )
    parser.add_argument(
        "--advanced-analytics",
        action="store_true",
        help="Run optional advanced analytics pipeline (rolling metrics, factors)"
    )
    args = parser.parse_args()

    print_header(f"DATABASE POPULATION WORKFLOW - {args.mode.upper()} MODE")
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Mode: {args.mode}")
    
    # Check environment
    print("\n📋 Checking environment...")
    supabase_url = os.getenv("SUPABASE_URL")
    supabase_key = (
        os.getenv("SUPABASE_SERVICE_KEY") 
        or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
        or os.getenv("SUPABASE_KEY") 
        or os.getenv("SUPABASE_ANON_KEY")
    )
    
    if not supabase_url:
        print("❌ SUPABASE_URL not set in environment")
        return 1
    if not supabase_key:
        print("❌ No Supabase key found (checked SERVICE_KEY, SERVICE_ROLE_KEY, KEY, ANON_KEY)")
        return 1
    
    print(f"✅ Supabase URL: {supabase_url[:30]}...")
    print(f"✅ Supabase Key: {'*' * 20}...")

    total_steps = 0
    if not args.skip_correlations:
        total_steps += 2  # 2 correlation methods
    if not args.skip_cointegration:
        total_steps += 1
        # plus materialized view refresh
        total_steps += 1
    total_steps += 1  # Verification
    # Optional advanced analytics
    if args.advanced_analytics:
        total_steps += 1
    # Optional tests
    should_run_tests = args.run_tests or (args.mode == "full" and not os.getenv("CI", "").lower() == "true")
    if should_run_tests:
        total_steps += 1
    
    current_step = 0
    
    # STEP 1 & 2: Precompute Correlations
    if not args.skip_correlations:
        print_header("CORRELATION MATRIX PRECOMPUTATION")
        
        # Spearman correlation (recommended for financial data)
        current_step += 1
        print_step(current_step, total_steps, "Precomputing Spearman Correlation Matrix")
        success = run_command(
            "python scripts/precompute_correlations.py --method spearman --lookback 252",
            "Spearman correlation (daily, 252-day lookback)"
        )
        if not success:
            print("\n⚠️  WARNING: Spearman correlation computation failed")
        
        # Pearson correlation (for comparison)
        current_step += 1
        print_step(current_step, total_steps, "Precomputing Pearson Correlation Matrix")
        success = run_command(
            "python scripts/precompute_correlations.py --method pearson --lookback 252",
            "Pearson correlation (daily, 252-day lookback)"
        )
        if not success:
            print("\n⚠️  WARNING: Pearson correlation computation failed")
    else:
        print("\n⏭️  Skipping correlation precomputation")
    
    # STEP 3: Populate Cointegration Data
    if not args.skip_cointegration:
        current_step += 1
        print_step(current_step, total_steps, "Computing Cointegration Tests for Top Pairs")
        
        if args.mode == "quick":
            print("  Running QUICK mode (testing first 10 pairs only)")
            # The populate_cointegration.py script already limits to 10 pairs
            success = run_command(
                "python scripts/populate_cointegration.py",
                "Cointegration tests (quick mode)"
            )
        else:
            print("  Running FULL mode (testing all significant pairs)")
            success = run_command(
                "python scripts/populate_cointegration.py --all",
                "Cointegration tests (full mode)"
            )
        
        if not success:
            print("\n⚠️  WARNING: Cointegration computation failed")
        else:
            # Refresh materialized view for latest results
            current_step += 1
            print_step(current_step, total_steps, "Refreshing materialized view: cointegration_scores_latest")
            try:
                from api.utils.supabase_client import get_supabase_client
                supabase = get_supabase_client()
                if not supabase:
                    print("  ⚠️  Supabase client unavailable; skipping refresh")
                else:
                    supabase.client.rpc("refresh_cointegration_scores_latest").execute()
                    print("  ✅ Materialized view refreshed")
            except Exception as e:
                print(f"  ⚠️  Failed to refresh materialized view: {e}")
    else:
        print("\n⏭️  Skipping cointegration computation")
    
    # Optional: Advanced analytics pipeline
    if args.advanced_analytics:
        current_step += 1
        print_step(current_step, total_steps, "Running advanced analytics pipeline (optional)")
        success = run_command(
            "python scripts/pipelines/analytics_computation_pipeline_v2.py",
            "Advanced analytics (rolling metrics, factors)"
        )
        if not success:
            print("\n⚠️  WARNING: Advanced analytics pipeline failed")

    # STEP: Verify Data
    current_step += 1
    print_step(current_step, total_steps, "Verifying Database Population")
    
    try:
        from api.utils.supabase_client import get_supabase_client
        
        supabase = get_supabase_client()
        if not supabase:
            print("❌ Failed to connect to Supabase for verification")
            return 1
        
        # Check correlation matrices
        if not args.skip_correlations:
            try:
                corr_result = supabase.client.table("correlation_matrix").select("*", count="exact").execute()
                corr_count = corr_result.count if hasattr(corr_result, 'count') else len(corr_result.data or [])
                print(f"  ✅ Correlation matrices: {corr_count} records")
            except Exception as e:
                print(f"  ⚠️  Could not verify correlation matrices: {e}")
        
        # Check cointegration scores
        if not args.skip_cointegration:
            try:
                coint_result = supabase.client.table("cointegration_scores").select("*", count="exact").execute()
                coint_count = coint_result.count if hasattr(coint_result, 'count') else len(coint_result.data or [])
                print(f"  ✅ Cointegration scores: {coint_count} records")
                
                # Count cointegrated pairs
                coint_positive = supabase.client.table("cointegration_scores").select("*", count="exact").eq("eg_is_cointegrated", 1).execute()
                coint_positive_count = coint_positive.count if hasattr(coint_positive, 'count') else len(coint_positive.data or [])
                print(f"  ✅ Cointegrated pairs: {coint_positive_count} pairs")
            except Exception as e:
                print(f"  ⚠️  Could not verify cointegration scores: {e}")
        
        print("\n✅ Database population completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Verification failed: {e}")
        return 1
    
    # Optional: Run E2E API tests
    if should_run_tests:
        current_step += 1
        print_step(current_step, total_steps, "Running E2E API tests (pytest)")
        tests_cmd = "pytest -q tests/test_real_api_endpoints.py tests/test_real_integration.py tests/test_real_business_engine.py"
        success = run_command(tests_cmd, "Pytest E2E suite")
        if not success:
            print("\n⚠️  WARNING: E2E tests reported failures")

    # Summary
    print_header("WORKFLOW SUMMARY")
    print(f"Completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n📊 Next Steps:")
    print(f"  1. Start the API server: python backend/api/run.py")
    print(f"  2. View screener: http://localhost:8000/api/screener/status")
    print(f"  3. (Optional) Run API tests: pytest tests/test_real_api_endpoints.py")
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
