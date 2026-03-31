#!/usr/bin/env python3
"""
ETL Phase 1: Setup and Flag Suspect Rows

Adds is_suspect column and flags problematic price history rows.
"""

import sys
from pathlib import Path

# Add backend to path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from scripts.etl.etl_runner import ETLRunner


class SetupFlagETL(ETLRunner):
    """ETL for setting up and flagging suspect rows."""

    def __init__(self, dry_run: bool = False):
        super().__init__("setup_flag", dry_run)

    def add_suspect_column(self):
        """Add is_suspect column if missing."""
        sql = """
        ALTER TABLE public.price_history
        ADD COLUMN IF NOT EXISTS is_suspect boolean DEFAULT false;
        """
        self.execute_sql(sql)
        print("✓ Added is_suspect column")

    def reset_flags(self):
        """Reset all suspect flags to false."""
        sql = """
        UPDATE public.price_history
        SET is_suspect = false
        WHERE is_suspect IS DISTINCT FROM false;
        """
        affected = self.execute_sql(sql)
        print(f"✓ Reset {affected} suspect flags")

    def flag_suspect_rows_batch(self, asset_ids: list):
        """Flag suspect rows for a batch of assets with enhanced anomaly detection."""
        if not asset_ids:
            return 0

        # Create IN clause for asset_ids
        asset_placeholders = ','.join(['%s'] * len(asset_ids))

        sql = f"""
        WITH asset_stats AS (
            -- Calculate rolling statistics for each asset
            SELECT
                asset_id,
                AVG(close) as mean_close,
                STDDEV(close) as std_close,
                PERCENTILE_CONT(0.25) WITHIN GROUP (ORDER BY close) as q1_close,
                PERCENTILE_CONT(0.75) WITHIN GROUP (ORDER BY close) as q3_close
            FROM public.price_history
            WHERE asset_id IN ({asset_placeholders})
              AND close > 0
            GROUP BY asset_id
        ),
        enriched AS (
            SELECT
                p.ctid,
                p.asset_id,
                p."timestamp",
                p.open, p.high, p.low, p.close, p.volume,
                LAG(p.close) OVER (PARTITION BY p.asset_id ORDER BY p."timestamp") AS prev_close,
                LAG(p."timestamp") OVER (PARTITION BY p.asset_id ORDER BY p."timestamp") AS prev_timestamp,
                LEAD(p.close) OVER (PARTITION BY p.asset_id ORDER BY p."timestamp") AS next_close,
                s.mean_close,
                s.std_close,
                s.q1_close,
                s.q3_close,
                (s.q3_close - s.q1_close) as iqr_close
            FROM public.price_history p
            LEFT JOIN asset_stats s ON p.asset_id = s.asset_id
            WHERE p.asset_id IN ({asset_placeholders})
        )
        UPDATE public.price_history p
        SET is_suspect = true
        FROM enriched e
        WHERE p.ctid = e.ctid
          AND (
              -- Extreme percentage changes (>500% or < -90%)
              (e.prev_close IS NOT NULL AND ABS((e.close - e.prev_close) / NULLIF(e.prev_close, 0)) > 5)
              OR (e.prev_close IS NOT NULL AND (e.close - e.prev_close) / NULLIF(e.prev_close, 0) < -0.9)

              -- Statistical outliers (beyond 3 standard deviations)
              OR (e.std_close > 0 AND ABS(e.close - e.mean_close) / e.std_close > 3)

              -- IQR outliers (beyond 1.5 * IQR from quartiles)
              OR (e.iqr_close > 0 AND (e.close < e.q1_close - 1.5 * e.iqr_close OR e.close > e.q3_close + 1.5 * e.iqr_close))

              -- Absurd values
              OR e.close < 1e-6                                    -- effectively zero
              OR e.close > 1e6                                    -- absurdly large
              OR e.open < 1e-6 OR e.open > 1e6                    -- invalid open
              OR e.high < 1e-6 OR e.high > 1e6                    -- invalid high
              OR e.low < 1e-6 OR e.low > 1e6                      -- invalid low

              -- OHLC inconsistencies
              OR e.high < e.low                                   -- high < low
              OR e.open > e.high OR e.open < e.low                -- open outside range
              OR e.close > e.high OR e.close < e.low              -- close outside range

              -- Time-based anomalies
              OR e."timestamp" > NOW() + interval '1 day'         -- future data
              OR (e.prev_timestamp IS NOT NULL AND e."timestamp" - e.prev_timestamp > interval '30 days')  -- large gaps

              -- Stale prices (no change for extended periods)
              OR (e.prev_close IS NOT NULL AND e.close = e.prev_close
                  AND ROW_NUMBER() OVER (PARTITION BY e.asset_id, e.close ORDER BY e."timestamp") > 30)

              -- Volume anomalies (extremely high volume spikes)
              OR (e.volume IS NOT NULL AND e.volume > 1000000000) -- >1B shares (likely error)
          );
        """

    def flag_volume_anomalies_batch(self, asset_ids: list):
        """Flag volume-based anomalies for a batch of assets."""
        if not asset_ids:
            return 0

        asset_placeholders = ','.join(['%s'] * len(asset_ids))

        sql = f"""
        WITH volume_stats AS (
            SELECT
                asset_id,
                AVG(volume) as mean_volume,
                STDDEV(volume) as std_volume,
                MAX(volume) as max_volume
            FROM public.price_history
            WHERE asset_id IN ({asset_placeholders})
              AND volume IS NOT NULL
              AND volume > 0
            GROUP BY asset_id
        ),
        enriched AS (
            SELECT
                p.ctid,
                p.asset_id,
                p.volume,
                v.mean_volume,
                v.std_volume,
                v.max_volume
            FROM public.price_history p
            LEFT JOIN volume_stats v ON p.asset_id = v.asset_id
            WHERE p.asset_id IN ({asset_placeholders})
              AND p.volume IS NOT NULL
        )
        UPDATE public.price_history p
        SET is_suspect = true
        FROM enriched e
        WHERE p.ctid = e.ctid
          AND (
              -- Extreme volume outliers (>5 std dev from mean)
              (e.std_volume > 0 AND e.volume > e.mean_volume + 5 * e.std_volume)
              -- Unrealistic volumes (>10x maximum historical volume)
              OR (e.max_volume > 0 AND e.volume > 10 * e.max_volume)
              -- Zero volume on trading days (suspicious)
              OR e.volume = 0
          );
        """

        affected = self.execute_sql(sql, tuple(asset_ids))
        return affected or 0

    def flag_cross_sectional_anomalies_batch(self, asset_ids: list):
        """Flag cross-sectional anomalies (compared to similar assets)."""
        if not asset_ids:
            return 0

        asset_placeholders = ','.join(['%s'] * len(asset_ids))

        sql = f"""
        WITH market_stats AS (
            -- Calculate market-wide statistics for each timestamp
            SELECT
                "timestamp",
                AVG(close) as market_avg_close,
                STDDEV(close) as market_std_close,
                COUNT(*) as market_count
            FROM public.price_history
            WHERE "timestamp" >= CURRENT_DATE - interval '1 year'
              AND close > 0
            GROUP BY "timestamp"
            HAVING COUNT(*) >= 10  -- Require minimum market participation
        ),
        asset_deviations AS (
            SELECT
                p.asset_id,
                p."timestamp",
                p.close,
                m.market_avg_close,
                m.market_std_close,
                ABS(p.close - m.market_avg_close) / NULLIF(m.market_std_close, 0) as z_score_from_market
            FROM public.price_history p
            JOIN market_stats m ON p."timestamp" = m."timestamp"
            WHERE p.asset_id IN ({asset_placeholders})
        )
        UPDATE public.price_history p
        SET is_suspect = true
        FROM asset_deviations a
        WHERE p.asset_id = a.asset_id
          AND p."timestamp" = a."timestamp"
          AND a.z_score_from_market > 10;  -- Extremely deviant from market
        """

        affected = self.execute_sql(sql, tuple(asset_ids))
        return affected or 0

    def run_phase(self):
        """Run the complete setup and flag phase."""
        operations = []

        # Operation 1: Add column
        def op1():
            self.add_suspect_column()

        # Operation 2: Reset flags
        def op2():
            self.reset_flags()

        # Operation 3: Flag suspect rows in batches
        def op3():
            batches = self.get_asset_batches(batch_size=50)
            total_flagged = 0

            for i, batch in enumerate(batches, 1):
                print(f"Processing batch {i}/{len(batches)} ({len(batch)} assets)")
                flagged = self.flag_suspect_rows_batch(batch) or 0
                total_flagged += flagged
                print(f"  Flagged {flagged} suspect rows in batch")

            print(f"✓ Total suspect rows flagged: {total_flagged}")

        # Operation 4: Flag volume anomalies
        def op4():
            batches = self.get_asset_batches(batch_size=50)
            total_volume_flagged = 0

            for i, batch in enumerate(batches, 1):
                print(f"Processing volume anomalies batch {i}/{len(batches)}")
                flagged = self.flag_volume_anomalies_batch(batch) or 0
                total_volume_flagged += flagged

            print(f"✓ Total volume anomalies flagged: {total_volume_flagged}")

        # Operation 5: Flag cross-sectional anomalies
        def op5():
            batches = self.get_asset_batches(batch_size=50)
            total_cross_sectional_flagged = 0

            for i, batch in enumerate(batches, 1):
                print(f"Processing cross-sectional anomalies batch {i}/{len(batches)}")
                flagged = self.flag_cross_sectional_anomalies_batch(batch) or 0
                total_cross_sectional_flagged += flagged

            print(f"✓ Total cross-sectional anomalies flagged: {total_cross_sectional_flagged}")

        operations.extend([op1, op2, op3, op4, op5])

        success = self.run_with_transaction(operations)
        return success


def main():
    """CLI interface."""
    import argparse

    parser = argparse.ArgumentParser(description="ETL Phase 1: Setup and Flag")
    parser.add_argument("--dry-run", action="store_true", help="Dry run mode")

    args = parser.parse_args()

    etl = SetupFlagETL(dry_run=args.dry_run)
    success = etl.run_phase()

    if success:
        print("✓ Phase 1 completed successfully")
        sys.exit(0)
    else:
        print("✗ Phase 1 failed")
        sys.exit(1)


if __name__ == "__main__":
    main()