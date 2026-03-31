import apiClient from "./apiClient";

export interface CacheHealthResponse {
  status: string;
  cache_type: "redis" | "memory";
  redis_available: boolean;
  set_success: boolean;
  get_success: boolean;
  delete_success: boolean;
  config: {
    redis_host?: string;
    redis_port?: number;
    redis_db?: number;
    redis_prefix?: string;
    redis_ttl?: number;
  };
}

export interface CacheStatsResponse {
  cache_type: "redis" | "memory";
  redis_available: boolean;
  configuration: Record<string, any>;
  redis_info?: {
    connected_clients: number;
    used_memory_human: string;
    total_commands_processed: number;
    keyspace_hits: number;
    keyspace_misses: number;
    hit_rate_percent: number;
  };
}

export function getCacheHealth() {
  return apiClient.get<CacheHealthResponse>("/cache/health").then((r) => r.data);
}

export function getCacheStats() {
  return apiClient.get<CacheStatsResponse>("/cache/stats").then((r) => r.data);
}

export function clearCache() {
  return apiClient
    .post<{ status: string; message: string }>("/cache/clear")
    .then((r) => r.data);
}

export function performCacheTest(iterations = 100) {
  return apiClient
    .get<{
      iterations: number;
      cache_type: string;
      set_performance: { avg_ms: number; min_ms: number; max_ms: number };
      get_performance: { avg_ms: number; min_ms: number; max_ms: number };
  }>(`/cache/performance-test?iterations=${iterations}`)
    .then((r) => r.data);
}
