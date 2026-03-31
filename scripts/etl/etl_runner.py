#!/usr/bin/env python3
"""
Base ETL Runner for Price History Data Cleaning

Provides common functionality for all ETL phases:
- Database connections
- Transaction management
- Error handling
- Logging
- Dry-run support
"""

import os
import sys
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from contextlib import contextmanager
import time

# Add backend to path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "backend"))

try:
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("ERROR: psycopg2 not available. Install with: pip install psycopg2-binary")
    sys.exit(1)

from api.utils.config import get_config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('etl_runner')


class ETLRunner:
    """Base class for ETL operations."""

    def __init__(self, phase_name: str, dry_run: bool = False):
        self.phase_name = phase_name
        self.dry_run = dry_run
        self.db_config = self._get_db_config()
        self.connection = None

    def _get_db_config(self) -> Optional[str]:
        """Get database connection string."""
        cfg = get_config()
        return cfg.get("DATABASE_URL")

    @contextmanager
    def get_connection(self):
        """Context manager for database connections."""
        if not self.db_config:
            raise RuntimeError("DATABASE_URL not configured")

        connection = None
        try:
            connection = psycopg2.connect(self.db_config)
            connection.autocommit = False  # Use transactions
            logger.info(f"Connected to database for phase: {self.phase_name}")
            yield connection
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            raise
        finally:
            if connection:
                connection.close()
                logger.info("Database connection closed")

    def execute_sql(self, sql: str, params: Optional[tuple] = None) -> Any:
        """Execute SQL with proper error handling."""
        if self.dry_run:
            logger.info(f"[DRY RUN] Would execute: {sql[:100]}...")
            return None

        if not self.connection:
            raise RuntimeError("No active database connection")

        try:
            with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
                cursor.execute(sql, params or ())
                if sql.strip().upper().startswith(('SELECT', 'WITH')):
                    return cursor.fetchall()
                else:
                    return cursor.rowcount
        except Exception as e:
            logger.error(f"SQL execution failed: {e}")
            logger.error(f"SQL: {sql}")
            self.connection.rollback()
            raise

    def log_etl_progress(self, records_processed: int, status: str = 'running', details: str = ''):
        """Log ETL progress to database."""
        sql = """
        INSERT INTO public.etl_logs (phase, records_processed, status, details, completed_at)
        VALUES (%s, %s, %s, %s, CASE WHEN %s = 'completed' THEN now() ELSE NULL END)
        """
        try:
            self.execute_sql(sql, (self.phase_name, records_processed, status, details, status))
        except Exception as e:
            logger.warning(f"Failed to log ETL progress: {e}")

    def run_with_transaction(self, operations: list) -> bool:
        """Run multiple operations in a transaction."""
        try:
            with self.get_connection() as conn:
                self.connection = conn

                # Start transaction
                logger.info(f"Starting ETL phase: {self.phase_name}")

                for i, operation in enumerate(operations, 1):
                    logger.info(f"Executing operation {i}/{len(operations)}")
                    operation()

                # Log success
                self.log_etl_progress(0, 'completed', f'Phase {self.phase_name} completed successfully')

                # Commit transaction
                if not self.dry_run:
                    conn.commit()
                    logger.info(f"ETL phase {self.phase_name} committed successfully")
                else:
                    logger.info(f"[DRY RUN] Would commit ETL phase {self.phase_name}")

                return True

        except Exception as e:
            logger.error(f"ETL phase {self.phase_name} failed: {e}")
            self.log_etl_progress(0, 'failed', str(e))
            return False

    def get_asset_batches(self, batch_size: int = 50) -> list:
        """Get asset IDs in batches to avoid long-running queries."""
        sql = """
        SELECT DISTINCT asset_id
        FROM public.price_history
        ORDER BY asset_id
        """
        results = self.execute_sql(sql)
        asset_ids = [row['asset_id'] for row in results]

        # Split into batches
        batches = []
        for i in range(0, len(asset_ids), batch_size):
            batches.append(asset_ids[i:i + batch_size])

        return batches


def main():
    """CLI interface for ETL runner."""
    import argparse

    parser = argparse.ArgumentParser(description="ETL Runner Base")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")
    parser.add_argument("--phase", required=True, help="ETL phase name")

    args = parser.parse_args()

    # This is a base class, should be subclassed
    logger.info(f"ETL Runner initialized for phase: {args.phase} (dry_run={args.dry_run})")


if __name__ == "__main__":
    main()