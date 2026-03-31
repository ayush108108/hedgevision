import argparse
import itertools
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in os.sys.path:
    os.sys.path.append(BASE_DIR)

from api.utils.pair_validation import (  # type: ignore
    MIN_OBSERVATIONS,
    PairEvaluation,
    SeriesPayload,
    evaluate_pair,
    infer_asset_class,
    prepare_price_series,
)

try:
    from supabase import create_client, Client
except Exception as e:  # pragma: no cover
    raise SystemExit("supabase-py is required. pip install supabase") from e

try:
    import statsmodels.api as sm  # noqa: F401
    from statsmodels.tsa.stattools import coint, adfuller
except Exception as e:  # pragma: no cover
    raise SystemExit("statsmodels is required. pip install statsmodels") from e

def load_env() -> Tuple[str, str]:
    # Prefer .env if present; else environment
    url = os.getenv("SUPABASE_URL", "")
    key = os.getenv("SUPABASE_SERVICE_KEY", "") or os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not url or not key:
        # Try a local .env file manually
        env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", ".env")
        env_path = os.path.abspath(env_path)
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" not in line or line.strip().startswith("#"):
                        continue
                    k, v = line.strip().split("=", 1)
                    os.environ.setdefault(k, v)
            url = os.getenv("SUPABASE_URL", url)
            key = os.getenv("SUPABASE_SERVICE_KEY", key) or os.getenv("SUPABASE_SERVICE_ROLE_KEY", key)
    if not url or not key:
        raise SystemExit("Missing SUPABASE_URL or SUPABASE_SERVICE_KEY in env/.env")
    return url, key


def get_client() -> Client:
    url, key = load_env()
    return create_client(url, key)


def fetch_assets(client: Client, limit: int) -> List[Dict[str, Any]]:
    """Fetch a small asset list with a portable schema.

    Tries (id,symbol); if missing, falls back to (id,yfinance_ticker) and maps it to 'symbol'.
    """
    # Attempt 1: id + symbol
    try:
        resp = client.table("assets").select("id,symbol").order("symbol").limit(limit).execute()
        data = resp.data or []
        seen, out = set(), []
        for r in data:
            i = r.get("id")
            if i is not None and i not in seen:
                seen.add(i)
                out.append({"id": i, "symbol": r.get("symbol")})
        if out:
            return out
    except Exception as e:
        print(f"Error fetching assets with symbol: {e}")
        pass

    # Attempt 2: id + yfinance_ticker mapped to symbol
    resp = client.table("assets").select("id,yfinance_ticker").order("yfinance_ticker").limit(limit).execute()
    data = resp.data or []
    seen, out = set(), []
    for r in data:
        i = r.get("id")
        if i is not None and i not in seen:
            seen.add(i)
            sym = r.get("yfinance_ticker") or r.get("id")
            out.append({"id": i, "symbol": sym})
    return out


