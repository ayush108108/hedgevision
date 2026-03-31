"""
Populate Supabase with precomputed correlation matrices and cointegration tests.

- Correlation matrices -> precomputed_correlations (method: spearman|pearson, granularity: daily)
- Cointegration tests   -> cointegration_tests (69 fields per test)

Usage (PowerShell):
  # Run with defaults (daily, spearman, last 180d, top 50 pairs from 200+ assets)
  python scripts/pipelines/populate_precomputed.py

  # Customize (200+ assets, screen for 5K+ pairs)
  python scripts/pipelines/populate_precomputed.py --lookback-days 252 --limit-assets 200 --top-pairs 5000 --method spearman --granularity daily

Notes:
- Requires backend .env with Supabase URL and service key.
- For cointegration tests, the FastAPI backend must be running on http://localhost:8000
  so we can call /api/cointegration/test-pair which stores results into cointegration_tests.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
import os
from typing import Dict, List, Literal, cast

import pandas as pd
import requests

# Make backend API importable
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'backend'))

from api.utils.supabase_client import get_supabase_client  # type: ignore[reportMissingImports]


def _load_env_from_file():
    """Best-effort load of environment variables from project .env or env.example file."""
    try:
        root = Path(__file__).resolve().parents[2]
        candidates = []
        env_path = root / '.env'
        if env_path.exists():
            candidates.append(env_path)
        example_path = root / 'env.example'
        if example_path.exists():
            candidates.append(example_path)
        for path in candidates:
            for line in path.read_text(encoding='utf-8').splitlines():
                line = line.strip()
                if not line or line.startswith('#'):
                    continue
                if '=' not in line:
                    continue
                key, val = line.split('=', 1)
                key = key.strip()
                val = val.strip().strip('"').strip("'")
                # Do not overwrite existing envs
                if key and key not in os.environ:
                    os.environ[key] = val
    except Exception:
        pass


def fetch_assets(supabase, limit_assets: int | None) -> List[Dict]:
    res = supabase.client.table('assets').select('id, symbol, name').execute()
    assets = res.data or []
    if limit_assets:
        assets = assets[:limit_assets]
    return assets


def fetch_price_history(supabase, asset_id: str, start_iso: str, end_iso: str) -> pd.DataFrame:
    q = (
        supabase.client.table('price_history')
        .select('timestamp, close')
        .eq('asset_id', asset_id)
        .gte('timestamp', start_iso)
        .lte('timestamp', end_iso)
        .order('timestamp')
    )
    res = q.execute()
    df = pd.DataFrame(res.data or [])
    if not df.empty:
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        df = df.drop_duplicates(subset=['timestamp'], keep='last').sort_values('timestamp')
    return df


def compute_corr_matrix(price_map: Dict[str, pd.DataFrame], method: str) -> pd.DataFrame:
    series_map = {}
    for symbol, df in price_map.items():
        if df is None or df.empty:
            continue
        if 'close' not in df.columns:
            continue
        s = df.set_index('timestamp')['close'].astype(float)
        s = s.where(s > 0).dropna()
        if s.size >= 3:
            series_map[symbol] = s
    if len(series_map) < 2:
        return pd.DataFrame()
    prices = pd.concat(series_map, axis=1).sort_index()
    # Compute log returns with numpy (vectorized) and keep as DataFrame
    import numpy as np
    returns = pd.DataFrame(
        np.log(prices / prices.shift(1)), index=prices.index, columns=prices.columns
    )
    # Pylance typing: cast to accepted literal values
    corr_method = cast(Literal['pearson', 'kendall', 'spearman'], method)
    corr = returns.corr(method=corr_method)
    if corr is None or corr.empty:
        return pd.DataFrame()
    # Ensure diagonal = 1
    for i, c in enumerate(corr.columns):
        corr.iat[i, i] = 1.0
    return corr


def store_correlation_matrix(supabase, corr_df: pd.DataFrame, granularity: str, method: str, start_iso: str, end_iso: str) -> bool:
    if corr_df is None or corr_df.empty:
        return False
    # Convert DF to nested dict of floats
    corr_dict: Dict[str, Dict[str, float]] = {}
    for r_label in corr_df.index:
        row = corr_df.loc[r_label]
        r_key = str(r_label)
        corr_dict[r_key] = {str(c): float(row[c]) for c in corr_df.columns}
    payload = {
        'granularity': granularity,
        'method': method,
        'start_date': start_iso,
        'end_date': end_iso,
        'correlation_matrix': corr_dict,
        'assets': list(map(str, corr_df.columns)),
    }
    return supabase.store_correlation_matrix(payload)


def top_pairs_from_matrix(corr_df: pd.DataFrame, min_abs: float, limit: int) -> List[Dict]:
    pairs = []
    if corr_df is None or corr_df.empty:
        return pairs
    cols = list(corr_df.columns)
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            a1, a2 = cols[i], cols[j]
            # .at uses label-based scalar access
            val_raw = corr_df.at[a1, a2]
            try:
                val = float(val_raw)  # type: ignore[arg-type]
            except Exception:
                continue
            if abs(val) >= min_abs:
                pairs.append({'asset1': a1, 'asset2': a2, 'correlation': val})
    pairs.sort(key=lambda p: abs(p['correlation']), reverse=True)
    return pairs[:limit]


def run_cointegration_tests_http(pairs: List[Dict], granularity: str, lookback_days: int, base_url: str = 'http://localhost:8000') -> int:
    ok = 0
    for p in pairs:
        try:
            resp = requests.post(
                f"{base_url}/api/cointegration/test-pair",
                json={
                    'asset1': p['asset1'],
                    'asset2': p['asset2'],
                    'granularity': granularity,
                    'lookback_days': lookback_days,
                },
                timeout=60,
            )
            if resp.status_code == 200:
                ok += 1
            else:
                print(f"Test {p['asset1']}/{p['asset2']} failed: {resp.status_code} {resp.text}")
        except Exception as e:
            print(f"Error testing {p['asset1']}/{p['asset2']}: {e}")
    return ok


def main():
    # Load .env if present so Supabase creds are available
    _load_env_from_file()
    ap = argparse.ArgumentParser()
    ap.add_argument('--lookback-days', type=int, default=180)
    ap.add_argument('--limit-assets', type=int, default=50)
    ap.add_argument('--top-pairs', type=int, default=50)
    ap.add_argument('--granularity', type=str, default='daily', choices=['daily'])
    ap.add_argument('--method', type=str, default='spearman', choices=['spearman', 'pearson'])
    ap.add_argument('--min-corr', type=float, default=0.6)
    ap.add_argument('--run-cointegration', action='store_true')
    args = ap.parse_args()

    supa = get_supabase_client()
    if supa is None:
        print('Supabase client is not configured. Set SUPABASE_URL and SUPABASE_SERVICE_KEY (or SUPABASE_ANON_KEY) in .env')
        print('Tip: copy env.example to .env and fill in your Supabase credentials.')
        print('Alternatively, run inside the backend container where env is already wired:')
        print('  docker compose exec hedgevision-backend python -m api.cli.precompute --method spearman --granularity daily')
        return 1

    # Time window
    end_dt = datetime.now(timezone.utc)
    start_dt = end_dt - timedelta(days=args.lookback_days)
    start_iso = start_dt.isoformat()
    end_iso = end_dt.isoformat()

    print('Fetching assets...')
    assets = fetch_assets(supa, args.limit_assets)
    if not assets:
        print('No assets found in Supabase table "assets"')
        return 1

    print(f"Fetching price_history for {len(assets)} assets...")
    price_map: Dict[str, pd.DataFrame] = {}
    for a in assets:
        df = fetch_price_history(supa, a['id'], start_iso, end_iso)
        if not df.empty:
            price_map[a['symbol']] = df

    if len(price_map) < 2:
        print('Insufficient assets with price data for correlation.')
        return 1

    print(f"Computing {args.method} correlation matrix...")
    corr_df = compute_corr_matrix(price_map, args.method)
    if corr_df.empty:
        print('Correlation matrix computation yielded empty result.')
        return 1

    print('Storing correlation matrix in precomputed_correlations...')
    ok = store_correlation_matrix(supa, corr_df, args.granularity, args.method, start_iso, end_iso)
    print(f"Stored: {ok}")

    print(f"Extracting top pairs with |corr| >= {args.min_corr} (limit {args.top_pairs})...")
    pairs = top_pairs_from_matrix(corr_df, args.min_corr, args.top_pairs)
    print(f"Found {len(pairs)} pairs")

    if args.run_cointegration and pairs:
        print('Running cointegration tests via backend API (cointegration_tests storage)...')
        tested = run_cointegration_tests_http(pairs, args.granularity, args.lookback_days)
        print(f"Cointegration tests completed: {tested}/{len(pairs)}")

    print('Done.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
