import apiClient from "./apiClient";

/**
 * Screener status interface for system health monitoring.
 * Used by SystemStatusCard to display precomputation status and data freshness.
 */
export interface ScreenerStatus {
  supabase_available: boolean;
  precompute_config: {
    max_age_hours: number;
    min_correlation: number;
    max_pairs: number;
  };
  data_freshness: Record<
    string,
    {
      correlation_matrix_available: boolean;
      correlation_matrix_age_hours?: number;
      top_pairs_available: boolean;
      top_pairs_count: number;
      top_pairs_age_hours?: number;
    }
  >;
  system_health: {
    fresh_datasets: number;
    total_datasets: number;
    health_score: number;
  };
  message?: string;
}

/**
 * Get precomputation status and data freshness metrics.
 * Used by SystemStatusCard for system monitoring.
 */
export function getScreenerStatus() {
  return apiClient.get<ScreenerStatus>("/screener/status").then((r) => r.data);
}
