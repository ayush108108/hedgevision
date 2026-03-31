#!/usr/bin/env python3
"""
Input validation guards for statistical calculations.
Add these to prevent NaN/inf issues in production.
"""

import numpy as np
from typing import Tuple

def validate_price_data(prices: np.ndarray, asset_name: str = "asset") -> Tuple[bool, str]:
    """
    Validate price data for statistical calculations.

    Args:
        prices: Array of price values
        asset_name: Name of asset for error messages

    Returns:
        (is_valid, error_message)
    """
    if prices is None or len(prices) == 0:
        return False, f"{asset_name}: No price data provided"

    if not np.isfinite(prices).all():
        return False, f"{asset_name}: Contains NaN or infinite values"

    if (prices <= 0).any():
        return False, f"{asset_name}: Contains zero or negative prices"

    if len(prices) < 30:
        return False, f"{asset_name}: Insufficient data points ({len(prices)} < 30 minimum)"

    # Check for extreme outliers (price changes > 1000%)
    if len(prices) > 1:
        pct_changes = np.abs(np.diff(prices) / prices[:-1])
        if (pct_changes > 10).any():  # 1000% change
            return False, f"{asset_name}: Contains extreme price jumps (>1000% change)"

    return True, ""

def validate_pair_data(asset1_prices: np.ndarray, asset2_prices: np.ndarray) -> Tuple[bool, str]:
    """
    Validate paired price data.

    Args:
        asset1_prices: Prices for first asset
        asset2_prices: Prices for second asset

    Returns:
        (is_valid, error_message)
    """
    # Validate individual assets
    valid1, err1 = validate_price_data(asset1_prices, "Asset 1")
    if not valid1:
        return False, err1

    valid2, err2 = validate_price_data(asset2_prices, "Asset 2")
    if not valid2:
        return False, err2

    # Validate pair consistency
    if len(asset1_prices) != len(asset2_prices):
        return False, f"Price arrays have different lengths: {len(asset1_prices)} vs {len(asset2_prices)}"

    # Check correlation isn't perfect (would cause issues)
    if len(asset1_prices) > 1:
        corr = np.corrcoef(asset1_prices, asset2_prices)[0, 1]
        if not np.isfinite(corr):
            return False, "Cannot compute correlation between assets"
        if abs(corr) > 0.999:
            return False, "Assets are perfectly correlated (correlation > 0.999)"

    return True, ""

def safe_mean_reversion_calculation(spread: np.ndarray) -> Tuple[float, float]:
    """
    Safely calculate mean reversion metrics with input validation.

    Args:
        spread: Spread array

    Returns:
        (half_life, speed) - half_life is inf if no mean reversion
    """
    if len(spread) < 30:
        return float('inf'), 0.0

    try:
        spread_lag = spread[:-1]
        spread_diff = np.diff(spread)

        # Remove any NaN values
        valid_idx = ~(np.isnan(spread_lag) | np.isnan(spread_diff))
        if valid_idx.sum() < 10:  # Need minimum data points
            return float('inf'), 0.0

        spread_lag = spread_lag[valid_idx]
        spread_diff = spread_diff[valid_idx]

        from sklearn.linear_model import LinearRegression
        model = LinearRegression()

        model.fit(spread_lag.reshape(-1, 1), spread_diff)
        lambda_param = -model.coef_[0]

        # Validate lambda parameter
        if not np.isfinite(lambda_param) or lambda_param <= 0:
            return float('inf'), 0.0

        half_life = np.log(2) / lambda_param
        if not np.isfinite(half_life) or half_life <= 0:
            return float('inf'), 0.0

        return float(half_life), float(lambda_param)

    except Exception:
        return float('inf'), 0.0

def safe_hurst_calculation(series: np.ndarray) -> float:
    """
    Safely calculate Hurst exponent with input validation.

    Args:
        series: Time series data

    Returns:
        Hurst exponent (clamped to [0.1, 0.9] for safety)
    """
    if len(series) < 100:  # Need sufficient data
        return 0.5  # Default to random walk

    try:
        lags = range(2, min(100, len(series) // 2))
        if len(lags) < 5:  # Need minimum lags for fitting
            return 0.5

        tau = []
        for lag in lags:
            try:
                std_val = np.std(series[lag:] - series[:-lag])
                if np.isfinite(std_val) and std_val > 0:
                    tau.append(std_val)
            except Exception:
                continue

        if len(tau) < 3:  # Need minimum points for regression
            return 0.5

        # Fit log(tau) vs log(lag)
        log_lags = np.log(lags[:len(tau)])
        log_tau = np.log(tau)

        # Simple linear regression
        slope = np.polyfit(log_lags, log_tau, 1)[0]

        # Clamp to reasonable range
        return max(0.1, min(0.9, slope))

    except Exception:
        return 0.5

# Example usage
if __name__ == "__main__":
    # Test with good data
    good_prices = np.array([100, 101, 102, 103, 104, 105])
    is_valid, error = validate_price_data(good_prices, "Test Asset")
    print(f"Good data valid: {is_valid}, error: '{error}'")

    # Test with bad data
    bad_prices = np.array([100, 101, np.nan, 103, 104])
    is_valid, error = validate_price_data(bad_prices, "Test Asset")
    print(f"Bad data valid: {is_valid}, error: '{error}'")

    # Test pair validation
    asset1 = np.array([100, 101, 102, 103, 104])
    asset2 = np.array([50, 51, 52, 53, 54])
    is_valid, error = validate_pair_data(asset1, asset2)
    print(f"Pair data valid: {is_valid}, error: '{error}'")

    print("✅ Input validation guards ready!")