def fetch_prices(client: Client, asset_id: Any, start: str, end: str) -> pd.DataFrame:
    # Try adjusted_close first, otherwise close
    cols = "timestamp,adjusted_close,close"
    resp = (
        client.table("price_history")
        .select(cols)
        .eq("asset_id", asset_id)
        .gte("timestamp", start)
        .lte("timestamp", end)
        .order("timestamp", desc=False)
        .execute()
    )
    rows = resp.data or []
    if not rows:
        return pd.DataFrame(columns=["timestamp", "close"])
    df = pd.DataFrame(rows)
    price_col = "adjusted_close" if "adjusted_close" in df.columns and df["adjusted_close"].notna().any() else "close"
    df = df[["timestamp", price_col]].rename(columns={price_col: "close"})
    # Normalize timestamp to UTC
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True)
    # Ensure numeric and positive
    df["close"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna().query("close > 0")
    return df


def build_series_payloads(
    client: Client,
    assets: List[Dict[str, Any]],
    start_iso: str,
    end_iso: str,
) -> Dict[int, SeriesPayload]:
    payloads: Dict[int, SeriesPayload] = {}
    for asset in assets:
        asset_id = asset["id"]
        symbol = str(asset.get("symbol") or asset_id)
        asset_class = infer_asset_class(symbol)
        raw = fetch_prices(client, asset_id, start_iso, end_iso)
        payloads[asset_id] = prepare_price_series(raw, symbol, asset_class)
    return payloads


def compute_pairs(
    pair_payloads: Dict[int, SeriesPayload],
    args: argparse.Namespace,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    results: List[Dict[str, Any]] = []
    diagnostics: List[Dict[str, Any]] = []
    for (id1, payload1), (id2, payload2) in itertools.combinations(
        pair_payloads.items(), 2
    ):
        evaluation: PairEvaluation = evaluate_pair(
            payload1, payload2, min_obs=MIN_OBSERVATIONS
        )
        diag_entry = {
            "asset1_id": id1,
            "asset2_id": id2,
            "asset1_symbol": payload1.symbol,
            "asset2_symbol": payload2.symbol,
            **evaluation.diagnostics,
        }
        diagnostics.append(diag_entry)

        if not evaluation.passed:
            continue

        stats = evaluation.stats
        results.append(
            {
                "asset1_id": id1,
                "asset2_id": id2,
                "asset1_symbol": payload1.symbol,
                "asset2_symbol": payload2.symbol,
                "window_days": args.lookback_days,
                "alpha_intercept": stats.get("alpha_intercept"),
                "beta_coefficient": stats.get("beta_coefficient"),
                "eg_pvalue": stats.get("eg_pvalue"),
                "adf_pvalue": stats.get("adf_pvalue"),
                "half_life_days": stats.get("half_life_days"),
                "mean_reversion_speed": stats.get("mean_reversion_speed"),
                "hurst": stats.get("hurst"),
                "r_squared": stats.get("r_squared"),
                "observations": stats.get("observations"),
            }
        )
    return results, diagnostics


def write_output(
    args: argparse.Namespace,
    assets: List[Dict[str, Any]],
    payloads: Dict[int, SeriesPayload],
    pairs: List[Dict[str, Any]],
    diagnostics: List[Dict[str, Any]],
    start_iso: str,
    end_iso: str,
) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    asset_metadata = {
        asset_id: payload.metadata for asset_id, payload in payloads.items()
    }
    payload = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "asset_count": len(assets),
        "pair_count": len(pairs),
        "window_days": args.lookback_days,
        "start": start_iso,
        "end": end_iso,
        "pairs": pairs,
        "diagnostics": diagnostics,
        "asset_metadata": asset_metadata,
    }
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    print(f"Wrote sample metrics for {len(pairs)} validated pairs to {args.output}")


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(
        description="Compute cointegration metrics for a small sample (no DB writes)."
    )
    ap.add_argument("--limit-assets", type=int, default=10, help="How many assets to sample")
    ap.add_argument("--lookback-days", type=int, default=252, help="Historical window size")
    ap.add_argument(
        "--end",
        type=str,
        default="2024-01-01T00:00:00Z",
        help="End timestamp (UTC ISO). Default: 2024-01-01 (based on data availability)",
    )
    ap.add_argument(
        "--output",
        type=str,
        default="backend/output/cointegration_sample_10.json",
        help="Output JSON path",
    )
    return ap.parse_args()


def setup_dates(args: argparse.Namespace) -> Tuple[str, str]:
    end_dt = (
        datetime.fromisoformat("2024-01-01T00:00:00+00:00")
        if args.end is None
        else datetime.fromisoformat(args.end.replace("Z", "+00:00")).astimezone(timezone.utc)
    )
    start_dt = end_dt - timedelta(days=int(args.lookback_days))
    start_iso = start_dt.isoformat().replace("+00:00", "Z")
    end_iso = end_dt.isoformat().replace("+00:00", "Z")
    return start_iso, end_iso


def main() -> None:
    args = parse_args()
    client = get_client()
    start_iso, end_iso = setup_dates(args)

    assets = fetch_assets(client, args.limit_assets)
    if not assets:
        raise SystemExit("No assets found to compute on.")

    payloads = build_series_payloads(client, assets, start_iso, end_iso)
    pairs, diagnostics = compute_pairs(payloads, args)
    write_output(args, assets, payloads, pairs, diagnostics, start_iso, end_iso)


if __name__ == "__main__":
    main()
