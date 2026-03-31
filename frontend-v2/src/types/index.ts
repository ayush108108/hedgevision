/**
 * Centralized TypeScript type definitions for HedgeVision frontend
 *
 * This file consolidates shared types from:
 * - services/cointegrationApi.ts
 * - services/pair.ts
 * - services/correlation.ts
 * - services/screener.ts (minimal - only ScreenerStatus)
 * - component prop interfaces
 */

// ============================================
// Common Types
// ============================================

export type Granularity = "daily" | "4h" | "intraday";
export type AssetType = "stock" | "etf" | "crypto" | "index";
export type SignalType = "long" | "short" | "exit" | "hold";
export type SignalStatus = "active" | "filled" | "exited" | "cancelled";
export type CointegrationStrength =
  | "very_strong"
  | "strong"
  | "moderate"
  | "weak"
  | "none";
export type TradingSuitability = "excellent" | "good" | "fair" | "poor";
export type CorrelationMethod = "pearson" | "spearman";
export type CorrelationViewMode = "sector" | "asset";

// ============================================
// Cointegration Types
// ============================================

export interface TestPairRequest {
  asset1: string;
  asset2: string;
  granularity: Granularity;
  lookback_days: number;
}

export interface TestPairResponse {
  test_id: string;
  asset1: string;
  asset2: string;
  granularity: Granularity;
  lookback_days: number;
  overall_score: number;
  cointegration_strength: CointegrationStrength;
  is_cointegrated: boolean;
  trading_suitability: TradingSuitability;
  created_at: string;
}

export interface CointegrationTestResult {
  // Metadata
  test_id: string;
  asset1_id: string;
  asset2_id: string;
  asset1_symbol: string;
  asset2_symbol: string;
  granularity: Granularity;
  lookback_days: number;
  test_date: string;
  created_at: string;

  // Correlation metrics (5 fields)
  pearson_correlation: number;
  spearman_correlation: number;
  kendall_tau: number;
  correlation_pvalue: number;
  correlation_strength: string;

  // Engle-Granger test (7 fields)
  eg_statistic: number;
  eg_pvalue: number;
  eg_critical_1pct: number;
  eg_critical_5pct: number;
  eg_critical_10pct: number;
  residual_adf_statistic: number;
  residual_adf_pvalue: number;

  // Johansen test (6 fields)
  johansen_trace_statistic: number;
  johansen_trace_critical_90: number;
  johansen_trace_critical_95: number;
  johansen_eigenvalue_statistic: number;
  johansen_eigenvalue_critical_90: number;
  johansen_cointegration_rank: number;

  // ADF test (7 fields)
  adf_statistic: number;
  adf_pvalue: number;
  adf_critical_1pct: number;
  adf_critical_5pct: number;
  adf_critical_10pct: number;
  adf_n_lags: number;
  is_stationary_adf: boolean;

  // Phillips-Perron test (6 fields)
  pp_statistic: number;
  pp_pvalue: number;
  pp_critical_1pct: number;
  pp_critical_5pct: number;
  pp_critical_10pct: number;
  is_stationary_pp: boolean;

  // KPSS test (6 fields)
  kpss_statistic: number;
  kpss_pvalue: number;
  kpss_critical_1pct: number;
  kpss_critical_5pct: number;
  kpss_critical_10pct: number;
  is_stationary_kpss: boolean;

  // Linear regression (8 fields)
  beta_coefficient: number;
  alpha_intercept: number;
  regression_r_squared: number;
  regression_pvalue: number;
  regression_std_error: number;
  residual_mean: number;
  residual_std: number;
  residual_autocorr: number;

  // Mean reversion (3 fields)
  half_life_days: number;
  hurst_exponent: number;
  mean_reversion_speed: number;

  // Spread statistics (7 fields)
  spread_mean: number;
  spread_std: number;
  spread_volatility: number;
  spread_min: number;
  spread_max: number;
  spread_skewness: number;
  spread_kurtosis: number;

  // Z-score analysis (6 fields)
  current_zscore: number;
  zscore_mean: number;
  zscore_std: number;
  entry_threshold_long: number;
  entry_threshold_short: number;
  exit_threshold: number;

  // Trading quality metrics (6 fields)
  sharpe_ratio: number;
  sortino_ratio: number;
  max_drawdown: number;
  win_rate: number;
  average_profit: number;
  average_loss: number;

  // Overall assessment (4 fields)
  overall_score: number;
  cointegration_strength: CointegrationStrength;
  is_cointegrated: boolean;
  trading_suitability: TradingSuitability;
}

export interface TopPairsParams {
  granularity?: Granularity;
  min_score?: number;
  limit?: number;
}

export interface TopPairsResponse {
  pairs: CointegrationTestResult[];
  count: number;
  min_score: number;
  granularity: Granularity;
}

export interface ScreenRequest {
  granularity: Granularity;
  lookback_days: number;
  min_correlation?: number;
  assets?: string[];
}

