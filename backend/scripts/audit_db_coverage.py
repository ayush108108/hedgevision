#!/usr/bin/env python3
"""
Audit DB coverage for EOD and intraday per symbol, plus sanity checks for metrics tables.

Outputs a concise console summary and a JSON report (optional) under backend/output.

Usage (PowerShell):
  python backend/scripts/audit_db_coverage.py --limit 200 --json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Tuple

# Ensure backend package root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from api.utils.config import get_config


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Audit DB coverage and metrics sanity")
    ap.add_argument("--limit", type=int, default=1000, help="Max assets to scan (symbol order)")
    ap.add_argument("--json", action="store_true", help="Write backend/output/db_coverage_report.json")
    return ap.parse_args()


def get_client():
    try:
        from supabase import create_client
    except Exception as e:
        print(f"Supabase client import failed: {e}")
        sys.exit(1)
    cfg = get_config()
    url = cfg.get("SUPABASE_URL")
    key = cfg.get("SUPABASE_SERVICE_KEY") or cfg.get("SUPABASE_KEY")
    if not url or not key:
        print("Missing SUPABASE_URL/SUPABASE_KEY")
        sys.exit(1)
    return create_client(url, key)


def _get_assets(client, limit: int) -> List[Dict[str, Any]]:
    resp = client.table("assets").select("id,symbol").order("symbol").limit(limit).execute()
    return resp.data or []


def _get_min_max(client, table: str, asset_id: int) -> Tuple[str | None, str | None, int]:
    cnt_resp = (
        client.table(table)
        .select("id", count="exact")
        .eq("asset_id", asset_id)
        .limit(1)
        .execute()
    )
    total = cnt_resp.count or 0
    if total == 0:
        return None, None, 0
    # Supabase Python client order() uses 'desc' flag; default asc
    min_resp = (
        client.table(table)
        .select("timestamp")
        .eq("asset_id", asset_id)
        .order("timestamp")  # ascending by default
        .limit(1)
        .execute()
    )
    max_resp = (
        client.table(table)
        .select("timestamp")
        .eq("asset_id", asset_id)
        .order("timestamp", desc=True)
        .limit(1)
        .execute()
    )
    tmin = (min_resp.data or [{}])[0].get("timestamp") if min_resp.data else None
    tmax = (max_resp.data or [{}])[0].get("timestamp") if max_resp.data else None
    return tmin, tmax, total


def audit_prices(client, assets: List[Dict[str, Any]]) -> Dict[str, Any]:
    eod = []
    intra = []
    for a in assets:
        aid = int(a["id"])
        sym = str(a["symbol"])
        tmin, tmax, total = _get_min_max(client, "price_history", aid)
        eod.append({"symbol": sym, "asset_id": aid, "rows": total, "min_ts": tmin, "max_ts": tmax})
        tmin2, tmax2, total2 = _get_min_max(client, "intraday_price_history", aid)
        intra.append({"symbol": sym, "asset_id": aid, "rows": total2, "min_ts": tmin2, "max_ts": tmax2})

    eod_total = sum(x["rows"] for x in eod)
    intra_total = sum(x["rows"] for x in intra)
    eod_cov = {
        "symbols_with_data": sum(1 for x in eod if x["rows"] > 0),
        "symbols_total": len(eod),
        "rows_total": eod_total,
        "rows_median_per_symbol": int(sorted([x["rows"] for x in eod])[len(eod)//2]) if eod else 0,
        "min_date": min((x["min_ts"] for x in eod if x["min_ts"]), default=None),
        "max_date": max((x["max_ts"] for x in eod if x["max_ts"]), default=None),
    }
    intra_cov = {
        "symbols_with_data": sum(1 for x in intra if x["rows"] > 0),
        "symbols_total": len(intra),
        "rows_total": intra_total,
        "rows_median_per_symbol": int(sorted([x["rows"] for x in intra])[len(intra)//2]) if intra else 0,
        "min_ts": min((x["min_ts"] for x in intra if x["min_ts"]), default=None),
        "max_ts": max((x["max_ts"] for x in intra if x["max_ts"]), default=None),
    }
    return {"eod": eod, "intraday": intra, "eod_summary": eod_cov, "intraday_summary": intra_cov}


def audit_metrics(client) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    cs = client.table("cointegration_scores").select("id", count="exact").limit(1).execute()
    ct = client.table("cointegration_tests").select("id", count="exact").limit(1).execute()
    rm = client.table("rolling_metrics").select("id", count="exact").limit(1).execute()
    cm = client.table("correlation_matrix").select("id", count="exact").limit(1).execute()
    out["counts"] = {
        "cointegration_scores": cs.count or 0,
        "cointegration_tests": ct.count or 0,
        "rolling_metrics": rm.count or 0,
        "correlation_matrix": cm.count or 0,
    }

    issues = []
    try:
        resp = client.table("cointegration_scores").select(
            "id,eg_pvalue,adf_pvalue,r_squared"
        ).limit(1000).execute()
        for r in resp.data or []:
            eg = r.get("eg_pvalue")
            adf = r.get("adf_pvalue")
            r2 = r.get("r_squared")
            if eg is not None and not (0 <= eg <= 1):
                issues.append({"table":"cointegration_scores","id":r.get("id"),"field":"eg_pvalue","value":eg})
            if adf is not None and not (0 <= adf <= 1):
                issues.append({"table":"cointegration_scores","id":r.get("id"),"field":"adf_pvalue","value":adf})
            if r2 is not None and not (0 <= r2 <= 1):
                issues.append({"table":"cointegration_scores","id":r.get("id"),"field":"r_squared","value":r2})
    except Exception:
        pass

    try:
        resp = client.table("cointegration_tests").select(
            "id,eg_pvalue,johansen_trace_pvalue,johansen_eigen_pvalue,adf_pvalue,pp_pvalue,kpss_pvalue,zscore_std"
        ).limit(1000).execute()
        for r in resp.data or []:
            for f in ["eg_pvalue","johansen_trace_pvalue","johansen_eigen_pvalue","adf_pvalue","pp_pvalue","kpss_pvalue"]:
                v = r.get(f)
                if v is not None and not (0 <= v <= 1):
                    issues.append({"table":"cointegration_tests","id":r.get("id"),"field":f,"value":v})
            zs = r.get("zscore_std")
            if zs is not None and zs <= 0:
                issues.append({"table":"cointegration_tests","id":r.get("id"),"field":"zscore_std","value":zs})
    except Exception:
        pass

    out["sanity_issues_sample"] = issues[:50]
    return out


def main() -> int:
    args = parse_args()
    client = get_client()
    assets = _get_assets(client, args.limit)
    price_report = audit_prices(client, assets)
    metrics_report = audit_metrics(client)

    print("\n== EOD coverage ==")
    print(json.dumps(price_report["eod_summary"], indent=2))
    print("\n== Intraday coverage ==")
    print(json.dumps(price_report["intraday_summary"], indent=2))
    print("\n== Metrics counts ==")
    print(json.dumps(metrics_report["counts"], indent=2))
    if metrics_report.get("sanity_issues_sample"):
        print("\nSample potential issues (first 50):")
        print(json.dumps(metrics_report["sanity_issues_sample"], indent=2))
    else:
        print("\nNo obvious issues in sampled metrics fields.")

    if args.json:
        out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "output")
        os.makedirs(out_dir, exist_ok=True)
        from datetime import timezone
        report = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "price": price_report,
            "metrics": metrics_report,
        }
        out_path = os.path.join(out_dir, "db_coverage_report.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2)
        print(f"\nWrote JSON report to {out_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
