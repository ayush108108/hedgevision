#!/usr/bin/env python3
"""
Bootstrap core asset symbols into Supabase `assets` table.

Idempotent: existing symbols are skipped (uses upsert on unique symbol).
Symbols chosen for broad coverage: US equities + ETF + large cap tech.

Usage (PowerShell):
  python backend/scripts/bootstrap_assets.py --symbols SPY,AAPL,MSFT,GOOGL,AMZN,META,NVDA,TSLA --commit

Without --commit it runs a dry-run preview.
"""
from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List, Tuple

# Ensure backend package root is on sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

try:
    from supabase import create_client
    from api.utils.config import get_config
except Exception as e:
    print(f"Import error: {e}")
    sys.exit(1)


PRESET_SYMBOL_GROUPS = {
    "equities": [
        "KO",
        "PEP",
        "MS",
        "GS",
        "V",
        "MA",
        "JPM",
        "BAC",
        "CVX",
        "XOM",
        "WMT",
        "TGT",
        "UPS",
        "FDX",
        "HD",
        "LOW",
        "AAPL",
        "MSFT",
        "RDSA",
        "BP",
        "RIO",
        "BHP",
        "TM",
        "HMC",
        "AMD",
        "NVDA",
        "INTC",
        "CRM",
        "NOW",
        "ADBE",
        "INTU",
        "SQ",
        "PYPL",
        "CME",
        "ICE",
        "HAL",
        "SLB",
        "EOG",
        "PXD",
        "DAL",
        "UAL",
        "MAR",
        "HLT",
        "COST",
        "BJ",
        "MCD",
        "SBUX",
        "TSLA",
        "BWA",
        "DE",
        "CAT",
        "NEM",
        "FNV",
        "SHW",
        "PPG",
        "CLX",
        "CHD",
        "ORCL",
        "IBM",
        "PANW",
        "CRWD",
        "NFLX",
        "DIS",
        "UBER",
        "LYFT",
        "BABA",
        "JD",
        "PDD",
        "FXI",
        "KWEB",
        "XLF",
        "KBE",
        "XLY",
        "XLP",
        "IYR",
        "VNQ",
        "XBI",
        "IBB",
        "KRE",
        "INDA",
        "MCHI",
        "ARKK",
        "QQQ",
    ],
    "index_etf": [
        "SPY",
        "VOO",
        "QQQ",
        "XLK",
        "IWM",
        "SLYV",
        "EFA",
        "EEM",
        "XLE",
        "XOP",
        "TLT",
        "IEF",
        "HYG",
        "JNK",
        "LQD",
        "IGLB",
        "GLD",
        "IAU",
        "SLV",
        "SIL",
    ],
    "fx": [
        "EURUSD",
        "GBPUSD",
        "AUDUSD",
        "NZDUSD",
        "USDJPY",
        "CNHJPY",
        "NKY",
        "USDCAD",
        "WTI",
        "CHFJPY",
        "XAUUSD",
    ],
    "commodities": [
        "XAGUSD",
        "BRENT",
        "WTI",
        "CORN",
        "SOYBEAN",
        "NG1",
        "UKNG",
        "HG1",
        "NI1",
    ],
    "crypto": [
        "BTC",
        "ETH",
        "SOL",
        "AVAX",
        "MATIC",
        "FTM",
        "ATOM",
        "OSMO",
        "BNB",
        "ADA",
        "DOT",
        "KSM",
        "LTC",
        "BCH",
        "XRP",
        "XLM",
        "AAVE",
        "COMP",
        "UNI",
        "SUSHI",
        "MKR",
        "SNX",
        "CRV",
        "LINK",
        "BAND",
        "ARB",
        "OP",
        "MANTA",
        "DOGE",
        "SHIB",
        "RUNE",
        "DYDX",
        "GMX",
        "INJ",
        "PERP",
        "APT",
        "SUI",
        "NEAR",
        "FIL",
        "AR",
        "RNDR",
        "AGIX",
        "GRT",
        "OCEAN",
        "TIA",
        "SEI",
        "JUP",
        "ORCA",
        "LDO",
        "RPL",
        "YFI",
        "CVX",
        "ZEC",
        "DASH",
        "ETC",
        "ETHW",
    ],
}

# Cross-asset sample used for pilot validation runs
PILOT_SYMBOLS = [
    "SPY",
    "QQQ",
    "KO",
    "PEP",
    "USDJPY",
    "EURUSD",
    "XAUUSD",
    "WTI",
    "BTC",
    "ETH",
]

PRESET_SYMBOL_GROUPS["pilot"] = PILOT_SYMBOLS

PRESET_CHOICES = sorted(PRESET_SYMBOL_GROUPS.keys()) + ["all"]


def parse_args() -> argparse.Namespace:
    ap = argparse.ArgumentParser(description="Bootstrap assets into Supabase")
    ap.add_argument(
        "--symbols",
        type=str,
        default="",
        help="Comma-separated list of symbols to upsert (in addition to presets)",
    )
    ap.add_argument(
        "--presets",
        type=str,
        default="all",
        help=f"Comma-separated presets to include ({', '.join(PRESET_CHOICES)})",
    )
    ap.add_argument(
        "--commit",
        action="store_true",
        help="Actually perform upsert; otherwise dry-run",
    )
    return ap.parse_args()


