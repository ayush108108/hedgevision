import React from "react";
import {
  GitCompare,
  Activity,
  BarChart3,
  LineChart,
  TrendingUp,
  Repeat,
  BarChart2,
  Zap,
  Award,
  Target,
  Maximize2,
  ChevronDown,
  CheckCircle2,
  XCircle,
  AlertCircle,
  TrendingDown,
} from "lucide-react";
import { TestPairResponse, CointegrationTestResult } from "../../services/cointegrationApi";

interface PairTestResultsProps {
  testResult: Partial<CointegrationTestResult & TestPairResponse>;
  selectedCategory?: TestCategory;
}

type TestCategory =
  | "correlation"
  | "engle-granger"
  | "johansen"
  | "adf"
  | "phillips-perron"
  | "kpss"
  | "regression"
  | "mean-reversion"
  | "spread-stats"
  | "zscore"
  | "trading-quality"
  | "overall";

const TEST_CATEGORIES = [
  {
    value: "overall",
    label: "Overall Assessment",
    icon: Target,
    color: "blue",
    description: "Composite score and trading suitability",
  },
  {
    value: "correlation",
    label: "Correlation Metrics",
    icon: GitCompare,
    color: "cyan",
    description: "Pearson, Spearman, and Kendall correlations",
  },
  {
    value: "engle-granger",
    label: "Engle-Granger Test",
    icon: Activity,
    color: "green",
    description: "Primary cointegration test with residual stationarity",
  },
  {
    value: "johansen",
    label: "Johansen Test",
    icon: BarChart3,
    color: "purple",
    description: "Multivariate cointegration with trace & eigen statistics",
  },
  {
    value: "adf",
    label: "ADF Test",
    icon: LineChart,
    color: "indigo",
    description: "Augmented Dickey-Fuller stationarity test",
  },
  {
    value: "phillips-perron",
    label: "Phillips-Perron Test",
    icon: TrendingUp,
    color: "pink",
    description: "Non-parametric stationarity test with Newey-West correction",
  },
  {
    value: "kpss",
    label: "KPSS Test",
    icon: Activity,
    color: "orange",
    description: "Kwiatkowski-Phillips-Schmidt-Shin stationarity test",
  },
  {
    value: "regression",
    label: "Linear Regression",
    icon: Maximize2,
    color: "emerald",
    description: "OLS regression with beta coefficient and R²",
  },
  {
    value: "mean-reversion",
    label: "Mean Reversion",
    icon: Repeat,
    color: "teal",
    description: "Half-life, Hurst exponent, and mean reversion speed",
  },
  {
    value: "spread-stats",
    label: "Spread Statistics",
    icon: BarChart2,
    color: "violet",
    description: "Spread mean, std, volatility, and distribution",
  },
  {
    value: "zscore",
    label: "Z-Score Analysis",
    icon: Zap,
    color: "yellow",
    description: "Current z-score with entry/exit thresholds",
  },
  {
    value: "trading-quality",
    label: "Trading Quality",
    icon: Award,
    color: "rose",
    description: "Sharpe ratio, win rate, and execution metrics",
  },
];

