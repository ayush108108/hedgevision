import apiClient from "./apiClient";

// ============================================================================
// ERROR HANDLING
// ============================================================================

export class CointegrationAPIError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public code?: string,
    public details?: any,
  ) {
    super(message);
    this.name = "CointegrationAPIError";
  }
}

function handleAPIError(error: any, context: string): never {
  if (error.response) {
    // Server responded with error status
    const statusCode = error.response.status;
    const message =
      error.response.data?.detail ||
      error.response.data?.message ||
      error.message;
    const code = error.response.data?.code;

    if (statusCode === 404) {
      throw new CointegrationAPIError(
        `${context}: Resource not found`,
        404,
        "NOT_FOUND",
        error.response.data,
      );
    } else if (statusCode === 400) {
      throw new CointegrationAPIError(
        `${context}: Invalid request - ${message}`,
        400,
        "VALIDATION_ERROR",
        error.response.data,
      );
    } else if (statusCode === 500) {
      throw new CointegrationAPIError(
        `${context}: Server error - ${message}`,
        500,
        "SERVER_ERROR",
        error.response.data,
      );
    } else if (statusCode === 503) {
      throw new CointegrationAPIError(
        `${context}: Service temporarily unavailable`,
        503,
        "SERVICE_UNAVAILABLE",
        error.response.data,
      );
    } else {
      throw new CointegrationAPIError(
        `${context}: ${message}`,
        statusCode,
        code,
        error.response.data,
      );
    }
  } else if (error.request) {
    // Request made but no response received
    throw new CointegrationAPIError(
      `${context}: Network error - no response from server`,
      0,
      "NETWORK_ERROR",
      { originalError: error.message },
    );
  } else {
    // Error setting up request
    throw new CointegrationAPIError(
      `${context}: ${error.message}`,
      0,
      "REQUEST_ERROR",
      { originalError: error.message },
    );
  }
}

// ============================================================================
// TYPES & INTERFACES
// ============================================================================

export interface TestPairRequest {
  asset1: string;
  asset2: string;
  granularity?: string;
  lookback_days?: number;
}

export interface TestPairResponse {
  test_id: string;
  asset1_symbol: string;
  asset2_symbol: string;
  test_date: string;
  granularity: string;
  lookback_days: number;
  sample_size: number;
  overall_score: number;
  cointegration_strength: string;
  trading_suitability: string;
  risk_level: string;
  eg_is_cointegrated: boolean;
  eg_pvalue: number;
  beta_coefficient: number;
  half_life_days: number;
  sharpe_ratio: number | null;
  computation_time_ms: number;
}

export interface CointegrationTestResult {
  // All 69 fields
  asset1_symbol: string;
  asset2_symbol: string;
  test_date: string;
  granularity: string;
  lookback_days: number;
  sample_size: number;

  // Correlation
  pearson_correlation: number;
  spearman_correlation: number;
  kendall_tau: number;
  correlation_pvalue: number;
  correlation_significance: string;

  // Engle-Granger
  eg_test_statistic: number;
  eg_pvalue: number;
  eg_critical_value_1pct: number;
  eg_critical_value_5pct: number;
  eg_critical_value_10pct: number;
  eg_is_cointegrated: boolean;
  eg_significance_level: string;

  // Johansen
  johansen_trace_stat: number;
  johansen_eigen_stat: number;
  johansen_rank: number;
  johansen_is_cointegrated: boolean;
  johansen_trace_critical: any;
  johansen_eigen_critical: any;

  // ADF
  adf_test_statistic: number;
  adf_pvalue: number;
  adf_critical_value_1pct: number;
  adf_critical_value_5pct: number;
  adf_critical_value_10pct: number;
  adf_is_stationary: boolean;
  adf_used_lag: number;

  // Phillips-Perron
  pp_test_statistic: number;
  pp_pvalue: number;
  pp_critical_value_1pct: number;
  pp_critical_value_5pct: number;
  pp_critical_value_10pct: number;
  pp_is_stationary: boolean;

  // KPSS
  kpss_test_statistic: number;
  kpss_pvalue: number;
  kpss_critical_value_1pct: number;
  kpss_critical_value_2_5pct: number;
  kpss_critical_value_5pct: number;
  kpss_critical_value_10pct: number;
  kpss_is_stationary: boolean;

