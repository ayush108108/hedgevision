"""
4-Hour Intraday Data Pipeline (Lightweight)
Fetches recent 4h intraday data for active assets without heavy validation.

This runs more frequently (every 4 hours) and only fetches incremental data.
Full validation and analytics run only during EOD pipeline.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta, timezone
import logging
import asyncio

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend" / "api"))

from utils.supabase_client import get_supabase_client
from services.pipeline_service import PipelineService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - [%(levelname)s] - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger(__name__)

LOOKBACK_HOURS = 8  # Fetch last 8 hours (includes gaps)
BATCH_SIZE = 10

async def main():
    """Fetch 4h intraday data for active assets"""
    logger.info("="*80)
    logger.info("4-HOUR INTRADAY DATA PIPELINE")
    logger.info(f"Started: {datetime.now(timezone.utc).isoformat()}")
    logger.info("="*80)
    
    try:
        supabase = get_supabase_client()
        # PipelineService no longer requires Supabase client in constructor
        pipeline_service = PipelineService()
        
        # Fetch active assets
        logger.info("Fetching active assets...")
        response = supabase.client.table("assets").select(
            "id,symbol,name"
        ).eq("is_active", 1).execute()
        
        assets = response.data
        logger.info(f"Found {len(assets)} active assets")
        
        # Calculate date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(hours=LOOKBACK_HOURS)
        
        logger.info(f"Fetching 4h data from {start_date} to {end_date}")
        
        stats = {"total": len(assets), "success": 0, "failed": 0, "records": 0}
        
        # Process in batches
        for i in range(0, len(assets), BATCH_SIZE):
            batch = assets[i:i+BATCH_SIZE]
            batch_num = (i // BATCH_SIZE) + 1
            total_batches = (len(assets) + BATCH_SIZE - 1) // BATCH_SIZE
            
            logger.info(f"\nBatch {batch_num}/{total_batches}: {len(batch)} assets")
            
            for asset in batch:
                symbol = asset["symbol"]
                try:
                    result = await pipeline_service.run_pipeline(
                        symbol=symbol,
                        start_date=start_date,
                        end_date=end_date,
                        granularity="4h"
                    )
                    
                    if result.get("success"):
                        records = result.get("records_inserted", 0)
                        stats["success"] += 1
                        stats["records"] += records
                        if records > 0:
                            logger.info(f"  ✓ {symbol}: {records} records")
                    else:
                        stats["failed"] += 1
                        logger.warning(f"  ✗ {symbol}: {result.get('error', 'Unknown')}")
                
                except Exception as e:
                    stats["failed"] += 1
                    logger.error(f"  ✗ {symbol}: {str(e)}")
        
        logger.info("\n" + "="*80)
        logger.info("PIPELINE COMPLETE")
        logger.info("="*80)
        logger.info(f"Total: {stats['total']}")
        logger.info(f"Success: {stats['success']}")
        logger.info(f"Failed: {stats['failed']}")
        logger.info(f"Records: {stats['records']}")
        
        return True
    
    except Exception as e:
        logger.error(f"Pipeline failed: {str(e)}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