export interface ScreenResponse {
  job_id: string;
  status: string;
  message: string;
}

export interface ScreenStatusResponse {
  job_id: string;
  status: "PENDING" | "STARTED" | "SUCCESS" | "FAILURE" | "RETRY";
  progress?: number;
  result?: any;
  error?: string;
}

export interface SpreadDataPoint {
  timestamp: string;
  long_asset_price: number;
  short_asset_price: number;
  spread_value: number;
  normalized_spread: number;
  zscore: number;
  spread_mean_20d: number;
  spread_std_20d: number;
  signal?: SignalType;
}

export interface SpreadHistoryResponse {
  asset1: string;
  asset2: string;
  granularity: Granularity;
  data: SpreadDataPoint[];
  latest_zscore: number;
  current_signal: SignalType;
}

export interface TradingSignal {
  signal_id: string;
  pair_trade_id: string;
  asset1_symbol: string;
  asset2_symbol: string;
  signal_type: SignalType;
  signal_strength: number;
  entry_zscore: number;
  current_zscore: number;
  status: SignalStatus;
  created_at: string;
  updated_at: string;
  fill_price?: number;
  exit_price?: number;
  pnl?: number;
}

export interface ActiveSignalsResponse {
  signals: TradingSignal[];
  count: number;
}

// ============================================
// Correlation Types
// ============================================

export interface TopPair {
  asset1: string;
  asset2: string;
  correlation: number;
}

export interface CorrelationMatrix {
  assets: string[];
  matrix: Record<string, Record<string, number>>;
  missing_assets?: string[];
  metadata?: Record<string, string>;
}

export interface RollingCorrelationRequest {
  asset1: string;
  asset2: string;
  window?: number;
  start_date?: string;
  end_date?: string;
  granularity?: string;
}

export interface RollingCorrelationPoint {
  date: string;
  correlation?: number;
}

export interface RollingCorrelationResponse {
  asset1: string;
  asset2: string;
  window: number;
  granularity: string;
  data: RollingCorrelationPoint[];
}

// ============================================
// Pair Analysis Types
// ============================================

export interface PairAnalysisResponse {
  asset1: string;
  asset2: string;
  correlation: number;
  beta: number;
  r_squared: number;
  volatility_asset1: number;
  volatility_asset2: number;
  sharpe_asset1: number;
  sharpe_asset2: number;
  cointegration_score: number;
  is_cointegrated: boolean;
  half_life: number;
  spread_zscore: number;
}

export interface RollingBetaRequest {
  asset1: string;
  asset2: string;
  window_days: number;
  lookback_days: number;
  granularity?: Granularity;
}

export interface RollingVolatilityRequest {
  asset: string;
  window_days: number;
  lookback_days: number;
  granularity?: Granularity;
}

export interface RollingPoint {
  date: string;
  value: number;
}

export interface RollingResponse {
  asset: string;
  window_days: number;
  data: RollingPoint[];
}

// ============================================
// Screener Types - REMOVED
// ============================================
// All screener types have been removed as the standalone Screener page
// was consolidated into the Cointegration page.
// Remaining screener functionality uses types from services/screener.ts

// ============================================
// Backtest Types
// ============================================

export interface EnqueueBacktestPayload {
  strategy: string;
  params: Record<string, any>;
  start_date: string;
  end_date: string;
  initial_capital: number;
}

export interface BacktestResult {
  job_id: string;
  status: string;
  strategy: string;
  start_date: string;
  end_date: string;
  initial_capital: number;
  final_capital: number;
  total_return: number;
  sharpe_ratio: number;
  max_drawdown: number;
  win_rate: number;
  total_trades: number;
  completed_at?: string;
}

// ============================================
// Cache Types
// ============================================

export interface CacheHealthResponse {
  redis_connected: boolean;
  ping_response: string;
  memory_used: string;
  memory_peak: string;
  connected_clients: number;
}

export interface CacheStatsResponse {
  total_keys: number;
  correlation_keys: number;
  pair_keys: number;
  ttl_info: Record<string, number>;
}

// ============================================
// Price Data Types
// ============================================

export interface PriceData {
  timestamp: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  adjusted_close?: number;
}

// ============================================
// Component Prop Types
// ============================================

export interface BaseComponentProps {
  className?: string;
}

export interface DataStateProps<T> {
  data: T | undefined;
  isLoading: boolean;
  error: Error | unknown;
  onRetry?: () => void;
}

export interface PaginationProps {
  page: number;
  perPage: number;
  total: number;
  onPageChange: (page: number) => void;
}

export interface FilterProps {
  filters: Record<string, any>;
  onFilterChange: (key: string, value: any) => void;
  onReset: () => void;
}

// ============================================
// Error Types
// ============================================

export type ErrorType =
  | "network"
  | "validation"
  | "not-found"
  | "server"
  | "timeout"
  | "unknown";

export interface APIError {
  message: string;
  statusCode?: number;
  code?: string;
  details?: any;
}

export interface ValidationError {
  field: string;
  message: string;
}
