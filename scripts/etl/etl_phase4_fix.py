#!/usr/bin/env python3
"""
ETL Phase 4: Fix Suspect Rows (Optional)

Repairs suspect rows by interpolating missing values.
"""

import sys
from pathlib import Path

# Add backend to path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from scripts.etl.etl_runner import ETLRunner


class FixETL(ETLRunner):
    """ETL for fixing suspect rows with interpolation."""

    def __init__(self, dry_run: bool = False):
        super().__init__("fix", dry_run)

    def interpolate_suspect_closes(self):
        """Fix suspect close prices using prev/next valid closes."""
        sql = """
        WITH suspect_neighbors AS (
            SELECT
                s.asset_id,
                s.timestamp,
                s.ctid,

                -- Previous valid close
                (
                    SELECT p2.close
                    FROM public.price_history p2
                    WHERE p2.asset_id = s.asset_id
                      AND p2.timestamp < s.timestamp
                      AND (p2.is_suspect IS DISTINCT FROM true)
                    ORDER BY p2.timestamp DESC
                    LIMIT 1
                ) AS prev_valid_close,

                -- Next valid close
                (
                    SELECT p3.close
                    FROM public.price_history p3
                    WHERE p3.asset_id = s.asset_id
                      AND p3.timestamp > s.timestamp
                      AND (p3.is_suspect IS DISTINCT FROM true)
                    ORDER BY p3.timestamp ASC
                    LIMIT 1
                ) AS next_valid_close

            FROM public.price_history s
            WHERE s.is_suspect = true
        ),
        replacements AS (
            SELECT
                asset_id,
                timestamp,
                ctid,
                CASE
                    WHEN prev_valid_close IS NOT NULL AND next_valid_close IS NOT NULL
                        THEN (prev_valid_close + next_valid_close) / 2.0
                    WHEN prev_valid_close IS NOT NULL
                        THEN prev_valid_close
                    WHEN next_valid_close IS NOT NULL
                        THEN next_valid_close
                    ELSE NULL
                END AS replacement_close
            FROM suspect_neighbors
        )
        UPDATE public.price_history p
        SET
            close = COALESCE(r.replacement_close, p.close),
            is_suspect = CASE WHEN r.replacement_close IS NOT NULL THEN false ELSE true END
        FROM replacements r
        WHERE p.ctid = r.ctid
          AND r.replacement_close IS NOT NULL;
        """

        affected = self.execute_sql(sql)
        print(f"✓ Interpolated {affected} suspect close prices")
        return affected

    def clamp_ohlc_for_suspect(self):
        """Clamp O/H/L to close for remaining suspect rows."""
        sql = """
        UPDATE public.price_history
        SET
            open = close,
            high = close,
            low = close
        WHERE is_suspect = true;
        """

        affected = self.execute_sql(sql)
        print(f"✓ Clamped O/H/L for {affected} remaining suspect rows")
        return affected

    def run_phase(self):
        """Run the complete fix phase."""
        operations = []

        # Operation 1: Interpolate suspect closes
        def op1():
            fixed = self.interpolate_suspect_closes()
            self.log_etl_progress(fixed, 'running', f'Interpolated {fixed} close prices')

        # Operation 2: Clamp O/H/L for remaining suspect rows
        def op2():
            clamped = self.clamp_ohlc_for_suspect()
            self.log_etl_progress(clamped, 'running', f'Clamped O/H/L for {clamped} rows')

        operations.extend([op1, op2])

        success = self.run_with_transaction(operations)
        return success


def main():
    """CLI interface."""
    import argparse

    parser = argparse.ArgumentParser(description="ETL Phase 4: Fix (Optional)")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")

    args = parser.parse_args()

    etl = FixETL(dry_run=args.dry_run)
    success = etl.run_phase()

    if success:
        print("✓ Phase 4 completed successfully")
        sys.exit(0)
    else:
        print("✗ Phase 4 failed")
        sys.exit(1)


if __name__ == "__main__":
    main()