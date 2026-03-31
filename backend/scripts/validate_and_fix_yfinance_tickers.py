"""Validate and backfill yfinance tickers for assets that lack one.

Usage
-----
    python -m backend.scripts.validate_and_fix_yfinance_tickers
    python -m backend.scripts.validate_and_fix_yfinance_tickers --commit
    python -m backend.scripts.validate_and_fix_yfinance_tickers --commit --skip-validation
"""
from __future__ import annotations

import argparse
import os
from typing import Any

from supabase import create_client  # type: ignore  # noqa: F401 – patched in tests

# ---------------------------------------------------------------------------
# Ticker inference rules
# ---------------------------------------------------------------------------

# Well-known crypto "name" → yfinance ticker mapping.  Lower-case keys.
_CRYPTO_NAME_MAP: dict[str, str] = {
    "bitcoin": "BTC-USD",
    "ethereum": "ETH-USD",
    "solana": "SOL-USD",
    "cardano": "ADA-USD",
    "ripple": "XRP-USD",
    "dogecoin": "DOGE-USD",
    "polkadot": "DOT-USD",
    "chainlink": "LINK-USD",
    "litecoin": "LTC-USD",
    "uniswap": "UNI-USD",
    "avalanche": "AVAX-USD",
    "polygon": "MATIC-USD",
    "cosmos": "ATOM-USD",
    "stellar": "XLM-USD",
    "filecoin": "FIL-USD",
    "tron": "TRX-USD",
    "shiba inu": "SHIB-USD",
    "binancecoin": "BNB-USD",
    "near protocol": "NEAR-USD",
    "algorand": "ALGO-USD",
}


def _infer_ticker(asset: dict[str, Any]) -> str | None:
    """Return a best-guess yfinance ticker symbol or *None* if we cannot infer one."""
    name = (asset.get("name") or "").strip().lower()
    exchange = (asset.get("exchange") or "").strip().upper()

    if exchange == "CRYPTO":
        if name in _CRYPTO_NAME_MAP:
            return _CRYPTO_NAME_MAP[name]
        # Generic fallback: treat the name as the base currency symbol
        # e.g. "BTC" → "BTC-USD" (only if name looks like a simple ticker)
        if name.isalpha() and len(name) <= 6:
            return f"{name.upper()}-USD"
        return None

    # Equity / ETF: name is usually already the ticker or very close
    # We do not mutate equity tickers here.
    return None


def _validate_ticker(ticker: str) -> bool:
    """Return True if yfinance can fetch at least one data point for *ticker*."""
    try:
        import yfinance as yf  # type: ignore

        info = yf.Ticker(ticker).fast_info
        # fast_info is a FastInfo object; presence of 'lastPrice' attr is enough
        last = getattr(info, "last_price", None) or getattr(info, "lastPrice", None)
        return last is not None
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def validate_and_fix_tickers(
    *,
    commit: bool = False,
    skip_validation: bool = False,
) -> dict[str, list[dict[str, Any]]]:
    """Inspect assets table and backfill missing yfinance tickers.

    Parameters
    ----------
    commit:
        If *True*, write updates back to Supabase.
    skip_validation:
        If *True*, skip the live yfinance probe and trust the inferred ticker.

    Returns
    -------
    dict with keys ``"fixed"``, ``"invalid"``, ``"unchanged"``.
    """
    url = os.environ.get("SUPABASE_URL", "")
    key = os.environ.get("SUPABASE_KEY", "")
    supabase = create_client(url, key)

    # Fetch assets without a yfinance ticker
    response = supabase.table("assets").select("*").order("id").execute()
    assets: list[dict[str, Any]] = response.data or []

    fixed: list[dict[str, Any]] = []
    invalid: list[dict[str, Any]] = []
    unchanged: list[dict[str, Any]] = []

    for asset in assets:
        if asset.get("yfinance_ticker") is not None:
            unchanged.append(asset)
            continue

        inferred = _infer_ticker(asset)
        if inferred is None:
            invalid.append(asset)
            continue

        if not skip_validation:
            if not _validate_ticker(inferred):
                invalid.append(asset)
                continue

        # Ticker is good — record as fixed
        fixed.append({**asset, "yfinance_ticker": inferred})

        if commit:
            # Update the assets row
            supabase.table("assets").update({"yfinance_ticker": inferred}).eq(
                "id", asset["id"]
            ).execute()

            # Write an audit record
            supabase.table("assets_yf_audit").insert(
                {
                    "asset_id": asset["id"],
                    "old_ticker": asset.get("yfinance_ticker"),
                    "new_ticker": inferred,
                    "validated": not skip_validation,
                }
            ).execute()

    return {"fixed": fixed, "invalid": invalid, "unchanged": unchanged}


# ---------------------------------------------------------------------------
# CLI entry-point
# ---------------------------------------------------------------------------


def _cli() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--commit",
        action="store_true",
        help="Write changes back to Supabase (default: dry-run)",
    )
    parser.add_argument(
        "--skip-validation",
        action="store_true",
        help="Skip yfinance probe; trust inferred tickers",
    )
    args = parser.parse_args()

    results = validate_and_fix_tickers(
        commit=args.commit,
        skip_validation=args.skip_validation,
    )
    print(f"Fixed   : {len(results['fixed'])}")
    print(f"Invalid : {len(results['invalid'])}")
    print(f"Unchanged: {len(results['unchanged'])}")
    if results["fixed"]:
        for a in results["fixed"]:
            print(f"  + {a.get('name')} → {a.get('yfinance_ticker')}")


if __name__ == "__main__":
    _cli()