  // Regression
  beta_coefficient: number;
  alpha_intercept: number;
  regression_r_squared: number;
  regression_adjusted_r_squared: number;
  regression_f_statistic: number;
  regression_f_pvalue: number;
  regression_durbin_watson: number;
  regression_standard_error: number;

  // Mean Reversion
  half_life_days: number;
  mean_reversion_speed: number;
  hurst_exponent: number;

  // Spread Stats
  spread_current: number;
  spread_mean: number;
  spread_std: number;
  spread_min: number;
  spread_max: number;
  spread_skewness: number;
  spread_kurtosis: number;

  // Z-Score
  zscore_current: number;
  zscore_mean: number;
  zscore_std: number;
  zscore_entry_threshold: number;
  zscore_exit_threshold: number;
  zscore_stop_loss: number;

  // Trading Quality
  signal_quality_score: number;
  sharpe_ratio: number | null;
  profit_factor: number | null;
  win_rate: number | null;
  max_drawdown_pct: number | null;
  expected_value: number | null;

  // Overall
  overall_score: number;
  cointegration_strength: string;
  trading_suitability: string;
  risk_level: string;

  // Metadata
  data_quality_score: number;
  computation_time_ms: number;
  error_message: string | null;
}

export interface TopPairsParams {
  limit?: number;
  granularity?: string;
  min_score?: number;
}

export interface TopPairsResponse {
  granularity: string;
  min_score: number;
  count: number;
  pairs: CointegrationTestResult[];
}

export interface ScreenRequest {
  granularity?: string;
  lookback_days?: number;
  min_correlation?: number;
  assets?: string[];
}

export interface ScreenResponse {
  job_id: string;
  status: string;
  message: string;
  check_status_at: string;
}

export interface ScreenStatusResponse {
  job_id: string;
  status: string;
  progress: any;
  started_at: string | null;
  completed_at: string | null;
  results_count: number | null;
}

export interface SpreadDataPoint {
  timestamp: string;
  long_asset_price: number;
  short_asset_price: number;
  spread_value: number;
  spread_mean_20d: number;
  spread_std_20d: number;
  z_score: number;
  signal: string;
}

export interface SpreadHistoryResponse {
  asset1: string;
  asset2: string;
  pair_id: string;
  granularity: string;
  count: number;
  spread_data: SpreadDataPoint[];
}

export interface TradingSignal {
  id: string;
  pair_trade_id: string;
  asset1_symbol: string;
  asset2_symbol: string;
  granularity: string;
  signal_type: string;
  signal_strength: number;
  current_zscore: number;
  entry_threshold: number;
  exit_threshold: number;
  stop_loss: number;
  hedge_ratio: number;
  status: string;
  generated_at: string;
}

export interface ActiveSignalsResponse {
  granularity: string;
  signal_type: string | null;
  count: number;
  signals: TradingSignal[];
}

// ============================================================================
// API FUNCTIONS
// ============================================================================

/**
 * Test a single asset pair for cointegration
 */
export async function testPair(
  request: TestPairRequest,
): Promise<TestPairResponse> {
  try {
    const response = await apiClient.post<TestPairResponse>(
      "/cointegration/test-pair",
      {
        asset1: request.asset1,
        asset2: request.asset2,
        granularity: request.granularity || "daily",
        lookback_days: request.lookback_days || 252,
      },
    );
    return response.data;
  } catch (error) {
    handleAPIError(error, `Test Pair ${request.asset1}/${request.asset2}`);
  }
}

/**
 * Get complete test results by test ID
 */
export async function getTestResults(
  testId: string,
): Promise<CointegrationTestResult> {
  try {
    const response = await apiClient.get<CointegrationTestResult>(
      `/cointegration/results/${testId}`,
    );
    return response.data;
  } catch (error) {
    handleAPIError(error, `Get Test Results (${testId})`);
  }
}

/**
 * Get historical test results for a specific pair
 */
export async function getPairHistory(
  asset1: string,
  asset2: string,
  granularity: string = "daily",
  limit: number = 10,
): Promise<any> {
  try {
    const response = await apiClient.get(
      `/cointegration/results/pair/${asset1}/${asset2}?granularity=${granularity}&limit=${limit}`,
    );
    return response.data;
  } catch (error) {
    handleAPIError(error, `Get Pair History ${asset1}/${asset2}`);
  }
}

/**
 * Get top cointegrated pairs
 */
