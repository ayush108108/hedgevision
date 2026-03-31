"""Build a unified dual-provider audit input bundle.

Collects:
- Cointegration sample JSON (metrics)
- Supabase cointegration_scores rows for involved asset IDs (if table populated)
- Recent price_history rows per asset (full window subset)
- Logic/script metadata for reproducibility

Output: backend/output/dual_provider_input.json

Env requirements:
  SUPABASE_URL
  SUPABASE_SERVICE_KEY (or SUPABASE_SERVICE_ROLE_KEY)
Optional env overrides:
  SAMPLE_PATH (default backend/output/cointegration_sample_5.json)
  PRICE_ROWS_LIMIT (default 500)
  INCLUDE_COIN_ROWS (default true)

This bundle is then referenced by the dual provider audit runner.
"""
from __future__ import annotations

import json
import os
import sys
from typing import Any, Dict, List, Set
from datetime import datetime, timezone

# Add backend to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load configuration (includes .env loading)
from api.utils.config import get_config

DEFAULT_SAMPLE = "backend/output/cointegration_sample_5.json"
OUTPUT_PATH = "backend/output/dual_provider_input.json"

try:
    from supabase import create_client  # type: ignore
except Exception as e:  # pragma: no cover
    raise SystemExit("supabase-py required. pip install supabase") from e


def _get_env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y"}


def load_sample(path: str) -> Dict[str, Any]:
    if not os.path.exists(path):
        raise SystemExit(f"Sample file not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def get_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise SystemExit("SUPABASE_URL and SUPABASE_SERVICE_KEY (or SERVICE_ROLE_KEY) must be set")
    return create_client(url, key)


def collect_asset_ids(pairs: List[Dict[str, Any]]) -> List[int]:
    s: Set[int] = set()
    for p in pairs:
        for k in ("asset1_id", "asset2_id"):
            v = p.get(k)
            if isinstance(v, int):
                s.add(v)
    return sorted(s)


def fetch_cointegration_rows(client, asset_ids: List[int]) -> List[Dict[str, Any]]:
    if not asset_ids:
        return []
    # We need rows where asset1_id or asset2_id in asset_ids. Build OR filter.
    # supabase-py doesn't have a direct OR for two IN filters elegantly; fallback to two queries merged.
    rows: Dict[int, Dict[str, Any]] = {}
    for col in ("asset1_id", "asset2_id"):
        resp = (
            client.table("cointegration_tests")
            .select("*")
            .in_(col, asset_ids)
            .limit(10000)
            .execute()
        )
        for r in resp.data or []:
            rid = r.get("id")
            if rid is not None:
                rows[rid] = r
    return list(rows.values())


def fetch_price_rows(client, asset_ids: List[int], limit_per_asset: int) -> Dict[str, List[Dict[str, Any]]]:
    out: Dict[str, List[Dict[str, Any]]] = {}
    if not asset_ids:
        return out
    
    # Optimized: Single query with IN filter, then group and limit in code
    resp = (
        client.table("price_history")
        .select("id,asset_id,timestamp,adjusted_close,close,volume")
        .in_("asset_id", asset_ids)
        .order("asset_id,timestamp", desc=False)
        .execute()
    )
    all_rows = resp.data or []
    
    # Group by asset_id
    from collections import defaultdict
    grouped: Dict[int, List[Dict[str, Any]]] = defaultdict(list)
    for row in all_rows:
        aid = row.get("asset_id")
        if aid in asset_ids:
            grouped[aid].append(row)
    
    # Apply limit per asset
    for aid in asset_ids:
        rows = grouped.get(aid, [])
        out[str(aid)] = rows[:limit_per_asset]
    
    return out


def main():
    sample_path = os.getenv("SAMPLE_PATH", DEFAULT_SAMPLE)
    price_limit = int(os.getenv("PRICE_ROWS_LIMIT", "500"))
    include_coin = _get_env_bool("INCLUDE_COIN_ROWS", True)

    sample = load_sample(sample_path)
    pairs = sample.get("pairs", [])
    asset_ids = collect_asset_ids(pairs)

    client = get_client()

    coin_rows = fetch_cointegration_rows(client, asset_ids) if include_coin else []
    price_rows = fetch_price_rows(client, asset_ids, price_limit)

    bundle = {
        "generated_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "sample_path": sample_path,
        "asset_ids": asset_ids,
        "pair_count": len(pairs),
        "price_rows_limit": price_limit,
        "pairs": pairs,
        "cointegration_rows": coin_rows,
        "price_rows_by_asset": price_rows,
        "logic": {
            "cointegration_sample_script": "backend/scripts/compute_cointegration_sample.py",
            "service_logic": "backend/api/services/cointegration_service.py",
            "tests": [
                "tests/test_cointegration_infinite_half_life.py",
                "tests/test_cointegration_service_unit.py",
            ],
            "notes": "Bundle aggregates metrics + raw supporting rows for dual provider validation.",
        },
        "meta": {
            "window_days": sample.get("window_days"),
            "start": sample.get("start"),
            "end": sample.get("end"),
            "asset_count": sample.get("asset_count"),
            "observation_uniformity_note": "Investigate identical observation counts across pairs.",
        },
    }

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(bundle, f, indent=2)
    print(f"Wrote dual provider bundle to {OUTPUT_PATH} (assets={len(asset_ids)}, pairs={len(pairs)})")


if __name__ == "__main__":  # pragma: no cover
    main()