export function PairTestResults({ testResult, selectedCategory = "overall" }: PairTestResultsProps) {

  const getStatusIcon = (isPass: boolean, condition?: boolean) => {
    if (condition === undefined)
      return <AlertCircle className="w-5 h-5 text-gray-400" />;
    if (isPass) return <CheckCircle2 className="w-5 h-5 text-green-400" />;
    return <XCircle className="w-5 h-5 text-red-400" />;
  };

  const getStatusColor = (isPass: boolean) => {
    return isPass
      ? "bg-green-500/20 border-green-500/30 text-green-300"
      : "bg-red-500/20 border-red-500/30 text-red-300";
  };

  const renderCategoryContent = () => {
    switch (selectedCategory) {
      case "overall":
        return (
          <div className="space-y-6">
            {/* Score Circle */}
            <div className="flex items-center justify-center">
              <div className="relative">
                <svg className="w-48 h-48 -rotate-90">
                  <circle
                    cx="96"
                    cy="96"
                    r="88"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="8"
                    className="text-white/10"
                  />
                  <circle
                    cx="96"
                    cy="96"
                    r="88"
                    fill="none"
                    stroke="currentColor"
                    strokeWidth="8"
                    strokeLinecap="round"
                    strokeDasharray={`${((testResult.overall_score ?? 0) / 100) * 553} 553`}
                    className={`${
                      (testResult.overall_score ?? 0) >= 80
                        ? "text-green-400"
                        : (testResult.overall_score ?? 0) >= 70
                          ? "text-blue-400"
                          : (testResult.overall_score ?? 0) >= 60
                            ? "text-yellow-400"
                            : "text-red-400"
                    } transition-all duration-1000`}
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <div className="text-5xl font-bold text-white">
                    {Math.round(testResult.overall_score ?? 0)}
                  </div>
                  <div className="text-sm text-gray-400 mt-1">
                    Overall Score
                  </div>
                </div>
              </div>
            </div>

            {/* Summary Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div
                className={`p-4 rounded-xl border ${
                  testResult.eg_is_cointegrated
                    ? "bg-green-500/10 border-green-500/30"
                    : "bg-red-500/10 border-red-500/30"
                }`}
              >
                <div className="flex items-center gap-2 mb-2">
                  {getStatusIcon(
                    testResult.eg_is_cointegrated ?? false,
                    testResult.eg_is_cointegrated ?? false,
                  )}
                  <span className="font-medium text-white">Cointegration</span>
                </div>
                <div
                  className={`text-sm ${testResult.eg_is_cointegrated ? "text-green-300" : "text-red-300"}`}
                >
                  {testResult.eg_is_cointegrated ? "Confirmed" : "Not Detected"}
                </div>
              </div>

              <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/30">
                <div className="flex items-center gap-2 mb-2">
                  <Award className="w-5 h-5 text-blue-400" />
                  <span className="font-medium text-white">Strength</span>
                </div>
                <div className="text-sm text-blue-300 capitalize">
                  {testResult.cointegration_strength?.replace("_", " ")}
                </div>
              </div>

              <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/30">
                <div className="flex items-center gap-2 mb-2">
                  <Target className="w-5 h-5 text-purple-400" />
                  <span className="font-medium text-white">Suitability</span>
                </div>
                <div className="text-sm text-purple-300 capitalize">
                  {testResult.trading_suitability}
                </div>
              </div>
            </div>

            {/* Key Metrics */}
            <div className="p-6 rounded-xl bg-white/5 border border-white/10 space-y-4">
              <h3 className="text-lg font-semibold text-white mb-4">
                Key Metrics
              </h3>
              <div className="grid grid-cols-2 gap-4">
                <MetricRow
                  label="P-Value"
                  value={testResult.eg_pvalue?.toFixed(4) || "N/A"}
                />
                <MetricRow
                  label="Beta"
                  value={testResult.beta_coefficient?.toFixed(4) || "N/A"}
                />
                <MetricRow
                  label="Half-Life"
                  value={testResult.half_life_days ? `${testResult.half_life_days.toFixed(1)} days` : "N/A"}
                />
                {testResult.sharpe_ratio !== null && testResult.sharpe_ratio !== undefined && (
                  <MetricRow
                    label="Sharpe Ratio"
                    value={testResult.sharpe_ratio.toFixed(2)}
                  />
                )}
                <MetricRow
                  label="Sample Size"
                  value={testResult.sample_size?.toString() || "N/A"}
                />
                <MetricRow
                  label="Lookback"
                  value={testResult.lookback_days ? `${testResult.lookback_days} days` : "N/A"}
                />
              </div>
            </div>
          </div>
        );

      case "correlation":
        return (
          <div className="space-y-6">
            <div className="p-6 rounded-xl bg-white/5 border border-white/10">
              <h3 className="text-lg font-semibold text-white mb-4">
                Correlation Coefficients
              </h3>
              <div className="space-y-3">
                <MetricRow
                  label="Pearson Correlation"
                  value={
                    testResult.pearson_correlation !== undefined && testResult.pearson_correlation !== null
                      ? testResult.pearson_correlation.toFixed(4)
                      : "N/A"
                  }
                  description="Linear correlation (-1 to 1)"
                />
                <MetricRow
                  label="Spearman Correlation"
                  value={
                    testResult.spearman_correlation !== undefined && testResult.spearman_correlation !== null
                      ? testResult.spearman_correlation.toFixed(4)
                      : "N/A"
                  }
                  description="Rank-based correlation"
                />
                <MetricRow
                  label="Kendall Tau"
                  value={
                    testResult.kendall_tau !== undefined && testResult.kendall_tau !== null
                      ? testResult.kendall_tau.toFixed(4)
                      : "N/A"
                  }
                  description="Concordance correlation"
                />
                {testResult.correlation_pvalue !== undefined && (
                  <MetricRow
                    label="Correlation P-Value"
                    value={
                      testResult.correlation_pvalue !== null
                        ? (testResult.correlation_pvalue as number).toFixed(4)
                        : "N/A"
                    }
                    description="Significance of correlation"
                  />
                )}
              </div>
            </div>
            <div className="p-4 rounded-xl bg-yellow-500/10 border border-yellow-500/30 text-yellow-300 text-sm">
              Note: Detailed correlation metrics available in full test results
            </div>
          </div>
        );

      case "engle-granger":
        return (
          <div className="space-y-6">
            <div
              className={`p-6 rounded-xl border ${
                testResult.eg_is_cointegrated
                  ? "bg-green-500/10 border-green-500/30"
                  : "bg-red-500/10 border-red-500/30"
              }`}
            >
              <div className="flex items-center gap-3 mb-4">
                {getStatusIcon(
                  testResult.eg_is_cointegrated ?? false,
                  testResult.eg_is_cointegrated ?? false,
                )}
                <h3 className="text-lg font-semibold text-white">
                  {testResult.eg_is_cointegrated
                    ? "Cointegrated"
                    : "Not Cointegrated"}
                </h3>
              </div>
              <div className="space-y-3">
                <MetricRow
                  label="P-Value"
                  value={testResult.eg_pvalue?.toFixed(4) || "N/A"}
                />
                <MetricRow
                  label="Test Statistic"
                  value={
                    testResult.eg_test_statistic !== undefined && testResult.eg_test_statistic !== null
                      ? testResult.eg_test_statistic.toFixed(4)
                      : "N/A"
                  }
                />
                <MetricRow
                  label="Critical Value (5%)"
                  value={
                    testResult.eg_critical_value_5pct !== undefined && testResult.eg_critical_value_5pct !== null
                      ? testResult.eg_critical_value_5pct.toFixed(4)
                      : "N/A"
                  }
                />
              </div>
            </div>
            <div className="p-4 rounded-xl bg-blue-500/10 border border-blue-500/30 text-blue-300 text-sm">
              <strong>Interpretation:</strong> P-value &lt; 0.05 indicates
              cointegration at 95% confidence level
            </div>
          </div>
        );

      case "johansen":
        return (
          <div className="space-y-6">
            <div className="p-6 rounded-xl bg-white/5 border border-white/10">
              <h3 className="text-lg font-semibold text-white mb-4">Johansen Test</h3>
              <div className="space-y-3">
                <MetricRow
                  label="Trace Statistic"
                  value={
                    testResult.johansen_trace_stat !== undefined && testResult.johansen_trace_stat !== null
                      ? testResult.johansen_trace_stat.toFixed(4)
                      : "N/A"
                  }
                />
                <MetricRow
                  label="Eigen Statistic"
                  value={
                    testResult.johansen_eigen_stat !== undefined && testResult.johansen_eigen_stat !== null
                      ? testResult.johansen_eigen_stat.toFixed(4)
                      : "N/A"
                  }
                />
                <MetricRow
                  label="Cointegration Rank"
                  value={
                    testResult.johansen_rank !== undefined && testResult.johansen_rank !== null
                      ? String(testResult.johansen_rank)
                      : "N/A"
                  }
                />
                <MetricRow
                  label="Is Cointegrated"
                  value={
                    testResult.johansen_is_cointegrated !== undefined
                      ? testResult.johansen_is_cointegrated
                        ? "Yes"
                        : "No"
                      : "N/A"
                  }
                />
              </div>
            </div>
          </div>
        );

      case "regression":
        return (
          <div className="space-y-6">
            <div className="p-6 rounded-xl bg-white/5 border border-white/10">
              <h3 className="text-lg font-semibold text-white mb-4">
                Linear Regression Results
              </h3>
              <div className="space-y-3">
                <MetricRow
                  label="Beta Coefficient"
                  value={testResult.beta_coefficient?.toFixed(4) || "N/A"}
                />
                <MetricRow
                  label="Alpha (Intercept)"
                  value={
                    testResult.alpha_intercept !== undefined && testResult.alpha_intercept !== null
                      ? testResult.alpha_intercept.toFixed(4)
                      : "N/A"
                  }
                />
                <MetricRow
                  label="R-Squared"
                  value={
                    testResult.regression_r_squared !== undefined && testResult.regression_r_squared !== null
                      ? testResult.regression_r_squared.toFixed(4)
                      : "N/A"
                  }
                />
                <MetricRow
                  label="Adjusted R²"
                  value={
                    testResult.regression_adjusted_r_squared !== undefined && testResult.regression_adjusted_r_squared !== null
                      ? testResult.regression_adjusted_r_squared.toFixed(4)
                      : "N/A"
                  }
                />
                <MetricRow
                  label="F-Statistic"
                  value={
                    testResult.regression_f_statistic !== undefined && testResult.regression_f_statistic !== null
                      ? testResult.regression_f_statistic.toFixed(4)
                      : "N/A"
                  }
                />
                <MetricRow
                  label="Standard Error"
                  value={
                    testResult.regression_standard_error !== undefined && testResult.regression_standard_error !== null
                      ? testResult.regression_standard_error.toFixed(4)
                      : "N/A"
                  }
                />
              </div>
            </div>
            <div className="p-4 rounded-xl bg-purple-500/10 border border-purple-500/30 text-purple-300 text-sm">
              <strong>Regression Equation:</strong> Asset2 = α + β × Asset1 + ε
            </div>
          </div>
        );

      case "mean-reversion":
        return (
          <div className="space-y-6">
            <div className="p-6 rounded-xl bg-white/5 border border-white/10">
              <h3 className="text-lg font-semibold text-white mb-4">
                Mean Reversion Metrics
              </h3>
              <div className="space-y-3">
                <MetricRow
                  label="Half-Life"
                  value={testResult.half_life_days ? `${testResult.half_life_days.toFixed(1)} days` : "N/A"}
                  description="Time for spread to revert halfway to mean"
                />
                <MetricRow
                  label="Hurst Exponent"
                  value={
                    testResult.hurst_exponent !== undefined && testResult.hurst_exponent !== null
                      ? testResult.hurst_exponent.toFixed(4)
                      : "N/A"
                  }
                  description="< 0.5: Mean reverting, > 0.5: Trending"
                />
                <MetricRow
                  label="Mean Reversion Speed"
                  value={
                    testResult.mean_reversion_speed !== undefined && testResult.mean_reversion_speed !== null
                      ? testResult.mean_reversion_speed.toFixed(4)
                      : "N/A"
                  }
                  description="Rate of reversion to equilibrium"
                />
              </div>
            </div>
            {testResult.half_life_days !== null && testResult.half_life_days !== undefined && (
              <div
                className={`p-4 rounded-xl border ${
                  testResult.half_life_days < 30
                    ? "bg-green-500/10 border-green-500/30 text-green-300"
                    : testResult.half_life_days < 60
                      ? "bg-yellow-500/10 border-yellow-500/30 text-yellow-300"
                      : "bg-red-500/10 border-red-500/30 text-red-300"
                } text-sm`}
              >
                <strong>Assessment:</strong>{" "}
                {testResult.half_life_days < 30
                  ? "Fast mean reversion - excellent for short-term trading"
                  : testResult.half_life_days < 60
                    ? "Moderate mean reversion - suitable for medium-term positions"
                    : "Slow mean reversion - may require longer holding periods"}
              </div>
            )}
          </div>
        );

      case "trading-quality":
        return (
          <div className="space-y-6">
            <div className="p-6 rounded-xl bg-white/5 border border-white/10">
              <h3 className="text-lg font-semibold text-white mb-4">
                Trading Quality Metrics
              </h3>
              <div className="space-y-3">
                {testResult.sharpe_ratio !== null && testResult.sharpe_ratio !== undefined && (
                  <MetricRow
                    label="Sharpe Ratio"
                    value={testResult.sharpe_ratio.toFixed(2)}
                    description="Risk-adjusted return measure"
                  />
                )}
                {testResult.win_rate !== undefined && testResult.win_rate !== null && (
                  <MetricRow
                    label="Win Rate"
                    value={`${(testResult.win_rate as number).toFixed(1)}%`}
                    description="Historical success rate"
                  />
                )}
                {testResult.profit_factor !== undefined && testResult.profit_factor !== null && (
                  <MetricRow
                    label="Profit Factor"
                    value={(testResult.profit_factor as number).toFixed(2)}
                    description="Gross profits / gross losses"
                  />
                )}
                {testResult.max_drawdown_pct !== undefined && testResult.max_drawdown_pct !== null && (
                  <MetricRow
                    label="Max Drawdown"
                    value={`${(testResult.max_drawdown_pct as number).toFixed(1)}%`}
                    description="Largest peak-to-trough decline"
                  />
                )}
                {testResult.expected_value !== undefined && testResult.expected_value !== null && (
                  <MetricRow
                    label="Expected Value"
                    value={(testResult.expected_value as number).toFixed(4)}
                    description="Expected return per trade"
                  />
                )}
              </div>
            </div>
          </div>
        );

      case "adf":
        return (
          <div className="space-y-6">
            <div className="p-6 rounded-xl bg-white/5 border border-white/10">
              <h3 className="text-lg font-semibold text-white mb-4">ADF Test</h3>
              <div className="space-y-3">
                <MetricRow
                  label="Test Statistic"
                  value={
                    testResult.adf_test_statistic !== undefined && testResult.adf_test_statistic !== null
                      ? testResult.adf_test_statistic.toFixed(4)
                      : "N/A"
                  }
                />
                <MetricRow
                  label="P-Value"
                  value={
                    testResult.adf_pvalue !== undefined && testResult.adf_pvalue !== null
                      ? testResult.adf_pvalue.toFixed(4)
                      : "N/A"
                  }
                />
                <MetricRow
                  label="Critical Value (5%)"
                  value={
                    testResult.adf_critical_value_5pct !== undefined && testResult.adf_critical_value_5pct !== null
                      ? testResult.adf_critical_value_5pct.toFixed(4)
                      : "N/A"
                  }
                />
                {testResult.adf_used_lag !== undefined && (
                  <MetricRow label="Used Lag" value={String(testResult.adf_used_lag)} />
                )}
                {testResult.adf_is_stationary !== undefined && (
                  <MetricRow
                    label="Is Stationary"
                    value={testResult.adf_is_stationary ? "Yes" : "No"}
                  />
                )}
              </div>
            </div>
          </div>
        );

      case "phillips-perron":
        return (
          <div className="space-y-6">
            <div className="p-6 rounded-xl bg-white/5 border border-white/10">
              <h3 className="text-lg font-semibold text-white mb-4">Phillips-Perron Test</h3>
              <div className="space-y-3">
                <MetricRow
                  label="Test Statistic"
                  value={
                    testResult.pp_test_statistic !== undefined && testResult.pp_test_statistic !== null
                      ? testResult.pp_test_statistic.toFixed(4)
                      : "N/A"
                  }
                />
                <MetricRow
                  label="P-Value"
                  value={
                    testResult.pp_pvalue !== undefined && testResult.pp_pvalue !== null
                      ? testResult.pp_pvalue.toFixed(4)
                      : "N/A"
                  }
                />
                <MetricRow
                  label="Critical Value (5%)"
                  value={
                    testResult.pp_critical_value_5pct !== undefined && testResult.pp_critical_value_5pct !== null
                      ? testResult.pp_critical_value_5pct.toFixed(4)
                      : "N/A"
                  }
                />
                {testResult.pp_is_stationary !== undefined && (
                  <MetricRow
                    label="Is Stationary"
                    value={testResult.pp_is_stationary ? "Yes" : "No"}
                  />
                )}
              </div>
            </div>
          </div>
        );

      case "kpss":
        return (
          <div className="space-y-6">
            <div className="p-6 rounded-xl bg-white/5 border border-white/10">
              <h3 className="text-lg font-semibold text-white mb-4">KPSS Test</h3>
              <div className="space-y-3">
                <MetricRow
                  label="Test Statistic"
                  value={
                    testResult.kpss_test_statistic !== undefined && testResult.kpss_test_statistic !== null
                      ? testResult.kpss_test_statistic.toFixed(4)
                      : "N/A"
                  }
                />
                <MetricRow
                  label="P-Value"
                  value={
                    testResult.kpss_pvalue !== undefined && testResult.kpss_pvalue !== null
                      ? testResult.kpss_pvalue.toFixed(4)
                      : "N/A"
                  }
                />
                <MetricRow
                  label="Critical Value (5%)"
                  value={
                    testResult.kpss_critical_value_5pct !== undefined && testResult.kpss_critical_value_5pct !== null
                      ? testResult.kpss_critical_value_5pct.toFixed(4)
                      : "N/A"
                  }
                />
                {testResult.kpss_is_stationary !== undefined && (
                  <MetricRow
                    label="Is Stationary"
                    value={testResult.kpss_is_stationary ? "Yes" : "No"}
                  />
                )}
              </div>
            </div>
          </div>
        );

      default:
        return (
          <div className="p-12 text-center rounded-xl bg-white/5 border border-white/10">
            <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-400 text-lg">
              Detailed metrics for this category
            </p>
            <p className="text-gray-500 text-sm mt-2">
              Coming soon in the full implementation
            </p>
          </div>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white">
            {testResult.asset1_symbol} / {testResult.asset2_symbol}
          </h2>
          <p className="text-gray-400 text-sm mt-1">
            {testResult.granularity} • {testResult.lookback_days} days •{" "}
            {testResult.test_date ? new Date(testResult.test_date).toLocaleDateString() : ""}
          </p>
        </div>
      </div>

      {/* Content Area (full width, categories moved to header) */}
      <div className="p-6 rounded-2xl bg-gradient-to-br from-white/5 to-white/[0.02] border border-white/10">
        {renderCategoryContent()}
      </div>
    </div>
  );
}

// Helper component for metric rows
function MetricRow({
  label,
  value,
  description,
}: {
  label: string;
  value: string;
  description?: string;
}) {
  return (
    <div className="flex items-center justify-between p-3 rounded-lg bg-white/5">
      <div>
        <div className="text-sm font-medium text-gray-300">{label}</div>
        {description && (
          <div className="text-xs text-gray-500 mt-0.5">{description}</div>
        )}
      </div>
      <div className="text-sm font-semibold text-white">{value}</div>
    </div>
  );
}
