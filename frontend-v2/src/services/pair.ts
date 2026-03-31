import apiClient from "./apiClient";

export interface OHLCVPoint {
  open: number | null;
  high: number | null;
  low: number | null;
  close: number | null;
  volume: number | null;
}

export interface PairAnalysisResponse {
  asset1: string;
  asset2: string;
  pair_metrics: {
    correlation?: number;
    volatility_ratio?: number;
  };
  correlation?: number;
  volatility_ratio?: number;
  price_data: {
    dates: string[];
    asset1_prices: (number | null)[];
    asset2_prices: (number | null)[];
    // OHLCV data for candlestick charts
    asset1_ohlcv?: OHLCVPoint[];
    asset2_ohlcv?: OHLCVPoint[];
  };
  spread_data: Array<{
    date: string;
    spread: number | null;
    zscore: number | null;
  }>;
  regression_metrics: {
    beta?: number;
    alpha?: number;
    r_squared?: number;
    std_error?: number;
    hedge_ratio?: number;
    intercept?: number;
    scatter_data?: Array<{ x: number; y: number }>;
  };
  cointegration_results: {
    eg_test_statistic?: number;
    eg_pvalue?: number;
    eg_is_cointegrated?: boolean;
    adf_statistic?: number;
    adf_pvalue?: number;
    adf_is_stationary?: boolean;
    critical_values?: Record<string, number>;
    is_cointegrated?: boolean;
  };
}

export interface RollingBetaRequest {
  asset: string;
  benchmark?: string;
  window?: number;
  start_date?: string;
  end_date?: string;
  granularity?: string;
}

export interface RollingVolatilityRequest {
  asset: string;
  window?: number;
  start_date?: string;
  end_date?: string;
  granularity?: string;
  annualization_factor?: number;
}

export interface RollingPoint {
  date: string;
  beta?: number;
  volatility?: number;
}

export interface RollingResponse {
  asset: string;
  benchmark?: string;
  window: number;
  granularity: string;
  data: RollingPoint[];
}

export function getPairAnalysis(params: {
  asset1: string;
  asset2: string;
  start_date?: string;
  end_date?: string;
  granularity?: string;
  use_precomputed?: boolean;
}) {
  return apiClient
    .get<PairAnalysisResponse>("/pair-analysis", { params })
    .then((r) => r.data);
}

export function getCointegrationResults(params: {
  asset1: string;
  asset2: string;
  start_date?: string;
  end_date?: string;
  granularity?: string;
  use_precomputed?: boolean;
}) {
  return apiClient
    .get<Record<string, any>>("/pair-analysis/cointegration", { params })
    .then((r) => r.data);
}

export function getSpreadSeries(params: {
  asset1: string;
  asset2: string;
  start_date?: string;
  end_date?: string;
  granularity?: string;
  use_precomputed?: boolean;
}) {
  // Updated: Use cointegration spread endpoint (includes signals & z-scores from DB)
  return apiClient
    .get<{ spread_data: Array<{ timestamp: string; spread_value?: number; z_score?: number }> }>(
      `/cointegration/pairs/${params.asset1}/${params.asset2}/spread?granularity=${params.granularity || 'daily'}`,
    )
    .then((r) => r.data.spread_data.map(item => ({
      date: item.timestamp,
      spread: item.spread_value,
      zscore: item.z_score
    })));
}

export function getRollingBeta(payload: RollingBetaRequest) {
  // Updated to use metrics endpoint (deprecated /pair-analysis/rolling-beta removed)
  return apiClient
    .get<RollingResponse>(`/metrics/rolling/${payload.asset}`)
    .then((r) => r.data);
}

export function getRollingVolatility(payload: RollingVolatilityRequest) {
  return apiClient
    .post<RollingResponse>("/pair-analysis/rolling-volatility", payload)
    .then((r) => r.data);
}
