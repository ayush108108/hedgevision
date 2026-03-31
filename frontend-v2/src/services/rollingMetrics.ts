/**
 * Rolling Metrics Service
 * 
 * Fetches pre-computed rolling metrics from the rolling_metrics table.
 * All metrics must be pre-computed by the backend pipeline.
 */

import apiClient from "./apiClient";

export type MetricType = "beta" | "volatility" | "sharpe" | "sortino" | "max_drawdown" | "var_95" | "cvar_95" | "hurst";

export interface RollingMetricPoint {
  date: string;
  value: number | null;
  metric: MetricType;
}

export interface RollingMetricsRequest {
  asset: string;
  metrics: MetricType[]; // Multiple metrics can be requested
  benchmark?: string;
  window?: number;
}

export interface RollingMetricsResponse {
  asset: string;
  benchmark?: string;
  window: number;
  data: RollingMetricPoint[];
  source: "cached" | "computed"; // Indicates data source
  cached_at?: string; // When cache was created
}

/**
 * Get rolling metrics from pre-computed cache
 */
export async function getRollingMetrics(
  params: RollingMetricsRequest
): Promise<RollingMetricsResponse> {
  const {
    asset,
    metrics,
    benchmark = "SPY.US",
    window = 60,
  } = params;

  try {
    // Fetch cached data from rolling_metrics table
    const response = await apiClient.get<any>(
      `/metrics/rolling/${asset}`,
      {
        params: {
          window,
          benchmark,
        },
      }
    );

    if (!response.data?.metrics || response.data.metrics.length === 0) {
      console.warn(`No cached metrics found for ${asset}. Please run the precomputation pipeline.`);
      return {
        asset,
        benchmark,
        window,
        data: [],
        source: "computed",
      };
    }

    // Transform cached data to our format
    return transformCachedData(response.data, metrics, asset, benchmark, window);
  } catch (error) {
    console.error("Error fetching rolling metrics:", error);
    return {
      asset,
      benchmark,
      window,
      data: [],
      source: "computed",
    };
  }
}

/**
 * Transform cached data from rolling_metrics table
 */
function transformCachedData(
  cachedData: any,
  requestedMetrics: MetricType[],
  asset: string,
  benchmark: string,
  window: number
): RollingMetricsResponse {
  const dataPoints: RollingMetricPoint[] = [];

  // Extract requested metrics from cache
  cachedData.metrics.forEach((metric: any) => {
    requestedMetrics.forEach((metricType) => {
      const value = getMetricValue(metric, metricType);
      if (value !== null && value !== undefined) {
        dataPoints.push({
          date: metric.end_date,
          value,
          metric: metricType,
        });
      }
    });
  });

  return {
    asset,
    benchmark,
    window,
    data: dataPoints,
    source: "cached",
    cached_at: cachedData.metrics[0]?.created_at,
  };
}

/**
 * Get specific metric value from cached record
 */
function getMetricValue(metricRecord: any, metricType: MetricType): number | null {
  const mapping: Record<MetricType, string> = {
    beta: "rolling_beta",
    volatility: "rolling_volatility",
    sharpe: "rolling_sharpe",      // backend model field (maps from DB col rolling_sharpe_ratio)
    sortino: "rolling_sortino",
    max_drawdown: "max_drawdown",
    var_95: "var_95",
    cvar_95: "cvar_95",
    hurst: "hurst_exponent",
  };

  const fieldName = mapping[metricType];
  return metricRecord[fieldName] ?? null;
}



/**
 * Get available metrics for an asset (from cache)
 */
export async function getAvailableMetrics(asset: string): Promise<{
  windows: number[];
  benchmarks: string[];
  metrics: MetricType[];
}> {
  try {
    const response = await apiClient.get(`/metrics/rolling/${asset}`);
    
    const windows = response.data?.windows_available || [30, 60, 90, 180, 252];
    const metrics: MetricType[] = [];
    
    // Check which metrics are available in cached data
    if (response.data?.metrics?.length > 0) {
      const sample = response.data.metrics[0];
      if (sample.rolling_beta !== null) metrics.push("beta");
      if (sample.rolling_volatility !== null) metrics.push("volatility");
      if (sample.rolling_sharpe !== null) metrics.push("sharpe");
      if (sample.rolling_sortino !== null) metrics.push("sortino");
      if (sample.max_drawdown !== null) metrics.push("max_drawdown");
      if (sample.var_95 !== null) metrics.push("var_95");
      if (sample.cvar_95 !== null) metrics.push("cvar_95");
      if (sample.hurst_exponent !== null) metrics.push("hurst");
    }

    return {
      windows,
      benchmarks: ["SPY.US", "GLD.US", "BTC-USD.CC"],
      metrics: metrics.length > 0 ? metrics : ["beta", "volatility"], // Default fallback
    };
  } catch (error) {
    console.error("Error getting available metrics:", error);
    return {
      windows: [30, 60, 90, 180, 252],
      benchmarks: ["SPY.US", "GLD.US", "BTC-USD.CC"],
      metrics: ["beta", "volatility"],
    };
  }
}
