#!/usr/bin/env python3
"""
ETL Phase 3: Create Clean Analytics View

Creates analytics view that excludes suspect data.
"""

import sys
from pathlib import Path

# Add backend to path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from scripts.etl.etl_runner import ETLRunner


class CleanViewETL(ETLRunner):
    """ETL for creating clean analytics view."""

    def __init__(self, dry_run: bool = False):
        super().__init__("clean_view", dry_run)

    def create_analytics_schema(self):
        """Create analytics schema if it doesn't exist."""
        sql = "CREATE SCHEMA IF NOT EXISTS analytics;"
        self.execute_sql(sql)
        print("✓ Created analytics schema")

    def create_clean_view(self):
        """Create clean view excluding suspect rows."""
        sql = """
        CREATE OR REPLACE VIEW analytics.price_history_clean AS
        SELECT
            asset_id,
            timestamp,
            open,
            high,
            low,
            close,
            volume,
            adjusted_close,
            source,
            data_quality,
            created_at,
            updated_at
        FROM public.price_history
        WHERE is_suspect IS DISTINCT FROM true;
        """
        self.execute_sql(sql)
        print("✓ Created analytics.price_history_clean view")

    def grant_permissions(self):
        """Grant select permissions on the view."""
        sql = "GRANT SELECT ON analytics.price_history_clean TO PUBLIC;"
        self.execute_sql(sql)
        print("✓ Granted public select permissions on clean view")

    def run_phase(self):
        """Run the complete clean view phase."""
        operations = []

        # Operation 1: Create schema
        def op1():
            self.create_analytics_schema()

        # Operation 2: Create view
        def op2():
            self.create_clean_view()

        # Operation 3: Grant permissions
        def op3():
            self.grant_permissions()

        operations.extend([op1, op2, op3])

        success = self.run_with_transaction(operations)
        return success


def main():
    """CLI interface."""
    import argparse

    parser = argparse.ArgumentParser(description="ETL Phase 3: Clean View")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")

    args = parser.parse_args()

    etl = CleanViewETL(dry_run=args.dry_run)
    success = etl.run_phase()

    if success:
        print("✓ Phase 3 completed successfully")
        sys.exit(0)
    else:
        print("✗ Phase 3 failed")
        sys.exit(1)


if __name__ == "__main__":
    main()