"""
CLI to precompute correlation matrices and store them in Supabase.

Run inside the backend container so env vars are available:

  python -m api.cli.precompute --method spearman --granularity daily

Optional:
  --min-correlation 0.6  # only affects logging of top pairs summary
  --limit 50              # summary count of top pairs
"""

from __future__ import annotations

import argparse
import logging
from datetime import datetime, timezone
from typing import Dict, Any

import pandas as pd

from api.services import correlation_service
from api.utils.config import config
from api.utils.cache_adapter import get_cache_adapter
from api.utils.supabase_client import get_supabase_client


logger = logging.getLogger(__name__)


def _df_to_nested_dict(df: pd.DataFrame) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    for r in df.index:
        row = df.loc[r]
        out[str(r)] = {str(c): float(row[c]) for c in df.columns}
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--granularity", choices=["daily", "hourly"], default="daily")
    ap.add_argument("--method", choices=["spearman", "pearson"], default="spearman")
    ap.add_argument("--min-periods", type=int, default=60, help="Minimum overlapping periods for correlation")
    ap.add_argument("--min-correlation", type=float, default=0.6, help="For summary output only")
    ap.add_argument("--limit", type=int, default=50, help="For summary output only")
    args = ap.parse_args()

    # Cache adapter for correlation_service
    try:
        cache = get_cache_adapter(default_ttl=config["REDIS_TTL"])  # type: ignore[index]
    except Exception:
        cache = None

    # Compute correlation matrix (asset-level)
    corr_df = correlation_service.get_correlation_data(
        cache,
        start_date=None,
        end_date=None,
        method=args.method,
        granularity=args.granularity,
        min_periods=args.min_periods,
        view_mode="asset",
    )

    if corr_df is None or getattr(corr_df, "empty", True):
        print("Correlation computation returned empty DataFrame.")
        return 1

    # Store to Supabase
    supa = get_supabase_client()
    if supa is None:
        print("Supabase not configured in container env.")
        return 1

    now = datetime.now(timezone.utc)
    payload: Dict[str, Any] = {
        "granularity": args.granularity,
        "method": args.method,
        "start_date": None,
        "end_date": now.isoformat(),
        "correlation_matrix": _df_to_nested_dict(corr_df),
        "assets": list(map(str, corr_df.columns)),
    }

    ok = supa.store_correlation_matrix(payload)
    print(f"Stored correlation matrix to Supabase: {ok}")

    # Optional summary
    try:
        pairs = []
        cols = list(corr_df.columns)
        for i in range(len(cols)):
            for j in range(i + 1, len(cols)):
                a, b = cols[i], cols[j]
                try:
                    val = float(corr_df.at[a, b])  # type: ignore[arg-type]
                except Exception:
                    continue
                if abs(val) >= args.min_correlation:
                    pairs.append((str(a), str(b), float(val)))
        pairs.sort(key=lambda x: abs(x[2]), reverse=True)
        if pairs:
            print("Top pairs (preview):")
            for a, b, v in pairs[: args.limit]:
                print(f"  {a} - {b}: {v:.3f}")
    except Exception:
        pass

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
