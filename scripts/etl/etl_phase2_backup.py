#!/usr/bin/env python3
"""
ETL Phase 2: Backup Suspect Rows

Creates backup table and archives suspect rows before modifications.
"""

import sys
from pathlib import Path

# Add backend to path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from scripts.etl.etl_runner import ETLRunner


class BackupETL(ETLRunner):
    """ETL for backing up suspect rows."""

    def __init__(self, dry_run: bool = False):
        super().__init__("backup", dry_run)

    def create_backup_table(self):
        """Create backup table with same structure."""
        sql = """
        CREATE TABLE IF NOT EXISTS public.price_history_backup
        (LIKE public.price_history INCLUDING ALL);
        """
        self.execute_sql(sql)

        # Add backup metadata columns
        sql_metadata = """
        ALTER TABLE public.price_history_backup
        ADD COLUMN IF NOT EXISTS backup_timestamp timestamptz DEFAULT now(),
        ADD COLUMN IF NOT EXISTS backup_reason text DEFAULT 'suspect_data_etl';
        """
        self.execute_sql(sql_metadata)
        print("✓ Created backup table with metadata columns")

    def backup_suspect_rows(self):
        """Insert suspect rows into backup table (avoid duplicates)."""
        sql = """
        INSERT INTO public.price_history_backup (
            asset_id, timestamp, open, high, low, close, volume, adjusted_close,
            source, data_quality, created_at, updated_at, is_suspect,
            backup_timestamp, backup_reason
        )
        SELECT
            p.asset_id, p.timestamp, p.open, p.high, p.low, p.close, p.volume, p.adjusted_close,
            p.source, p.data_quality, p.created_at, p.updated_at, p.is_suspect,
            now(), 'suspect_data_etl'
        FROM public.price_history p
        LEFT JOIN public.price_history_backup b
            ON p.asset_id = b.asset_id
           AND p.timestamp = b.timestamp
        WHERE p.is_suspect = true
          AND b.asset_id IS NULL;  -- Avoid duplicates
        """

        affected = self.execute_sql(sql)
        print(f"✓ Backed up {affected} suspect rows")
        return affected

    def run_phase(self):
        """Run the complete backup phase."""
        operations = []

        # Operation 1: Create backup table
        def op1():
            self.create_backup_table()

        # Operation 2: Backup suspect rows
        def op2():
            backed_up = self.backup_suspect_rows()
            self.log_etl_progress(backed_up, 'running', f'Backed up {backed_up} suspect rows')

        operations.extend([op1, op2])

        success = self.run_with_transaction(operations)
        return success


def main():
    """CLI interface."""
    import argparse

    parser = argparse.ArgumentParser(description="ETL Phase 2: Backup")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")

    args = parser.parse_args()

    etl = BackupETL(dry_run=args.dry_run)
    success = etl.run_phase()

    if success:
        print("✓ Phase 2 completed successfully")
        sys.exit(0)
    else:
        print("✗ Phase 2 failed")
        sys.exit(1)


if __name__ == "__main__":
    main()