"""
Cointegration Service - Comprehensive Statistical Testing
Performs multiple cointegration tests and generates trading signals for pairs.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional, Any, Tuple

import numpy as np
import pandas as pd
from scipy import stats

# Statistical testing libraries
from statsmodels.tsa.stattools import adfuller, coint, kpss
from statsmodels.tsa.vector_ar.vecm import coint_johansen

logger = logging.getLogger(__name__)


@dataclass
class CointegrationTestResult:
    """Container for comprehensive cointegration test results"""

    # Pair identification
    asset1_symbol: str
    asset2_symbol: str
    test_date: str
    granularity: str
    lookback_days: int
    sample_size: int

    # Correlation metrics
    pearson_correlation: float
    spearman_correlation: float
    kendall_tau: float
    correlation_pvalue: float
    correlation_significance: str

    # Engle-Granger test
    eg_test_statistic: float
    eg_pvalue: float
    eg_critical_value_1pct: float
    eg_critical_value_5pct: float
    eg_critical_value_10pct: float
    eg_is_cointegrated: bool
    eg_significance_level: str

    # Johansen test
    johansen_trace_stat: float
    johansen_trace_crit_90: float
    johansen_trace_crit_95: float
    johansen_trace_crit_99: float
    johansen_eigen_stat: float
    johansen_eigen_crit_90: float
    johansen_eigen_crit_95: float
    johansen_eigen_crit_99: float
    johansen_rank: int  # Cointegration rank (0, 1, or 2 for pair)
    johansen_is_cointegrated: bool

    # ADF test on residuals
    adf_test_statistic: float
    adf_pvalue: float
    adf_critical_value_1pct: float
    adf_critical_value_5pct: float
    adf_critical_value_10pct: float
    adf_used_lag: int
    adf_is_stationary: bool

    # Phillips-Perron test
    pp_test_statistic: Optional[float]
    pp_pvalue: Optional[float]
    pp_critical_value_1pct: Optional[float]
    pp_critical_value_5pct: Optional[float]
    pp_critical_value_10pct: Optional[float]
    pp_is_stationary: Optional[bool]

    # KPSS test
    kpss_test_statistic: float
    kpss_pvalue: float
    kpss_critical_value_1pct: float
    kpss_critical_value_5pct: float
    kpss_critical_value_10pct: float
    kpss_is_stationary: bool

    # Regression results
    beta_coefficient: float
    alpha_intercept: float
    regression_r_squared: float
    regression_adj_r_squared: float
    regression_f_statistic: float
    regression_f_pvalue: float
    regression_std_error: float
    regression_durbin_watson: float

    # Mean reversion metrics
    half_life_days: float
    mean_reversion_speed: float
    hurst_exponent: float

    # Spread statistics
    spread_mean: float
    spread_std: float
    spread_min: float
    spread_max: float
    spread_skewness: float
    spread_kurtosis: float
    spread_current: float

    # Z-score analysis
    zscore_current: float
    zscore_mean: float
    zscore_std: float
    zscore_entry_threshold: float
    zscore_exit_threshold: float
    zscore_stop_loss: float

    # Trading quality metrics
    signal_quality_score: float
    sharpe_ratio: Optional[float]
    profit_factor: Optional[float]
    win_rate: Optional[float]
    max_drawdown_pct: Optional[float]
    avg_trade_duration_days: Optional[float]

    # Overall assessment
    overall_score: float
    cointegration_strength: str
    trading_suitability: str
    risk_level: str

    # Metadata
    data_quality_score: float
    computation_time_ms: int
    error_message: Optional[str] = None


class CointegrationService:
    """
    Performs comprehensive cointegration analysis on asset pairs.
    Includes multiple statistical tests and generates trading signals.
    """

    def __init__(self):
        self.logger = logger

    def test_pair(
        self,
        asset1_symbol: str,
        asset2_symbol: str,
        prices_df: pd.DataFrame,
        granularity: str = "daily",
        lookback_days: int = 252,
    ) -> CointegrationTestResult:
        """
        Run comprehensive cointegration tests on a pair of assets.

        Args:
            asset1_symbol: Symbol for first asset (dependent variable)
            asset2_symbol: Symbol for second asset (independent variable)
            prices_df: DataFrame with columns [date, asset1_price, asset2_price]
            granularity: Data granularity ('daily', '4h', 'hourly')
            lookback_days: Number of days to look back

        Returns:
            CointegrationTestResult with all test results
        """
        start_time = datetime.now()

        try:
            # Data validation and preparation
            df = self._prepare_data(prices_df, lookback_days)

            if len(df) < 30:
                raise ValueError(
                    f"Insufficient data: only {len(df)} points (need at least 30)"
                )

            asset1_prices = df["asset1_price"].values
            asset2_prices = df["asset2_price"].values

            # 1. Correlation Analysis
            correlation_results = self._compute_correlations(
                asset1_prices, asset2_prices
            )

            # 2. Linear Regression (for hedge ratio)
            regression_results = self._compute_regression(asset1_prices, asset2_prices)

            # 3. Compute spread
            spread = asset1_prices - (
                regression_results["beta"] * asset2_prices + regression_results["alpha"]
            )
            spread_stats = self._compute_spread_statistics(spread)

            # 4. Engle-Granger Cointegration Test
            eg_results = self._engle_granger_test(asset1_prices, asset2_prices)

            # 5. Johansen Cointegration Test
            johansen_results = self._johansen_test(asset1_prices, asset2_prices)

            # 6. ADF Test on Residuals
            adf_results = self._adf_test(spread)

            # 7. Phillips-Perron Test
            pp_results = self._phillips_perron_test(spread)

            # 8. KPSS Test
            kpss_results = self._kpss_test(spread)

            # 9. Mean Reversion Characteristics
            mean_reversion = self._compute_mean_reversion_metrics(spread)

            # 10. Z-Score Analysis
            zscore_analysis = self._compute_zscore_analysis(spread)

            # 11. Signal Quality and Trading Metrics
            signal_quality = self._compute_signal_quality(
                spread, zscore_analysis["zscore_series"], mean_reversion["half_life"]
            )

            # 12. Data Quality Score
            data_quality = self._assess_data_quality(df)

            # 13. Overall Assessment
            overall_assessment = self._compute_overall_assessment(
                eg_results,
                johansen_results,
                adf_results,
                correlation_results,
                mean_reversion,
                signal_quality,
            )

            computation_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Build result object
            result = CointegrationTestResult(
                asset1_symbol=asset1_symbol,
                asset2_symbol=asset2_symbol,
                test_date=datetime.now().strftime("%Y-%m-%d"),
                granularity=granularity,
                lookback_days=lookback_days,
                sample_size=len(df),
                # Correlation
                pearson_correlation=correlation_results["pearson"],
                spearman_correlation=correlation_results["spearman"],
                kendall_tau=correlation_results["kendall"],
                correlation_pvalue=correlation_results["pvalue"],
                correlation_significance=correlation_results["significance"],
                # Engle-Granger
                eg_test_statistic=eg_results["test_stat"],
                eg_pvalue=eg_results["pvalue"],
                eg_critical_value_1pct=eg_results["crit_1pct"],
                eg_critical_value_5pct=eg_results["crit_5pct"],
                eg_critical_value_10pct=eg_results["crit_10pct"],
                eg_is_cointegrated=eg_results["is_cointegrated"],
                eg_significance_level=eg_results["significance_level"],
                # Johansen
                johansen_trace_stat=johansen_results["trace_stat"],
                johansen_trace_crit_90=johansen_results["trace_crit_90"],
                johansen_trace_crit_95=johansen_results["trace_crit_95"],
                johansen_trace_crit_99=johansen_results["trace_crit_99"],
                johansen_eigen_stat=johansen_results["eigen_stat"],
                johansen_eigen_crit_90=johansen_results["eigen_crit_90"],
                johansen_eigen_crit_95=johansen_results["eigen_crit_95"],
                johansen_eigen_crit_99=johansen_results["eigen_crit_99"],
                johansen_rank=johansen_results["rank"],
                johansen_is_cointegrated=johansen_results["is_cointegrated"],
                # ADF
                adf_test_statistic=adf_results["test_stat"],
                adf_pvalue=adf_results["pvalue"],
                adf_critical_value_1pct=adf_results["crit_1pct"],
                adf_critical_value_5pct=adf_results["crit_5pct"],
                adf_critical_value_10pct=adf_results["crit_10pct"],
                adf_used_lag=adf_results["used_lag"],
                adf_is_stationary=adf_results["is_stationary"],
                # Phillips-Perron
                pp_test_statistic=pp_results.get("test_stat"),
                pp_pvalue=pp_results.get("pvalue"),
                pp_critical_value_1pct=pp_results.get("crit_1pct"),
                pp_critical_value_5pct=pp_results.get("crit_5pct"),
                pp_critical_value_10pct=pp_results.get("crit_10pct"),
                pp_is_stationary=pp_results.get("is_stationary"),
                # KPSS
                kpss_test_statistic=kpss_results["test_stat"],
                kpss_pvalue=kpss_results["pvalue"],
                kpss_critical_value_1pct=kpss_results["crit_1pct"],
                kpss_critical_value_5pct=kpss_results["crit_5pct"],
                kpss_critical_value_10pct=kpss_results["crit_10pct"],
                kpss_is_stationary=kpss_results["is_stationary"],
                # Regression
                beta_coefficient=regression_results["beta"],
                alpha_intercept=regression_results["alpha"],
                regression_r_squared=regression_results["r_squared"],
                regression_adj_r_squared=regression_results["adj_r_squared"],
                regression_f_statistic=regression_results["f_statistic"],
                regression_f_pvalue=regression_results["f_pvalue"],
                regression_std_error=regression_results["std_error"],
                regression_durbin_watson=regression_results["durbin_watson"],
                # Mean reversion
                half_life_days=mean_reversion["half_life"],
                mean_reversion_speed=mean_reversion["speed"],
                hurst_exponent=mean_reversion["hurst"],
                # Spread stats
                spread_mean=spread_stats["mean"],
                spread_std=spread_stats["std"],
                spread_min=spread_stats["min"],
                spread_max=spread_stats["max"],
                spread_skewness=spread_stats["skewness"],
                spread_kurtosis=spread_stats["kurtosis"],
                spread_current=spread_stats["current"],
                # Z-score
                zscore_current=zscore_analysis["current"],
                zscore_mean=zscore_analysis["mean"],
                zscore_std=zscore_analysis["std"],
                zscore_entry_threshold=2.0,
                zscore_exit_threshold=0.5,
                zscore_stop_loss=3.0,
                # Trading quality
                signal_quality_score=signal_quality["quality_score"],
                sharpe_ratio=signal_quality.get("sharpe_ratio"),
                profit_factor=signal_quality.get("profit_factor"),
                win_rate=signal_quality.get("win_rate"),
                max_drawdown_pct=signal_quality.get("max_drawdown_pct"),
                avg_trade_duration_days=signal_quality.get("avg_duration"),
                # Overall
                overall_score=overall_assessment["score"],
                cointegration_strength=overall_assessment["strength"],
                trading_suitability=overall_assessment["suitability"],
                risk_level=overall_assessment["risk_level"],
                # Metadata
                data_quality_score=data_quality,
                computation_time_ms=computation_time,
                error_message=None,
            )

            return result

        except Exception as e:
            self.logger.error(
                f"Error testing pair {asset1_symbol}/{asset2_symbol}: {str(e)}"
            )
            computation_time = int((datetime.now() - start_time).total_seconds() * 1000)

            # Return minimal result with error
            return self._create_error_result(
                asset1_symbol,
                asset2_symbol,
                granularity,
                lookback_days,
                computation_time,
                str(e),
            )

    def _prepare_data(self, df: pd.DataFrame, lookback_days: int) -> pd.DataFrame:
        """Validate and prepare price data"""
        # Ensure required columns
        required_cols = ["date", "asset1_price", "asset2_price"]
        if not all(col in df.columns for col in required_cols):
            raise ValueError(f"DataFrame must have columns: {required_cols}")

        # Sort by date
        df = df.sort_values("date").reset_index(drop=True)

        # Remove NaN values
        df = df.dropna(subset=["asset1_price", "asset2_price"])

        # Limit to lookback period
        if len(df) > lookback_days:
            df = df.tail(lookback_days)

        return df

    def _compute_correlations(self, x: np.ndarray, y: np.ndarray) -> Dict[str, Any]:
        """Compute Pearson, Spearman, and Kendall correlations"""
        pearson_corr, pearson_pval = stats.pearsonr(x, y)
        spearman_corr, _ = stats.spearmanr(x, y)
        kendall_corr, _ = stats.kendalltau(x, y)

        # Determine significance
        if pearson_pval < 0.01:
            significance = "highly_significant"
        elif pearson_pval < 0.05:
            significance = "significant"
        else:
            significance = "not_significant"

        return {
            "pearson": float(pearson_corr),
            "spearman": float(spearman_corr),
            "kendall": float(kendall_corr),
            "pvalue": float(pearson_pval),
            "significance": significance,
        }

    def _compute_regression(self, y: np.ndarray, x: np.ndarray) -> Dict[str, Any]:
        """Perform linear regression Y = alpha + beta*X"""
        from statsmodels.api import OLS, add_constant
        from statsmodels.stats.stattools import durbin_watson

        X = add_constant(x)
        model = OLS(y, X).fit()

        return {
            "alpha": float(model.params[0]),
            "beta": float(model.params[1]),
            "r_squared": float(model.rsquared),
            "adj_r_squared": float(model.rsquared_adj),
            "f_statistic": float(model.fvalue),
            "f_pvalue": float(model.f_pvalue),
            "std_error": float(np.std(model.resid)),
            "durbin_watson": float(durbin_watson(model.resid)),
        }

    def _compute_spread_statistics(self, spread: np.ndarray) -> Dict[str, Any]:
        """Compute descriptive statistics for spread"""
        return {
            "mean": float(np.mean(spread)),
            "std": float(np.std(spread, ddof=1)),  # Use ddof=1 for sample standard deviation
            "min": float(np.min(spread)),
            "max": float(np.max(spread)),
            "skewness": float(stats.skew(spread)),
            "kurtosis": float(stats.kurtosis(spread)),
            "current": float(spread[-1]),
        }

    def _engle_granger_test(self, y: np.ndarray, x: np.ndarray) -> Dict[str, Any]:
        """Engle-Granger two-step cointegration test"""
        test_stat, pvalue, crit_values = coint(y, x)

        # Determine significance level
        if test_stat < crit_values[0]:
            significance = "1%"
            is_cointegrated = True
        elif test_stat < crit_values[1]:
            significance = "5%"
            is_cointegrated = True
        elif test_stat < crit_values[2]:
            significance = "10%"
            is_cointegrated = True
        else:
            significance = "not_significant"
            is_cointegrated = False

        return {
            "test_stat": float(test_stat),
            "pvalue": float(pvalue),
            "crit_1pct": float(crit_values[0]),
            "crit_5pct": float(crit_values[1]),
            "crit_10pct": float(crit_values[2]),
            "is_cointegrated": is_cointegrated,
            "significance_level": significance,
        }

    def _johansen_test(self, y: np.ndarray, x: np.ndarray) -> Dict:
        """
        Johansen cointegration test - determines cointegration rank.

        Returns trace and max eigenvalue statistics with their critical values.
        The cointegration rank is determined by comparing statistics to critical values.
        """
        # Prepare data for Johansen test
        data = np.column_stack([y, x])

        try:
            result = coint_johansen(data, det_order=0, k_ar_diff=1)

            # Determine cointegration rank using trace statistic (90%, 95%, 99% confidence)
            # We test sequentially: r=0, r<=1, etc.
            # Stop when we cannot reject the null hypothesis at 95% level
            rank = 0
            for i in range(len(result.trace_stat)):
                if (
                    result.trace_stat[i] > result.trace_stat_crit_vals[i, 1]
                ):  # 5% crit val
                    rank = i + 1  # At least i+1 cointegrating relationships
                else:
                    break

            # Get first (most important) statistics for pair analysis
            trace_stat = result.trace_stat[0]
            trace_crit_90 = result.trace_stat_crit_vals[0, 0]
            trace_crit_95 = result.trace_stat_crit_vals[0, 1]
            trace_crit_99 = result.trace_stat_crit_vals[0, 2]

            eigen_stat = result.max_eig_stat[0]
            eigen_crit_90 = result.max_eig_stat_crit_vals[0, 0]
            eigen_crit_95 = result.max_eig_stat_crit_vals[0, 1]
            eigen_crit_99 = result.max_eig_stat_crit_vals[0, 2]

            return {
                # Trace statistic (tests H0: rank <= r)
                "trace_stat": float(trace_stat),
                "trace_crit_90": float(trace_crit_90),
                "trace_crit_95": float(trace_crit_95),
                "trace_crit_99": float(trace_crit_99),
                # Max eigenvalue statistic (tests H0: rank = r)
                "eigen_stat": float(eigen_stat),
                "eigen_crit_90": float(eigen_crit_90),
                "eigen_crit_95": float(eigen_crit_95),
                "eigen_crit_99": float(eigen_crit_99),
                # Cointegration rank (most important result)
                "rank": int(rank),
                "is_cointegrated": rank > 0,
            }
        except Exception as e:
            self.logger.warning(f"Johansen test failed: {str(e)}")
            return {
                "trace_stat": 0.0,
                "trace_crit_90": 0.0,
                "trace_crit_95": 0.0,
                "trace_crit_99": 0.0,
                "eigen_stat": 0.0,
                "eigen_crit_90": 0.0,
                "eigen_crit_95": 0.0,
                "eigen_crit_99": 0.0,
                "rank": 0,
                "is_cointegrated": False,
            }

    def _adf_test(self, series: np.ndarray) -> Dict:
        """Augmented Dickey-Fuller test for stationarity"""
        result = adfuller(series, autolag="AIC")

        test_stat = result[0]
        pvalue = result[1]
        used_lag = result[2]
        crit_values = result[4]

        is_stationary = pvalue < 0.05

        return {
            "test_stat": float(test_stat),
            "pvalue": float(pvalue),
            "used_lag": int(used_lag),
            "crit_1pct": float(crit_values["1%"]),
            "crit_5pct": float(crit_values["5%"]),
            "crit_10pct": float(crit_values["10%"]),
            "is_stationary": is_stationary,
        }

    def _phillips_perron_test(self, series: np.ndarray) -> Dict:
        """
        Phillips-Perron test for unit root (non-stationarity).

        Uses arch.unitroot.PhillipsPerron which handles serial correlation
        and heteroskedasticity non-parametrically using Newey-West estimator.
        """
        try:
            from arch.unitroot import PhillipsPerron

            pp_test = PhillipsPerron(series, lags=None, trend="c", test_type="tau")

            return {
                "test_stat": float(pp_test.stat),
                "pvalue": float(pp_test.pvalue),
                "crit_1pct": float(pp_test.critical_values["1%"]),
                "crit_5pct": float(pp_test.critical_values["5%"]),
                "crit_10pct": float(pp_test.critical_values["10%"]),
                "is_stationary": pp_test.pvalue < 0.05,
            }
        except Exception as e:
            logger.error(f"Phillips-Perron test failed: {e}")
            return {}

    def _kpss_test(self, series: np.ndarray) -> Dict:
        """KPSS test for stationarity (null hypothesis: series is stationary)"""
        test_stat, pvalue, lags, crit_values = kpss(
            series, regression="c", nlags="auto"
        )

        # For KPSS, we want to NOT reject null (series is stationary)
        is_stationary = pvalue > 0.05

        return {
            "test_stat": float(test_stat),
            "pvalue": float(pvalue),
            "crit_1pct": float(crit_values["1%"]),
            "crit_5pct": float(crit_values["5%"]),
            "crit_10pct": float(crit_values["10%"]),
            "is_stationary": is_stationary,
        }

    def _compute_mean_reversion_metrics(self, spread: np.ndarray) -> Dict:
        """Compute mean reversion characteristics"""
        # Half-life using Ornstein-Uhlenbeck process
        spread_lag = spread[:-1]
        spread_diff = np.diff(spread)

        # Fit AR(1) model: spread_t - spread_{t-1} = lambda * (mu - spread_{t-1}) + epsilon
        from sklearn.linear_model import LinearRegression

        model = LinearRegression()
        model.fit(spread_lag.reshape(-1, 1), spread_diff)

        lambda_param = -model.coef_[0]
        # Correct half-life calculation: hl = ln(2) / lambda, with explicit handling for non-mean-reverting (lambda <= 0)
        if not np.isfinite(lambda_param) or lambda_param <= 0:
            half_life = float("inf")
            speed = 0.0
        else:
            half_life = float(np.log(2) / float(lambda_param))
            speed = float(lambda_param)

        # Hurst exponent
        hurst = self._compute_hurst_exponent(spread)

        return {
            "half_life": float(half_life),
            "speed": float(speed),
            "hurst": float(hurst),
        }

    def _compute_hurst_exponent(self, series: np.ndarray) -> float:
        """Compute Hurst exponent using R/S analysis"""
        """H<0.5=mean-reverting, H=0.5=random walk, H>0.5=trending"""
        lags = range(2, min(100, len(series) // 2))
        tau = []

        for lag in lags:
            # Calculate standard deviation for this lag
            std = np.std(series[lag:] - series[:-lag])
            tau.append(std)

        # Fit log(tau) vs log(lag)
        try:
            poly = np.polyfit(np.log(lags), np.log(tau), 1)
            hurst = poly[0]
            return max(0.0, min(1.0, hurst))  # Clamp to [0, 1]
        except Exception:
            return 0.5  # Default to random walk

    def _compute_zscore_analysis(self, spread: np.ndarray) -> Dict:
        """Compute z-score statistics"""
        # Use ddof=1 for sample standard deviation (Bessel's correction)
        # This is more appropriate for financial time series analysis
        zscore = (spread - np.mean(spread)) / np.std(spread, ddof=1)

        return {
            "current": float(zscore[-1]),
            "mean": float(np.mean(zscore)),
            "std": float(np.std(zscore, ddof=1)),  # Also use ddof=1 for consistency
            "zscore_series": zscore,
        }

    def _compute_signal_quality(
        self, spread: np.ndarray, zscore: np.ndarray, half_life: float
    ) -> Dict:
        """Compute trading signal quality metrics"""
        # Simulate trading signals based on z-score thresholds
        entry_threshold = 2.0
        exit_threshold = 0.5

        signals = []
        positions = []  # 1 = long, -1 = short, 0 = flat
        current_pos = 0
        entry_price = 0

        for i, z in enumerate(zscore):
            if current_pos == 0:
                # Enter position when z-score exceeds threshold
                if z > entry_threshold:
                    current_pos = -1  # Short spread (bet on convergence)
                    entry_price = spread[i]
                    signals.append(
                        {"entry": i, "type": "short", "entry_price": entry_price}
                    )
                elif z < -entry_threshold:
                    current_pos = 1  # Long spread (bet on convergence)
                    entry_price = spread[i]
                    signals.append(
                        {"entry": i, "type": "long", "entry_price": entry_price}
                    )
            else:
                # Exit position when z-score returns to normal range
                if abs(z) < exit_threshold:
                    exit_price = spread[i]
                    pnl = current_pos * (exit_price - entry_price)  # Calculate profit/loss
                    signals[-1]["exit"] = i
                    signals[-1]["exit_price"] = exit_price
                    signals[-1]["pnl"] = pnl
                    current_pos = 0  # Close position

            positions.append(current_pos)

        # Calculate metrics
        completed_trades = [s for s in signals if "pnl" in s]

        if len(completed_trades) > 0:
            pnls = [t["pnl"] for t in completed_trades]
            winning_trades = [p for p in pnls if p > 0]

            # Sharpe ratio (annualized)
            if np.std(pnls) > 0:
                sharpe = np.mean(pnls) / np.std(pnls) * np.sqrt(252)
            else:
                sharpe = 0.0

            # Profit factor
            gross_profit = sum(winning_trades) if winning_trades else 0
            gross_loss = abs(sum([p for p in pnls if p < 0]))
            profit_factor = gross_profit / gross_loss if gross_loss > 0 else None

            # Win rate
            win_rate = len(winning_trades) / len(completed_trades) * 100

            # Max drawdown
            cumulative_pnl = np.cumsum(pnls)
            running_max = np.maximum.accumulate(cumulative_pnl)
            drawdown = running_max - cumulative_pnl
            max_drawdown_pct = (
                (np.max(drawdown) / np.max(running_max) * 100)
                if np.max(running_max) > 0
                else 0
            )

            # Average trade duration
            durations = [t["exit"] - t["entry"] for t in completed_trades]
            avg_duration = np.mean(durations) if durations else None

            # Quality score (0-100)
            # Components: win rate (up to 50), Sharpe ratio (up to 30), mean reversion (up to 20)
            # Mean-reversion contribution should be 0 when half-life is not finite (no mean reversion)
            mr_points = 0
            if np.isfinite(half_life):
                if half_life < 20:
                    mr_points = 20  # Strong mean reversion
                elif half_life < 60:
                    mr_points = 10  # Moderate mean reversion

            quality_score = (
                min(50, win_rate)  # Max 50 points for win rate
                + min(30, sharpe * 10)  # Max 30 points for Sharpe (scaled)
                + mr_points  # Mean reversion bonus
            )

            return {
                "quality_score": float(min(100, max(0, quality_score))),
                "sharpe_ratio": float(sharpe),
                "profit_factor": float(profit_factor) if profit_factor else None,
                "win_rate": float(win_rate),
                "max_drawdown_pct": float(max_drawdown_pct),
                "avg_duration": float(avg_duration) if avg_duration else None,
            }
        else:
            return {
                "quality_score": 0.0,
                "sharpe_ratio": None,
                "profit_factor": None,
                "win_rate": None,
                "max_drawdown_pct": None,
                "avg_duration": None,
            }

    def _assess_data_quality(self, df: pd.DataFrame) -> float:
        """Assess data quality (0-100 score)"""
        score = 100.0

        # Penalize for missing data
        missing_pct = df.isnull().sum().sum() / (len(df) * len(df.columns)) * 100
        score -= missing_pct * 2

        # Penalize for insufficient data
        if len(df) < 252:
            score -= (252 - len(df)) / 252 * 20

        # Penalize for zero or negative prices
        if (df["asset1_price"] <= 0).any() or (df["asset2_price"] <= 0).any():
            score -= 10

        return max(0.0, min(100.0, score))

    def _compute_overall_assessment(
        self,
        eg_results: Dict,
        johansen_results: Dict,
        adf_results: Dict,
        correlation_results: Dict,
        mean_reversion: Dict,
        signal_quality: Dict,
    ) -> Dict:
        """Compute overall cointegration score and assessment"""
        score = 0.0

        # Engle-Granger test (30 points)
        if eg_results["is_cointegrated"]:
            if eg_results["significance_level"] == "1%":
                score += 30
            elif eg_results["significance_level"] == "5%":
                score += 25
            elif eg_results["significance_level"] == "10%":
                score += 20

        # Johansen test (20 points)
        if johansen_results["is_cointegrated"]:
            score += 20

        # ADF stationarity (15 points)
        if adf_results["is_stationary"]:
            score += 15

        # Correlation strength (15 points)
        corr = abs(correlation_results["pearson"])
        if corr > 0.8:
            score += 15
        elif corr > 0.6:
            score += 10
        elif corr > 0.4:
            score += 5

        # Mean reversion (up to 10 points)
        half_life = mean_reversion["half_life"]
        hurst = mean_reversion["hurst"]
        if hurst < 0.5 and np.isfinite(half_life):
            if half_life < 20:
                score += 10
            else:
                score += 5

        # Signal quality (10 points)
        score += signal_quality["quality_score"] * 0.1

        # Determine strength
        if score >= 80:
            strength = "strong"
        elif score >= 60:
            strength = "moderate"
        elif score >= 40:
            strength = "weak"
        else:
            strength = "none"

        # Trading suitability
        if score >= 75 and signal_quality["quality_score"] > 60:
            suitability = "excellent"
        elif score >= 60 and signal_quality["quality_score"] > 40:
            suitability = "good"
        elif score >= 40:
            suitability = "fair"
        else:
            suitability = "poor"

        # Risk level (non-mean-reverting => high risk)
        if not np.isfinite(half_life):
            risk_level = "high"
        elif half_life < 10 and hurst < 0.4:
            risk_level = "low"
        elif half_life < 20 and hurst < 0.5:
            risk_level = "medium"
        else:
            risk_level = "high"

        return {
            "score": float(min(100, max(0, score))),
            "strength": strength,
            "suitability": suitability,
            "risk_level": risk_level,
        }

    def _create_error_result(
        self,
        asset1: str,
        asset2: str,
        granularity: str,
        lookback_days: int,
        computation_time: int,
        error: str,
    ) -> CointegrationTestResult:
        """Create a minimal result object for failed tests"""
        return CointegrationTestResult(
            asset1_symbol=asset1,
            asset2_symbol=asset2,
            test_date=datetime.now().strftime("%Y-%m-%d"),
            granularity=granularity,
            lookback_days=lookback_days,
            sample_size=0,
            # Set all metrics to None/0
            pearson_correlation=0.0,
            spearman_correlation=0.0,
            kendall_tau=0.0,
            correlation_pvalue=1.0,
            correlation_significance="not_significant",
            eg_test_statistic=0.0,
            eg_pvalue=1.0,
            eg_critical_value_1pct=-3.90,
            eg_critical_value_5pct=-3.34,
            eg_critical_value_10pct=-3.04,
            eg_is_cointegrated=False,
            eg_significance_level="not_significant",
            johansen_trace_stat=0.0,
            johansen_trace_crit_90=0.0,
            johansen_trace_crit_95=0.0,
            johansen_trace_crit_99=0.0,
            johansen_eigen_stat=0.0,
            johansen_eigen_crit_90=0.0,
            johansen_eigen_crit_95=0.0,
            johansen_eigen_crit_99=0.0,
            johansen_rank=0,
            johansen_is_cointegrated=False,
            adf_test_statistic=0.0,
            adf_pvalue=1.0,
            adf_critical_value_1pct=0.0,
            adf_critical_value_5pct=0.0,
            adf_critical_value_10pct=0.0,
            adf_used_lag=0,
            adf_is_stationary=False,
            pp_test_statistic=None,
            pp_pvalue=None,
            pp_critical_value_1pct=None,
            pp_critical_value_5pct=None,
            pp_critical_value_10pct=None,
            pp_is_stationary=None,
            kpss_test_statistic=0.0,
            kpss_pvalue=1.0,
            kpss_critical_value_1pct=0.0,
            kpss_critical_value_5pct=0.0,
            kpss_critical_value_10pct=0.0,
            kpss_is_stationary=False,
            beta_coefficient=0.0,
            alpha_intercept=0.0,
            regression_r_squared=0.0,
            regression_adj_r_squared=0.0,
            regression_f_statistic=0.0,
            regression_f_pvalue=1.0,
            regression_std_error=0.0,
            regression_durbin_watson=2.0,
            half_life_days=999.0,
            mean_reversion_speed=0.0,
            hurst_exponent=0.5,
            spread_mean=0.0,
            spread_std=0.0,
            spread_min=0.0,
            spread_max=0.0,
            spread_skewness=0.0,
            spread_kurtosis=0.0,
            spread_current=0.0,
            zscore_current=0.0,
            zscore_mean=0.0,
            zscore_std=0.0,
            zscore_entry_threshold=2.0,
            zscore_exit_threshold=0.5,
            zscore_stop_loss=3.0,
            signal_quality_score=0.0,
            sharpe_ratio=None,
            profit_factor=None,
            win_rate=None,
            max_drawdown_pct=None,
            avg_trade_duration_days=None,
            overall_score=0.0,
            cointegration_strength="none",
            trading_suitability="poor",
            risk_level="high",
            data_quality_score=0.0,
            computation_time_ms=computation_time,
            error_message=error,
        )

    # ============================================================================
    # PAIR TRADING UTILITY FUNCTIONS
    # Merged from pair_analysis_service.py for complete consolidation
    # ============================================================================

    def resolve_asset_symbol(self, asset_input: str) -> str:
        """
        Resolve asset input to symbol format.
        Accepts either display name (e.g., 'Apple') or symbol (e.g., 'AAPL.US').
        Returns the symbol format.
        """
        from api.utils.assets import name_to_symbol
        
        # Check if input is already a symbol (contains a dot like 'AAPL.US')
        if "." in asset_input:
            return asset_input
        # Check if it's already in symbol format (in name_to_symbol values)
        if asset_input in name_to_symbol.values():
            return asset_input
        # Otherwise, look it up as a display name
        return name_to_symbol.get(asset_input, asset_input)

    def calculate_hedge_ratio(
        self, asset1_prices: np.ndarray, asset2_prices: np.ndarray
    ) -> float:
        """
        Calculate the hedge ratio between two assets using OLS regression.
        
        The hedge ratio represents how many units of asset2 to short for each
        unit of asset1 held long to create a market-neutral position.
        
        Args:
            asset1_prices: Price array for the first asset (dependent variable)
            asset2_prices: Price array for the second asset (independent variable)
            
        Returns:
            Hedge ratio (beta coefficient from regression)
        """
        from statsmodels.api import OLS, add_constant

        X = add_constant(asset2_prices)
        model = OLS(asset1_prices, X).fit()
        return float(model.params[1])  # Return beta coefficient

    def calculate_spread(
        self,
        asset1_prices: np.ndarray,
        asset2_prices: np.ndarray,
        hedge_ratio: Optional[float] = None,
        intercept: Optional[float] = None,
    ) -> np.ndarray:
        """
        Calculate the spread between two assets.
        
        Spread = asset1_prices - (hedge_ratio * asset2_prices + intercept)
        
        For cointegration analysis, the spread should be the residual from the
        full regression model including both beta (hedge_ratio) and alpha (intercept).
        
        Args:
            asset1_prices: Price array for the first asset
            asset2_prices: Price array for the second asset
            hedge_ratio: Hedge ratio (beta) to use. If None, calculated automatically.
            intercept: Regression intercept (alpha) to use. If None, calculated automatically.
            
        Returns:
            Array representing the spread (residuals)
        """
        if hedge_ratio is None or intercept is None:
            # Calculate both beta and alpha from regression
            from statsmodels.api import OLS, add_constant
            
            X = add_constant(asset2_prices)
            model = OLS(asset1_prices, X).fit()
            hedge_ratio = float(model.params[1])
            intercept = float(model.params[0])

        spread = asset1_prices - (hedge_ratio * asset2_prices + intercept)
        return spread

    def calculate_zscore(
        self, series: np.ndarray, window: Optional[int] = None
    ) -> np.ndarray:
        """
        Calculate the z-score of a series.
        
        Z-score = (value - mean) / std_dev
        
        Args:
            series: Input series (typically a spread)
            window: Rolling window size. If None, uses full series statistics.
            
        Returns:
            Array of z-scores
        """
        import pandas as pd

        if window is None:
            # Use full series statistics
            mean = np.mean(series)
            std = np.std(series)
            return (series - mean) / std
        else:
            # Use rolling statistics
            series_pd = pd.Series(series)
            rolling_mean = series_pd.rolling(window).mean().values
            rolling_std = series_pd.rolling(window).std().values
            return (series - rolling_mean) / rolling_std