def detect_identifier_column(client) -> Tuple[str, Dict[str, bool]]:
    """
    Determine which identifier column is available in the assets table.
    Preference order: symbol -> yfinance_ticker -> name.
    Returns (column_name, flags) where flags indicate which supporting columns exist.
    """
    candidates = ["symbol", "yfinance_ticker", "name"]
    available_flags: Dict[str, bool] = {}

    sample_row = None
    try:
        resp = client.table("assets").select("*").limit(1).execute()
        if getattr(resp, "data", None):
            sample_row = resp.data[0]
    except Exception:
        sample_row = None

    if sample_row:
        for key in sample_row.keys():
            available_flags[key] = True

    for col in candidates:
        try:
            resp = client.table("assets").select(f"id,{col}").limit(1).execute()
            data = getattr(resp, "data", None)
            if data is not None:
                # column exists even if rows empty
                return col, available_flags
        except Exception:
            continue

    raise RuntimeError("Unable to detect identifier column (symbol/yfinance_ticker/name missing).")


def get_existing_symbols(client, identifier_column: str) -> Dict[str, int]:
    select_clause = f"id,{identifier_column}"
    try:
        resp = client.table("assets").select(select_clause).limit(2000).execute()
        rows = getattr(resp, "data", None) or []
        existing = {}
        for r in rows:
            identifier = r.get(identifier_column)
            if identifier:
                existing[str(identifier).upper()] = int(r["id"])
        return existing
    except Exception:
        return {}


def build_rows(symbols: List[str], identifier_column: str, available_flags: Dict[str, bool]) -> List[Dict]:
    rows = []
    for sym in symbols:
        sym_upper = sym.upper()
        row: Dict[str, Any] = {"is_active": 1}
        row[identifier_column] = sym_upper

        if available_flags.get("name"):
            row.setdefault("name", sym_upper)
        if available_flags.get("yfinance_ticker"):
            row.setdefault("yfinance_ticker", sym_upper)
        if available_flags.get("tiingo_ticker"):
            row.setdefault("tiingo_ticker", sym_upper)
        if available_flags.get("polygon_ticker"):
            row.setdefault("polygon_ticker", sym_upper if "-" not in sym_upper else sym_upper.replace("-", ""))
        rows.append(row)
    return rows


def main() -> int:
    args = parse_args()
    preset_names = [p.strip().lower() for p in args.presets.split(",") if p.strip()]
    preset_symbols = []
    if not preset_names or "all" in preset_names:
        for group in PRESET_SYMBOL_GROUPS.values():
            preset_symbols.extend(group)
    else:
        unknown = [p for p in preset_names if p not in PRESET_SYMBOL_GROUPS]
        if unknown:
            print(f"Unknown presets: {', '.join(unknown)}")
            print(f"Valid presets: {', '.join(PRESET_CHOICES)}")
            return 1
        for name in preset_names:
            preset_symbols.extend(PRESET_SYMBOL_GROUPS[name])

    additional_symbols = [s.strip().upper() for s in args.symbols.split(",") if s.strip()]
    seen = set()

    def dedupe(seq):
        for sym in seq:
            sym_upper = sym.upper()
            if sym_upper not in seen:
                seen.add(sym_upper)
                yield sym_upper

    target_symbols = list(dedupe(preset_symbols + additional_symbols))
    cfg = get_config()
    supabase_key = cfg.get("SUPABASE_SERVICE_KEY") or cfg.get("SUPABASE_KEY")
    if not supabase_key:
        print("Missing Supabase key. Ensure SUPABASE_SERVICE_KEY or SUPABASE_KEY is set.")
        return 1
    if not cfg.get("SUPABASE_URL") or not supabase_key:
        print("Missing SUPABASE_URL and Supabase key env vars")
        return 1
    client = create_client(cfg["SUPABASE_URL"], supabase_key)

    try:
        identifier_column, available_flags = detect_identifier_column(client)
    except RuntimeError as err:
        print(str(err))
        return 1

    existing = get_existing_symbols(client, identifier_column)
    to_insert = [s for s in target_symbols if s not in existing]
    rows = build_rows(to_insert, identifier_column, available_flags)

    sample_existing = ", ".join(list(existing.keys())[:10])
    if len(existing) > 10:
        sample_existing += "..."
    print(f"Identifier column: {identifier_column}")
    print(f"Existing identifiers ({len(existing)}): {sample_existing}")
    print(f"Target identifiers ({len(target_symbols)}): {', '.join(target_symbols)}")
    print(f"Will add {len(rows)} new identifiers: {', '.join(to_insert)}")

    if not args.commit:
        print("Dry run complete (use --commit to apply).")
        return 0

    if rows:
        try:
            client.table("assets").insert(rows).execute()
            print(f"Inserted {len(rows)} new assets.")
        except Exception as e:
            print(f"Upsert error: {e}")
            return 1
    else:
        print("No new assets to insert.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