export async function getTopPairs(
  params: TopPairsParams = {},
): Promise<TopPairsResponse> {
  try {
    const queryParams = new URLSearchParams({
      limit: String(params.limit || 20),
      granularity: params.granularity || "daily",
      min_score: String(params.min_score || 60.0),
    });

    // Updated: Use unified screener endpoint (consolidated from /cointegration/pairs/top)
    const response = await apiClient.get<TopPairsResponse>(
      `/screener/cointegration/top-pairs?${queryParams}`,
    );
    return response.data;
  } catch (error) {
    handleAPIError(error, "Get Top Pairs");
  }
}

/**
 * Get latest cointegration scores
 */
export async function getLatestScores(
  granularity: string = "daily",
  cointegrated_only: boolean = true,
  limit: number = 50,
): Promise<any> {
  try {
    const response = await apiClient.get(
      `/cointegration/pairs/latest?granularity=${granularity}&cointegrated_only=${cointegrated_only}&limit=${limit}`,
    );
    return response.data;
  } catch (error) {
    handleAPIError(error, "Get Latest Scores");
  }
}

/**
 * Start batch screening
 */
export async function startScreening(
  request: ScreenRequest,
): Promise<ScreenResponse> {
  // Deprecated: Celery removed. For now, no-op to avoid breaking UI; backend no longer supports async screening.
  return Promise.resolve({
    job_id: "deprecated",
    status: "completed",
    message: "Async screening deprecated; use direct tests",
    check_status_at: new Date().toISOString(),
  } as ScreenResponse);
}

/**
 * Get screening job status
 * @deprecated Celery removed, use synchronous screening
 */
export async function getScreeningStatus(
  jobId: string,
): Promise<ScreenStatusResponse> {
  // Deprecated: Celery removed. Return a completed status to avoid UI errors if called.
  return Promise.resolve({
    job_id: jobId,
    status: "completed",
    progress: null,
    started_at: null,
    completed_at: new Date().toISOString(),
    results_count: null,
  } as ScreenStatusResponse);
}

/**
 * Get spread history for a pair
 */
export async function getSpreadHistory(
  asset1: string,
  asset2: string,
  granularity: string = "daily",
  limit: number = 100,
): Promise<SpreadHistoryResponse> {
  try {
    const response = await apiClient.get<SpreadHistoryResponse>(
      `/cointegration/pairs/${asset1}/${asset2}/spread?granularity=${granularity}&limit=${limit}`,
    );
    return response.data;
  } catch (error) {
    handleAPIError(error, `Get Spread History ${asset1}/${asset2}`);
  }
}

/**
 * Get active trading signals
 */
export async function getActiveSignals(
  params: {
    granularity?: string;
    signal_type?: string;
  } = {},
): Promise<ActiveSignalsResponse> {
  try {
    const queryParams = new URLSearchParams({
      granularity: params.granularity || "daily",
      ...(params.signal_type && { signal_type: params.signal_type }),
    });

    const response = await apiClient.get<ActiveSignalsResponse>(
      `/cointegration/signals/active?${queryParams}`,
    );
    return response.data;
  } catch (error) {
    handleAPIError(error, "Get Active Signals");
  }
}

/**
 * Update signal status
 */
export async function updateSignal(
  signalId: string,
  status: string,
  fillPrice?: number,
  exitPrice?: number,
): Promise<any> {
  try {
    const queryParams = new URLSearchParams({ status });
    if (fillPrice !== undefined)
      queryParams.append("fill_price", String(fillPrice));
    if (exitPrice !== undefined)
      queryParams.append("exit_price", String(exitPrice));

    const response = await apiClient.post(
      `/cointegration/signals/${signalId}/update?${queryParams}`,
    );
    return response.data;
  } catch (error) {
    handleAPIError(error, `Update Signal (${signalId})`);
  }
}

/**
 * Refresh materialized view
 */
export async function refreshScores(): Promise<any> {
  try {
    const response = await apiClient.post("/cointegration/refresh-scores");
    return response.data;
  } catch (error) {
    handleAPIError(error, "Refresh Scores");
  }
}

/**
 * Delete test result
 */
export async function deleteTestResult(testId: string): Promise<any> {
  try {
    const response = await apiClient.delete(`/cointegration/results/${testId}`);
    return response.data;
  } catch (error) {
    handleAPIError(error, `Delete Test Result (${testId})`);
  }
}
