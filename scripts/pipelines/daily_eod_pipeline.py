"""
Daily EOD Data Pipeline with Validation Gates
Orchestrates: Data Ingestion → Validation → Analytics Computation

Architecture:
1. Raw data ingestion (yfinance)
2. Data quality validation and verification
3. Analytics computation (only if validation passes)
4. Precomputed data generation

This pipeline ensures analytics are only computed on verified, high-quality raw data.
"""

import sys
from pathlib import Path

# Add backend to sys.path so package `api` (backend/api) is importable
# This MUST happen before other imports to ensure api modules can be found
base_backend = Path(__file__).parent.parent.parent / "backend"
sys.path.insert(0, str(base_backend.resolve()))

# noqa: E402 - Module level imports intentionally after sys.path setup for import resolution
import logging  # noqa: E402
import sqlite3  # noqa: E402
import traceback  # noqa: E402
from datetime import datetime, timedelta, timezone  # noqa: E402
from typing import Dict, List  # noqa: E402

import pandas as pd  # noqa: E402
from api.utils.config import config  # noqa: E402
from api.utils.asset_universe_loader import (  # noqa: E402
    get_crypto_core_tickers,
    get_gap_assets_tickers,
    get_macro_monitor_tickers,
)
from api.utils.supabase_client import get_supabase_client  # noqa: E402, F401
from api.services.pipeline_service import PipelineService  # noqa: E402, F401

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================

# Data validation thresholds
MIN_DATA_POINTS_REQUIRED = 5  # Minimum data points per asset
MAX_MISSING_RATIO = 0.1  # Max 10% missing data allowed
MIN_ASSETS_REQUIRED = 50  # Minimum active assets to proceed

# Pipeline configuration
LOOKBACK_DAYS = 5  # Fetch last 5 days of data (includes weekends)
BATCH_SIZE = 10  # Process assets in batches
MAX_WORKERS = 5  # Concurrent workers

# ============================================================================
# DATA INGESTION LAYER
# ============================================================================

