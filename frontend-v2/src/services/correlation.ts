import apiClient from "../services/apiClient";
import type {
  TopPair,
  CorrelationMatrix,
  RollingCorrelationRequest,
  RollingCorrelationResponse,
} from "../types";

export function getTopPairs(
  params: {
    limit?: number;
    start_date?: string;
    end_date?: string;
    method?: string;
    sector?: string;
    granularity?: string;
    min_periods?: number;
    min_correlation?: number;
    use_precomputed?: boolean;
  } = {},
) {
  const query = new URLSearchParams();

  if (params.limit !== undefined)
    query.append("limit", params.limit.toString());
  if (params.start_date) query.append("start_date", params.start_date);
  if (params.end_date) query.append("end_date", params.end_date);
  if (params.method) query.append("method", params.method);
  if (params.sector) query.append("sector", params.sector);
  if (params.granularity) query.append("granularity", params.granularity);
  if (params.min_periods !== undefined)
    query.append("min_periods", params.min_periods.toString());
  if (params.min_correlation !== undefined)
    query.append("min_correlation", params.min_correlation.toString());
  if (params.use_precomputed !== undefined)
    query.append("use_precomputed", params.use_precomputed.toString());

  // Updated to use screener endpoint (deprecated /correlation/top-pairs removed)
  // The backend returns a unified response { pairs: UnifiedScreenerPair[], ... }.
  // Map it into TopPair[] shape expected by UI components.
  return apiClient
    .get(`/screener/correlation/top-pairs?${query.toString()}`)
    .then((r) => {
      const data: any = r.data;
      const pairs = Array.isArray(data?.pairs) ? data.pairs : [];
      const mapped: TopPair[] = pairs.map((p: any) => {
        // Prefer the raw correlation when provided as secondary_metric_value.
        const corrRaw: number | undefined =
          typeof p?.secondary_metric_value === "number"
            ? p.secondary_metric_value
            : undefined;
        const corrAbs: number | undefined =
          typeof p?.primary_metric_value === "number"
            ? p.primary_metric_value
            : undefined;
        return {
          asset1: p?.asset1 ?? p?.asset1_symbol ?? "",
          asset2: p?.asset2 ?? p?.asset2_symbol ?? "",
          correlation:
            corrRaw !== undefined
              ? corrRaw
              : corrAbs !== undefined
              ? corrAbs
              : 0,
        } as TopPair;
      });
      return mapped;
    });
}

export function getCorrelationMatrix(
  params: {
    start_date?: string;
    end_date?: string;
    method?: string;
    sector?: string;
    granularity?: string;
    min_periods?: number;
    view_mode?: string;
  } = {},
) {
  const query = new URLSearchParams();

  if (params.start_date) query.append("start_date", params.start_date);
  if (params.end_date) query.append("end_date", params.end_date);
  if (params.method) query.append("method", params.method);
  if (params.sector) query.append("sector", params.sector);
  if (params.granularity) query.append("granularity", params.granularity);
  if (params.min_periods !== undefined)
    query.append("min_periods", params.min_periods.toString());
  if (params.view_mode) query.append("view_mode", params.view_mode);

  return apiClient
    .get<CorrelationMatrix>(`/correlation?${query.toString()}`)
    .then((r) => r.data);
}

export function getRollingCorrelation(payload: RollingCorrelationRequest) {
  // Deprecated: Use pre-computed correlation matrices from /api/correlation instead
  throw new Error("Rolling correlation computation deprecated. Use pre-computed data from /api/correlation");
}
