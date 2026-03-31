#!/usr/bin/env python3
"""
Simple data validation checks for Phase 1
Run with: python scripts/simple_validation.py
"""

import os
import sys

# Simple validation without complex imports
def run_sql_validation():
    """Print SQL commands for manual execution"""
    print("📊 DATA VALIDATION CHECKS")
    print("=" * 50)

    print("\n1. OHLC CONSTRAINTS VALIDATION")
    print("Run this SQL in Supabase SQL Editor:")
    print("""
SELECT
    COUNT(*) as total_rows,
    COUNT(CASE WHEN low > open THEN 1 END) as low_gt_open,
    COUNT(CASE WHEN low > close THEN 1 END) as low_gt_close,
    COUNT(CASE WHEN high < open THEN 1 END) as high_lt_open,
    COUNT(CASE WHEN high < close THEN 1 END) as high_lt_close,
    COUNT(CASE WHEN open < 0 OR high < 0 OR low < 0 OR close < 0 THEN 1 END) as negative_prices
FROM price_history_eod
WHERE date >= '2020-01-01';
    """)

    print("\n2. DUPLICATE TIMESTAMPS CHECK")
    print("Run this SQL in Supabase SQL Editor:")
    print("""
SELECT COUNT(*) as duplicate_count
FROM (
    SELECT asset_id, date, COUNT(*) as cnt
    FROM price_history_eod
    WHERE date >= '2020-01-01'
    GROUP BY asset_id, date
    HAVING COUNT(*) > 1
) duplicates;
    """)

    print("\n3. MISSING TRADING DAYS (GAP DETECTION)")
    print("Run this SQL in Supabase SQL Editor:")
    print("""
SELECT
    asset_id,
    symbol,
    COUNT(*) as gaps_found
FROM (
    SELECT
        phe.asset_id,
        a.symbol,
        phe.date,
        LAG(phe.date) OVER (PARTITION BY phe.asset_id ORDER BY phe.date) as prev_date,
        phe.date - LAG(phe.date) OVER (PARTITION BY phe.asset_id ORDER BY phe.date) as days_diff
    FROM price_history_eod phe
    JOIN assets a ON phe.asset_id = a.id
    WHERE phe.date >= '2020-01-01'
) gaps
WHERE days_diff > 1
GROUP BY asset_id, symbol
ORDER BY gaps_found DESC
LIMIT 10;
    """)

if __name__ == "__main__":
    run_sql_validation()