"""
Pair validation utilities for cointegration testing.

Provides a single source of truth for data alignment, statistical testing,
and quality gating across sampling scripts and the analytics pipeline.
"""

from __future__ import annotations

import hashlib
import math
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import numpy as np
import pandas as pd
from statsmodels.regression.linear_model import OLS
from statsmodels.tools.tools import add_constant
from statsmodels.tsa.stattools import adfuller, coint

# --------------------------------------------------------------------------- #
# Configuration constants
# --------------------------------------------------------------------------- #

MIN_OBSERVATIONS = 100
MAX_MISSING_RATIO = 0.10  # 10%
HALF_LIFE_THRESHOLD = 20.0
HURST_THRESHOLD = 0.5
RSQUARED_THRESHOLD = 0.30
P_VALUE_THRESHOLD = 0.05

BUSINESS_DAY_CLASSES = {"equity", "etf", "commodity", "future"}


# --------------------------------------------------------------------------- #
# Dataclasses
# --------------------------------------------------------------------------- #

@dataclass
class SeriesPayload:
    """Normalized price series and provenance metadata."""

    symbol: str
    asset_class: str
    series: pd.Series
    metadata: Dict[str, Any]


@dataclass
class PairEvaluation:
    """Result of evaluating a pair for cointegration suitability."""

    passed: bool
    reason: Optional[str]
    stats: Dict[str, Any]
    diagnostics: Dict[str, Any]


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #


