-- OHLC Validation Query
-- Run this in Supabase SQL Editor or psql to validate OHLC constraints

SELECT
    'OHLC Validation Results' as check_type,
    COUNT(*) as total_rows_checked,
    COUNT(CASE WHEN low > open THEN 1 END) as low_gt_open_violations,
    COUNT(CASE WHEN low > close THEN 1 END) as low_gt_close_violations,
    COUNT(CASE WHEN high < open THEN 1 END) as high_lt_open_violations,
    COUNT(CASE WHEN high < close THEN 1 END) as high_lt_close_violations,
    COUNT(CASE WHEN open < 0 OR high < 0 OR low < 0 OR close < 0 THEN 1 END) as negative_price_violations
FROM price_history_eod
WHERE date >= '2020-01-01';

-- Check for duplicate timestamps per symbol
SELECT
    'Duplicate Timestamps Check' as check_type,
    COUNT(*) as total_duplicates
FROM (
    SELECT asset_id, date, COUNT(*) as cnt
    FROM price_history_eod
    WHERE date >= '2020-01-01'
    GROUP BY asset_id, date
    HAVING COUNT(*) > 1
) duplicates;

-- Check for missing trading days (basic gap detection)
-- This is a simplified check - real gap detection would be more complex
SELECT
    'Basic Gap Detection' as check_type,
    asset_id,
    COUNT(*) as gaps_found
FROM (
    SELECT
        asset_id,
        date,
        LAG(date) OVER (PARTITION BY asset_id ORDER BY date) as prev_date,
        date - LAG(date) OVER (PARTITION BY asset_id ORDER BY date) as days_diff
    FROM price_history_eod
    WHERE date >= '2020-01-01'
) gaps
WHERE days_diff > 1
GROUP BY asset_id
ORDER BY gaps_found DESC
LIMIT 10;