class DataIngestionOrchestrator:
    """Orchestrates raw data ingestion from yfinance"""
    
    def __init__(self):
        self.data_backend = str(config.get("DATA_BACKEND", "sqlite")).lower()
        self.supabase = get_supabase_client() if self.data_backend == "supabase" else None
        # PipelineService no longer requires a Supabase client in the constructor;
        # it obtains dependencies internally. Instantiate without args.
        self.pipeline_service = PipelineService()
        self.stats = {
            "total_assets": 0,
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "total_records": 0
        }
    
    def fetch_active_assets(self) -> List[Dict]:
        """Fetch list of active assets to update"""
        logger.info("Fetching active assets from %s backend...", self.data_backend)
        if self.supabase is None:
            tickers: List[str] = []
            tickers.extend(get_crypto_core_tickers())
            tickers.extend(get_macro_monitor_tickers())
            tickers.extend(get_gap_assets_tickers())
            deduped = sorted(set(tickers))
            assets = [{"name": t, "yfinance_ticker": t} for t in deduped]
            logger.info("Found %d local-universe assets", len(assets))
            return assets

        # Do not request `asset_type` to avoid schema mismatches in CI/remote DBs.
        # Only select name and yfinance_ticker for ingestion, per schema and requirements
        response = self.supabase.client.table("assets").select(
            "name,yfinance_ticker"
        ).eq("is_active", 1).execute()

        assets = response.data
        logger.info(f"Found {len(assets)} active assets")
        return assets
    
    async def ingest_daily_data(self, assets: List[Dict]) -> Dict:
        """
        Ingest daily EOD data for all active assets
        
        Returns:
            Dict with ingestion statistics
        """
        logger.info(f"\n{'='*80}")
        logger.info("STAGE 1: RAW DATA INGESTION")
        logger.info(f"{'='*80}\n")
        
        self.stats["total_assets"] = len(assets)
        
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=LOOKBACK_DAYS)
        
        logger.info(f"Date range: {start_date.date()} to {end_date.date()}")
        logger.info(f"Processing {len(assets)} assets in batches of {BATCH_SIZE}...")
        
        # Process in batches
        for i in range(0, len(assets), BATCH_SIZE):
            batch = assets[i:i+BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (len(assets) + BATCH_SIZE - 1) // BATCH_SIZE
            
            logger.info(f"\nBatch {batch_num}/{total_batches}: Processing {len(batch)} assets")
            
            # Within each batch, group-fetch 5 symbols per call for speed
            GROUP_SIZE = 5
            for j in range(0, len(batch), GROUP_SIZE):
                group = batch[j:j+GROUP_SIZE]
                group_symbols = [a.get("yfinance_ticker") or a["name"] for a in group]
                try:
                    summary = await self.pipeline_service.run_multi_fetch_store(
                        symbols=group_symbols,
                        start_date=start_date,
                        end_date=end_date,
                        granularity="daily",
                        group_size=GROUP_SIZE,
                        validate=True,
                    )
                    # Log and update stats per symbol
                    for sym in group_symbols:
                        res = summary["results"].get(sym, {})
                        status = res.get("status")
                        records = res.get("records_stored", 0)
                        if status == "success":
                            self.stats["successful"] += 1
                            self.stats["total_records"] += records
                            logger.info(f"  ✓ {sym}: {records} new (batched)")
                        elif status == "skipped":
                            self.stats["skipped"] += 1
                            logger.info(f"  → {sym}: 0 new (duplicates, batched)")
                        else:
                            self.stats["failed"] += 1
                            logger.warning(f"  ✗ {sym}: {status or 'Unknown error'}")
                except Exception as e:
                    # Count all in group as failed on unexpected error
                    self.stats["failed"] += len(group_symbols)
                    logger.error(f"  ✗ Group {group_symbols}: {str(e)}")
        
        logger.info(f"\n{'='*80}")
        logger.info("INGESTION COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"Total assets: {self.stats['total_assets']}")
        logger.info(f"Successful: {self.stats['successful']}")
        logger.info(f"Failed: {self.stats['failed']}")
        logger.info(f"Total records: {self.stats['total_records']}")
        
        return self.stats

# ============================================================================
# DATA VALIDATION LAYER
# ============================================================================

class DataQualityValidator:
    """Validates ingested raw data quality before analytics"""
    
    def __init__(self):
        self.data_backend = str(config.get("DATA_BACKEND", "sqlite")).lower()
        self.db_path = str(config.get("DB_PATH"))
        self.supabase = get_supabase_client() if self.data_backend == "supabase" else None
        self.validation_results = {
            "passed": False,
            "checks": {},
            "errors": [],
            "warnings": []
        }
    
    def validate_all(self) -> Dict:
        """
        Run all validation checks
        
        Returns:
            Dict with validation results
        """
        logger.info(f"\n{'='*80}")
        logger.info("STAGE 2: DATA QUALITY VALIDATION")
        logger.info(f"{'='*80}\n")
        
        # Run validation checks
        self._check_data_completeness()
        self._check_data_freshness()
        self._check_data_quality()
        self._check_asset_coverage()
        
        # Determine overall pass/fail
        critical_checks = ["completeness", "freshness", "asset_coverage"]
        all_passed = all(
            self.validation_results["checks"].get(check, {}).get("passed", False)
            for check in critical_checks
        )
        
        self.validation_results["passed"] = all_passed
        
        # Log summary
        logger.info(f"\n{'='*80}")
        logger.info("VALIDATION SUMMARY")
        logger.info(f"{'='*80}")
        
        for check_name, check_result in self.validation_results["checks"].items():
            status = "✓ PASS" if check_result.get("passed") else "✗ FAIL"
            logger.info(f"{status}: {check_name}")
            if check_result.get("details"):
                logger.info(f"  {check_result['details']}")
        
        if self.validation_results["errors"]:
            logger.error("\nERRORS:")
            for error in self.validation_results["errors"]:
                logger.error(f"  • {error}")
        
        if self.validation_results["warnings"]:
            logger.warning("\nWARNINGS:")
            for warning in self.validation_results["warnings"]:
                logger.warning(f"  • {warning}")
        
        overall_status = "✓ PASSED" if all_passed else "✗ FAILED"
        logger.info(f"\nOverall validation: {overall_status}")
        
        return self.validation_results
    
    def _check_data_completeness(self):
        """Check if sufficient data points exist per asset"""
        logger.info("Check 1: Data completeness...")
        
        try:
            if self.supabase is None:
                cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
                with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                    total_records = int(
                        conn.execute(
                            "SELECT COUNT(*) FROM price_history WHERE timestamp >= ?",
                            (cutoff,),
                        ).fetchone()[0]
                    )
                    active_assets = int(
                        conn.execute(
                            "SELECT COUNT(*) FROM assets WHERE COALESCE(is_active, 1) = 1"
                        ).fetchone()[0]
                    )

                expected_assets = min(active_assets, MIN_ASSETS_REQUIRED)
                expected_records = expected_assets * MIN_DATA_POINTS_REQUIRED
                tolerance_ratio = 0.8
                threshold = int(expected_records * tolerance_ratio)

                if total_records >= threshold:
                    self.validation_results["checks"]["completeness"] = {
                        "passed": True,
                        "details": f"{total_records} recent records found (expected ≥ {threshold})",
                    }
                    logger.info("  ✓ Found %d recent records", total_records)
                else:
                    self.validation_results["checks"]["completeness"] = {
                        "passed": False,
                        "details": f"Only {total_records} records found (expected ≥ {threshold})",
                    }
                    self.validation_results["errors"].append(
                        f"Insufficient data points: {total_records}"
                    )
                    logger.error("  ✗ Insufficient data points")
                return

            # Count total recent records
            response = self.supabase.client.table("price_history").select(
                "asset_id,timestamp",
                count="exact"
            ).gte(
                "timestamp",
                (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            ).execute()

            total_records = response.count or 0

            # Determine expected records with tolerance, based on active assets
            assets_resp = self.supabase.client.table("assets").select(
                "id",
                count="exact"
            ).eq("is_active", 1).execute()
            active_assets = assets_resp.count or 0

            expected_assets = min(active_assets, MIN_ASSETS_REQUIRED)
            expected_records = expected_assets * MIN_DATA_POINTS_REQUIRED
            tolerance_ratio = 0.8  # allow up to 20% shortfall for delistings/market holidays

            if total_records >= int(expected_records * tolerance_ratio):
                self.validation_results["checks"]["completeness"] = {
                    "passed": True,
                    "details": f"{total_records} recent records found (expected ≥ {int(expected_records * tolerance_ratio)})"
                }
                logger.info(f"  ✓ Found {total_records} recent records")
            else:
                self.validation_results["checks"]["completeness"] = {
                    "passed": False,
                    "details": f"Only {total_records} records found (expected ≥ {int(expected_records * tolerance_ratio)})"
                }
                self.validation_results["errors"].append(
                    f"Insufficient data points: {total_records}"
                )
                logger.error("  ✗ Insufficient data points")
        
        except Exception as e:
            logger.error(f"  ✗ Completeness check failed: {str(e)}")
            self.validation_results["checks"]["completeness"] = {
                "passed": False,
                "details": str(e)
            }
            self.validation_results["errors"].append(f"Completeness check error: {str(e)}")
    
    def _check_data_freshness(self):
        """Check if data is recent (within last 2 days)"""
        logger.info("Check 2: Data freshness...")
        
        try:
            if self.supabase is None:
                with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                    row = conn.execute(
                        "SELECT timestamp FROM price_history ORDER BY timestamp DESC LIMIT 1"
                    ).fetchone()
                if not row or not row[0]:
                    self.validation_results["checks"]["freshness"] = {
                        "passed": False,
                        "details": "No data found in price_history",
                    }
                    self.validation_results["errors"].append("No data in price_history table")
                    logger.error("  ✗ No data found")
                    return

                latest_timestamp = pd.to_datetime(str(row[0]), utc=True)
                now = pd.Timestamp.now(tz="UTC")
                age_hours = (now - latest_timestamp).total_seconds() / 3600
                if age_hours <= 48:
                    self.validation_results["checks"]["freshness"] = {
                        "passed": True,
                        "details": f"Latest data is {age_hours:.1f} hours old",
                    }
                    logger.info("  ✓ Data is %.1f hours old", age_hours)
                else:
                    self.validation_results["checks"]["freshness"] = {
                        "passed": False,
                        "details": f"Data is {age_hours:.1f} hours old (> 48 hours)",
                    }
                    self.validation_results["errors"].append(
                        f"Stale data: {age_hours:.1f} hours old"
                    )
                    logger.error("  ✗ Data is stale (%.1f hours)", age_hours)
                return

            # Get most recent timestamp
            response = self.supabase.client.table("price_history").select(
                "timestamp"
            ).order("timestamp", desc=True).limit(1).execute()
            
            if response.data:
                # Ensure timezone-aware comparison in UTC
                latest_timestamp = pd.to_datetime(response.data[0]["timestamp"], utc=True)
                now = pd.Timestamp.now(tz="UTC")
                age_hours = (now - latest_timestamp).total_seconds() / 3600
                
                # Allow 48 hours (includes weekends)
                if age_hours <= 48:
                    self.validation_results["checks"]["freshness"] = {
                        "passed": True,
                        "details": f"Latest data is {age_hours:.1f} hours old"
                    }
                    logger.info(f"  ✓ Data is {age_hours:.1f} hours old")
                else:
                    self.validation_results["checks"]["freshness"] = {
                        "passed": False,
                        "details": f"Data is {age_hours:.1f} hours old (> 48 hours)"
                    }
                    self.validation_results["errors"].append(
                        f"Stale data: {age_hours:.1f} hours old"
                    )
                    logger.error(f"  ✗ Data is stale ({age_hours:.1f} hours)")
            else:
                self.validation_results["checks"]["freshness"] = {
                    "passed": False,
                    "details": "No data found in price_history"
                }
                self.validation_results["errors"].append("No data in price_history table")
                logger.error("  ✗ No data found")
        
        except Exception as e:
            logger.error(f"  ✗ Freshness check failed: {str(e)}")
            self.validation_results["checks"]["freshness"] = {
                "passed": False,
                "details": str(e)
            }
            self.validation_results["errors"].append(f"Freshness check error: {str(e)}")
    
    def _check_data_quality(self):
        """Check for data quality issues (nulls, duplicates, outliers)"""
        logger.info("Check 3: Data quality...")
        
        try:
            if self.supabase is None:
                cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
                with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                    null_count = int(
                        conn.execute(
                            """
                            SELECT COUNT(*) FROM price_history
                            WHERE timestamp >= ? AND (close IS NULL OR volume IS NULL)
                            """,
                            (cutoff,),
                        ).fetchone()[0]
                    )
                    total_count = int(
                        conn.execute(
                            "SELECT COUNT(*) FROM price_history WHERE timestamp >= ?",
                            (cutoff,),
                        ).fetchone()[0]
                    )

                total = max(total_count, 1)
                null_ratio = null_count / total
                if null_ratio <= MAX_MISSING_RATIO:
                    self.validation_results["checks"]["quality"] = {
                        "passed": True,
                        "details": f"Null ratio: {null_ratio:.2%} (acceptable)",
                    }
                    logger.info("  ✓ Data quality acceptable (null ratio: %.2f%%)", null_ratio * 100)
                else:
                    self.validation_results["checks"]["quality"] = {
                        "passed": True,
                        "details": f"Null ratio: {null_ratio:.2%} (high)",
                    }
                    self.validation_results["warnings"].append(
                        f"High null ratio: {null_ratio:.2%}"
                    )
                    logger.warning("  ⚠ High null ratio: %.2f%%", null_ratio * 100)
                return

            # Check for null values in critical columns
            response = self.supabase.client.table("price_history").select(
                "close,volume",
                count="exact"
            ).is_("close", "null").execute()
            
            null_count = response.count or 0
            
            # Get total recent records
            total_response = self.supabase.client.table("price_history").select(
                "id",
                count="exact"
            ).gte(
                "timestamp",
                (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            ).execute()
            
            total_count = total_response.count or 1  # Avoid division by zero
            null_ratio = null_count / total_count if total_count > 0 else 0
            
            if null_ratio <= MAX_MISSING_RATIO:
                self.validation_results["checks"]["quality"] = {
                    "passed": True,
                    "details": f"Null ratio: {null_ratio:.2%} (acceptable)"
                }
                logger.info(f"  ✓ Data quality acceptable (null ratio: {null_ratio:.2%})")
            else:
                self.validation_results["checks"]["quality"] = {
                    "passed": True,  # Non-critical, just warning
                    "details": f"Null ratio: {null_ratio:.2%} (high)"
                }
                self.validation_results["warnings"].append(
                    f"High null ratio: {null_ratio:.2%}"
                )
                logger.warning(f"  ⚠ High null ratio: {null_ratio:.2%}")
        
        except Exception as e:
            logger.warning(f"  ⚠ Quality check failed: {str(e)}")
            self.validation_results["checks"]["quality"] = {
                "passed": True,  # Non-critical
                "details": str(e)
            }
            self.validation_results["warnings"].append(f"Quality check error: {str(e)}")
    
    def _check_asset_coverage(self):
        """Check if minimum number of assets have recent data"""
        logger.info("Check 4: Asset coverage...")
        
        try:
            if self.supabase is None:
                cutoff = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
                with sqlite3.connect(self.db_path, timeout=5.0) as conn:
                    unique_assets = int(
                        conn.execute(
                            "SELECT COUNT(DISTINCT asset_id) FROM price_history WHERE timestamp >= ?",
                            (cutoff,),
                        ).fetchone()[0]
                    )
                if unique_assets >= MIN_ASSETS_REQUIRED:
                    self.validation_results["checks"]["asset_coverage"] = {
                        "passed": True,
                        "details": f"{unique_assets} assets have recent data",
                    }
                    logger.info("  ✓ %d assets with recent data", unique_assets)
                else:
                    self.validation_results["checks"]["asset_coverage"] = {
                        "passed": False,
                        "details": f"Only {unique_assets} assets (min {MIN_ASSETS_REQUIRED} required)",
                    }
                    self.validation_results["errors"].append(
                        f"Insufficient asset coverage: {unique_assets}/{MIN_ASSETS_REQUIRED}"
                    )
                    logger.error(
                        "  ✗ Only %d assets (min %d required)",
                        unique_assets,
                        MIN_ASSETS_REQUIRED,
                    )
                return

            # Attempt RPC if available (optional)
            _ = self.supabase.client.rpc(
                "get_recent_asset_count",
                {"days": 7}
            ).execute()
            
            # Fallback: count via Python
            assets_response = self.supabase.client.table("price_history").select(
                "asset_id"
            ).gte(
                "timestamp",
                (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()
            ).execute()
            
            unique_assets = len(set(row["asset_id"] for row in assets_response.data))
            
            if unique_assets >= MIN_ASSETS_REQUIRED:
                self.validation_results["checks"]["asset_coverage"] = {
                    "passed": True,
                    "details": f"{unique_assets} assets have recent data"
                }
                logger.info(f"  ✓ {unique_assets} assets with recent data")
            else:
                self.validation_results["checks"]["asset_coverage"] = {
                    "passed": False,
                    "details": f"Only {unique_assets} assets (min {MIN_ASSETS_REQUIRED} required)"
                }
                self.validation_results["errors"].append(
                    f"Insufficient asset coverage: {unique_assets}/{MIN_ASSETS_REQUIRED}"
                )
                logger.error(f"  ✗ Only {unique_assets} assets (min {MIN_ASSETS_REQUIRED} required)")
        
        except Exception as e:
            # RPC function might not exist, try simple count
            logger.warning(f"  ⚠ Using fallback asset count: {str(e)}")
            try:
                assets_response = self.supabase.client.table("assets").select(
                    "id",
                    count="exact"
                ).eq("is_active", 1).execute()
                
                active_assets = assets_response.count or 0
                
                if active_assets >= MIN_ASSETS_REQUIRED:
                    self.validation_results["checks"]["asset_coverage"] = {
                        "passed": True,
                        "details": f"{active_assets} active assets found"
                    }
                    logger.info(f"  ✓ {active_assets} active assets")
                else:
                    self.validation_results["checks"]["asset_coverage"] = {
                        "passed": False,
                        "details": f"Only {active_assets} active assets"
                    }
                    self.validation_results["errors"].append(
                        f"Insufficient active assets: {active_assets}/{MIN_ASSETS_REQUIRED}"
                    )
                    logger.error(f"  ✗ Only {active_assets} active assets")
            except Exception as e2:
                logger.error(f"  ✗ Asset coverage check failed: {str(e2)}")
                self.validation_results["checks"]["asset_coverage"] = {
                    "passed": False,
                    "details": str(e2)
                }
                self.validation_results["errors"].append(f"Asset coverage error: {str(e2)}")

# ============================================================================
# ANALYTICS ORCHESTRATION LAYER
# ============================================================================

def run_analytics_pipeline():
    """Run analytics computation pipeline (Tier 3)"""
    if str(config.get("DATA_BACKEND", "sqlite")).lower() == "sqlite":
        logger.info("Local SQLite mode detected: skipping Stage 3 analytics subprocess.")
        return True

    logger.info(f"\n{'='*80}")
    logger.info("STAGE 3: ANALYTICS COMPUTATION")
    logger.info(f"{'='*80}\n")
    
    try:
        import subprocess
        
        # Run analytics computation pipeline
        analytics_script = Path(__file__).parent / "analytics_computation_pipeline_v2.py"
        
        logger.info(f"Executing: {analytics_script} --prod")

        # Stream output line-by-line so Heroku logs show live progress
        import time
        process = subprocess.Popen(
            [sys.executable, "-u", str(analytics_script), "--prod"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,  # line-buffered
        )

        deadline = time.time() + 3600  # 1 hour max
        for line in process.stdout:  # type: ignore[union-attr]
            logger.info(line.rstrip())
            if time.time() > deadline:
                process.kill()
                raise subprocess.TimeoutExpired(process.args, 3600)

        process.wait()
        if process.returncode != 0:
            raise subprocess.CalledProcessError(process.returncode, process.args)

        logger.info("✓ Analytics computation completed successfully")
        return True
    
    except Exception as e:
        logger.error(f"✗ Analytics pipeline failed: {e}")
        logger.error(f"Output: {getattr(e, 'output', 'N/A')}")
        logger.error(f"Error: {getattr(e, 'stderr', 'N/A')}")
        logger.error(traceback.format_exc())
        return False

def run_precomputation_pipeline():
    """Run precomputed correlations generation"""
    if str(config.get("DATA_BACKEND", "sqlite")).lower() == "sqlite":
        logger.info("Local SQLite mode detected: skipping Stage 4 precomputation subprocess.")
        return True

    logger.info(f"\n{'='*80}")
    logger.info("STAGE 4: PRECOMPUTED DATA GENERATION")
    logger.info(f"{'='*80}\n")
    
    try:
        import subprocess
        
        # Run populate_precomputed script
        precompute_script = Path(__file__).parent / "populate_precomputed.py"
        
        # Run with specific parameters
        logger.info(f"Executing: {precompute_script}")
        result = subprocess.run(
            [
                sys.executable,
                str(precompute_script),
                "--lookback-days", "180",
                "--limit-assets", "100",
                "--top-pairs", "100",
                "--method", "spearman",
                "--granularity", "daily"
            ],
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info("Precomputation output:")
        logger.info(result.stdout)
        
        if result.stderr:
            logger.warning(f"Precomputation stderr: {result.stderr}")
        
        logger.info("✓ Precomputation completed successfully")
        return True
    
    except Exception as e:
        logger.error(f"✗ Precomputation pipeline failed: {e}")
        logger.error(f"Output: {getattr(e, 'output', 'N/A')}")
        logger.error(f"Error: {getattr(e, 'stderr', 'N/A')}")
        logger.error(traceback.format_exc())
        return False

# ============================================================================
# MAIN ORCHESTRATOR
# ============================================================================

async def main():
    """Main orchestration function"""
    logger.info(f"\n{'='*80}")
    logger.info("DAILY EOD DATA PIPELINE")
    logger.info(f"Started: {datetime.now(timezone.utc).isoformat()}")
    logger.info(f"{'='*80}\n")
    
    try:
        # Stage 1: Data Ingestion
        ingestor = DataIngestionOrchestrator()
        assets = ingestor.fetch_active_assets()
        
        if not assets:
            logger.error("No active assets found. Aborting pipeline.")
            return False
        
        ingestion_stats = await ingestor.ingest_daily_data(assets)
        
        # Stage 2: Data Validation
        validator = DataQualityValidator()
        validation_results = validator.validate_all()
        
        # Decision gate: Only proceed if validation passes
        if not validation_results["passed"]:
            logger.error("\n❌ DATA VALIDATION FAILED")
            logger.error("Analytics pipeline will NOT run until data quality issues are resolved.")
            logger.error("Please review validation errors above and fix data issues.")
            return False
        
        logger.info("\n✓ DATA VALIDATION PASSED")
        logger.info("Proceeding to analytics computation...\n")
        
        # Stage 3: Analytics Computation
        analytics_success = run_analytics_pipeline()
        
        if not analytics_success:
            logger.error("Analytics computation failed, but data ingestion was successful.")
            logger.error("You may need to run analytics manually after investigating the issue.")
            return False
        
        # Stage 4: Precomputed Data Generation
        precompute_success = run_precomputation_pipeline()
        
        if not precompute_success:
            logger.warning("Precomputation failed, but core analytics were successful.")
            logger.warning("API may use slower real-time computations until this is fixed.")
        
        # Final summary
        logger.info(f"\n{'='*80}")
        logger.info("PIPELINE COMPLETE")
        logger.info(f"{'='*80}")
        logger.info(f"Finished: {datetime.now(timezone.utc).isoformat()}")
        logger.info("\nSummary:")
        logger.info(f"  • Data ingestion: ✓ {ingestion_stats['successful']}/{ingestion_stats['total_assets']} assets")
        logger.info("  • Data validation: ✓ PASSED")
        logger.info(f"  • Analytics computation: {'✓ PASSED' if analytics_success else '✗ FAILED'}")
        logger.info(f"  • Precomputed data: {'✓ PASSED' if precompute_success else '✗ FAILED'}")
        
        return True
    
    except Exception as e:
        logger.error(f"\n❌ PIPELINE FAILED: {str(e)}")
        logger.error(traceback.format_exc())
        return False

if __name__ == "__main__":
    import asyncio
    try:
        success = asyncio.run(main())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        logger.info("\n\nPipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