def infer_asset_class(symbol: str) -> str:
    """Infer asset class from symbol naming conventions."""

    s = (symbol or "").upper()
    if not s:
        return "unknown"

    crypto_markers = ("-USD", "-USDT", "-BTC")
    if any(marker in s for marker in crypto_markers):
        return "crypto"
    if s.endswith("=X") or s in {"EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "NZDUSD"}:
        return "fx"
    if s.endswith("=F"):
        return "commodity"
    return "equity"


def _hash_series(series: pd.Series) -> str:
    if series.empty:
        return ""
    payload = ";".join(
        f"{ts.isoformat()}|{float(val):.10f}"
        for ts, val in series.items()
        if np.isfinite(val)
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def prepare_price_series(
    df: pd.DataFrame, symbol: str, asset_class: str
) -> SeriesPayload:
    """Normalize price data to daily frequency and compile provenance metadata."""

    metadata: Dict[str, Any] = {
        "symbol": symbol,
        "asset_class": asset_class,
        "raw_row_count": int(len(df)),
    }

    if df.empty:
        metadata.update(
            {
                "row_count": 0,
                "start": None,
                "end": None,
                "provenance_hash": "",
            }
        )
        return SeriesPayload(symbol, asset_class, pd.Series(dtype=float), metadata)

    df = df.copy()
    # Accept either `timestamp` or `date` (standardizer uses `date`) to support both
    # formats across the codebase. Prefer `timestamp` if present, else fall back to `date`.
    if "timestamp" not in df.columns and "date" in df.columns:
        df["timestamp"] = df["date"]

    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df = df.dropna(subset=["timestamp"])
    df["price"] = pd.to_numeric(df["close"], errors="coerce")
    df = df.dropna(subset=["price"]).sort_values("timestamp")
    if df.empty:
        metadata.update(
            {
                "row_count": 0,
                "start": None,
                "end": None,
                "provenance_hash": "",
            }
        )
        return SeriesPayload(symbol, asset_class, pd.Series(dtype=float), metadata)

    df = df.set_index("timestamp")
    freq = "1B" if asset_class in BUSINESS_DAY_CLASSES else "1D"
    series = df["price"].resample(freq).last().ffill()
    series = series.dropna()

    metadata.update(
        {
            "row_count": int(len(series)),
            "start": series.index[0].isoformat() if not series.empty else None,
            "end": series.index[-1].isoformat() if not series.empty else None,
            "provenance_hash": _hash_series(series),
            "resample_frequency": freq,
        }
    )
    return SeriesPayload(symbol, asset_class, series, metadata)


def _alignment_failure(reason: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    payload = {"passed": False, "reason": reason}
    if extra:
        payload.update(extra)
    return payload


def align_pair(
    series_a: SeriesPayload,
    series_b: SeriesPayload,
    min_obs: int = MIN_OBSERVATIONS,
) -> Tuple[Optional[pd.DataFrame], Dict[str, Any]]:
    """Align series and enforce coverage ratio requirements."""

    if series_a.asset_class != series_b.asset_class:
        return None, _alignment_failure(
            "asset_class_mismatch",
            {"asset_class_a": series_a.asset_class, "asset_class_b": series_b.asset_class},
        )

    s1, s2 = series_a.series, series_b.series
    if s1.empty or s2.empty:
        return None, _alignment_failure("empty_series", {"rows_a": len(s1), "rows_b": len(s2)})

    aligned_index = s1.index.intersection(s2.index).sort_values()
    if len(aligned_index) < min_obs:
        return None, _alignment_failure(
            "insufficient_overlap",
            {"overlap_rows": int(len(aligned_index)), "min_required": int(min_obs)},
        )

    aligned = pd.DataFrame(
        {
            "price_1": s1.reindex(aligned_index),
            "price_2": s2.reindex(aligned_index),
        }
    ).dropna()

    if len(aligned) < min_obs:
        return None, _alignment_failure(
            "insufficient_after_dropna",
            {"rows_after_dropna": int(len(aligned)), "min_required": int(min_obs)},
        )

    coverage_a = 1.0 - (len(aligned) / max(len(s1), 1))
    coverage_b = 1.0 - (len(aligned) / max(len(s2), 1))

    if coverage_a > MAX_MISSING_RATIO or coverage_b > MAX_MISSING_RATIO:
        return None, _alignment_failure(
            "coverage_mismatch",
            {
                "coverage_a": float(coverage_a),
                "coverage_b": float(coverage_b),
                "threshold": float(MAX_MISSING_RATIO),
                "rows_aligned": int(len(aligned)),
            },
        )

    diagnostics = {
        "rows_aligned": int(len(aligned)),
        "coverage_ratio_a": float(coverage_a),
        "coverage_ratio_b": float(coverage_b),
        "start": aligned.index[0].isoformat(),
        "end": aligned.index[-1].isoformat(),
    }

    return aligned, diagnostics


def _compute_hurst_exponent(series: np.ndarray) -> float:
    series = np.asarray(series, dtype=float)
    if series.size < 50 or not np.isfinite(series).all():
        return float("nan")

    lags = range(2, min(100, series.size // 2))
    if len(list(lags)) < 2:
        return float("nan")

    tau = []
    for lag in lags:
        diff = series[lag:] - series[:-lag]
        tau.append(math.sqrt(np.std(diff)))

    tau = np.array(tau)
    with np.errstate(divide="ignore", invalid="ignore"):
        poly = np.polyfit(np.log(list(lags)), np.log(tau), 1)
    hurst = float(2 * poly[0])
    return hurst


def _compute_mean_reversion(spread: np.ndarray) -> Tuple[float, float]:
    """Return (phi, half_life)."""

    spread = np.asarray(spread, dtype=float)
    if spread.size < 10 or not np.isfinite(spread).all():
        return float("nan"), float("inf")

    y = spread[1:]
    x = spread[:-1]

    X = np.column_stack([np.ones_like(x), x])
    try:
        params = np.linalg.lstsq(X, y, rcond=None)[0]
        phi = float(params[1])
    except (np.linalg.LinAlgError, ValueError, IndexError):
        return float("nan"), float("inf")

    if not np.isfinite(phi) or phi <= 0 or phi >= 1:
        return phi, float("inf")

    half_life = float(-np.log(2) / np.log(phi))
    return phi, half_life


def compute_pair_statistics(aligned: pd.DataFrame) -> Dict[str, Any]:
    """Compute Engle-Granger, ADF, R², Hurst, and mean reversion metrics."""

    prices1 = aligned["price_1"].values.astype(float)
    prices2 = aligned["price_2"].values.astype(float)

    log1 = np.log(prices1)
    log2 = np.log(prices2)

    X = add_constant(log2)
    model = OLS(log1, X).fit()
    alpha = float(model.params[0])
    beta = float(model.params[1])
    r_squared = float(model.rsquared)

    residuals = model.resid

    eg_stat, eg_pvalue, _ = coint(log1, log2)
    adf_stat, adf_pvalue, *_ = adfuller(residuals, autolag="AIC")

    phi, half_life = _compute_mean_reversion(residuals)
    hurst = _compute_hurst_exponent(residuals)

    stats = {
        "alpha_intercept": alpha,
        "beta_coefficient": beta,
        "r_squared": r_squared,
        "eg_stat": float(eg_stat),
        "eg_pvalue": float(eg_pvalue),
        "adf_stat": float(adf_stat),
        "adf_pvalue": float(adf_pvalue),
        "mean_reversion_phi": float(phi),
        "mean_reversion_speed": float(phi),
        "half_life_days": float(half_life),
        "hurst": float(hurst),
        "observations": int(len(aligned)),
    }
    return stats


def quality_gate(stats: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """Evaluate stats against hard thresholds."""

    checks = [
        (stats.get("eg_pvalue"), lambda v: v is not None and v < P_VALUE_THRESHOLD, "eg_pvalue"),
        (stats.get("adf_pvalue"), lambda v: v is not None and v < P_VALUE_THRESHOLD, "adf_pvalue"),
        (stats.get("hurst"), lambda v: np.isfinite(v) and v < HURST_THRESHOLD, "hurst"),
        (
            stats.get("half_life_days"),
            lambda v: np.isfinite(v) and v < HALF_LIFE_THRESHOLD,
            "half_life_days",
        ),
        (
            stats.get("r_squared"),
            lambda v: np.isfinite(v) and v > RSQUARED_THRESHOLD,
            "r_squared",
        ),
    ]

    for value, predicate, label in checks:
        try:
            if not predicate(value):
                return False, f"{label}_threshold_failed"
        except Exception:
            return False, f"{label}_evaluation_error"

    return True, None


def evaluate_pair(
    series_a: SeriesPayload,
    series_b: SeriesPayload,
    min_obs: int = MIN_OBSERVATIONS,
) -> PairEvaluation:
    """Full validation pipeline for a pair."""

    diagnostics: Dict[str, Any] = {
        "asset1": series_a.metadata,
        "asset2": series_b.metadata,
    }

    aligned, alignment_diag = align_pair(series_a, series_b, min_obs=min_obs)
    diagnostics["alignment"] = alignment_diag

    if aligned is None:
        diagnostics["passed"] = False
        diagnostics["reason"] = alignment_diag.get("reason", "alignment_failed")
        diagnostics["stats"] = {}
        return PairEvaluation(False, diagnostics["reason"], {}, diagnostics)

    stats = compute_pair_statistics(aligned)
    passed, reason = quality_gate(stats)

    diagnostics["passed"] = passed
    diagnostics["reason"] = reason
    diagnostics["stats"] = stats

    return PairEvaluation(passed, reason, stats, diagnostics)
