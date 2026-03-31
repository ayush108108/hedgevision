import React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  getCacheHealth,
  getCacheStats,
  CacheHealthResponse,
  CacheStatsResponse,
} from "../../services/cache";
import { getScreenerStatus, ScreenerStatus } from "../../services/screener";
import {
  Activity,
  Database,
  Server,
  Zap,
  AlertTriangle,
  CheckCircle,
  Clock,
} from "lucide-react";

interface SystemStatusCardProps {
  className?: string;
}

export function SystemStatusCard({ className = "" }: SystemStatusCardProps) {
  // Cache health query
  const { data: cacheHealth, isLoading: cacheHealthLoading } =
    useQuery<CacheHealthResponse>({
      queryKey: ["cache-health"],
      queryFn: getCacheHealth,
      staleTime: 30 * 1000, // 30 seconds
      refetchInterval: 60 * 1000, // 1 minute
    });

  // Cache stats query
  const { data: cacheStats, isLoading: cacheStatsLoading } =
    useQuery<CacheStatsResponse>({
      queryKey: ["cache-stats"],
      queryFn: getCacheStats,
      staleTime: 30 * 1000, // 30 seconds
      refetchInterval: 60 * 1000, // 1 minute
    });

  // Screener status query
  const { data: screenerStatus, isLoading: screenerStatusLoading } =
    useQuery<ScreenerStatus>({
      queryKey: ["screener-status"],
      queryFn: getScreenerStatus,
      staleTime: 60 * 1000, // 1 minute
      refetchInterval: 2 * 60 * 1000, // 2 minutes
    });

  const getStatusIcon = (healthy: boolean) => {
    return healthy ? (
      <CheckCircle className="h-5 w-5 text-green-400" />
    ) : (
      <AlertTriangle className="h-5 w-5 text-red-400" />
    );
  };

  const getStatusColor = (healthy: boolean) => {
    return healthy ? "text-green-400" : "text-red-400";
  };

  const formatBytes = (bytes: string) => {
    return bytes; // Already formatted by Redis
  };

  const formatNumber = (num: number) => {
    return num.toLocaleString();
  };

  return (
    <div className={`premium-card p-6 ${className}`}>
      <div className="flex items-center gap-3 mb-6">
        <Activity className="h-6 w-6 text-blue-400" />
        <h2 className="text-xl font-semibold text-white">System Status</h2>
      </div>

      <div className="space-y-6">
        {/* Cache Status */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Database className="h-5 w-5 text-blue-400" />
            <h3 className="font-medium text-white">Cache System</h3>
          </div>

          {cacheHealthLoading ? (
            <div className="animate-pulse">
              <div className="h-4 bg-gray-700 rounded w-1/2 mb-2"></div>
              <div className="h-4 bg-gray-700 rounded w-1/3"></div>
            </div>
          ) : cacheHealth ? (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="bg-white/5 rounded-lg p-4 border border-gray-700">
                <div className="flex items-center justify-between">
                  <span className="text-sm text-gray-400">Cache Type</span>
                  {getStatusIcon(cacheHealth.status === "healthy")}
                </div>
                <div
                  className={`text-lg font-semibold ${getStatusColor(cacheHealth.status === "healthy")}`}
                >
                  {cacheHealth.cache_type}
                </div>
                <div className="text-xs text-gray-500 mt-1">
                  Redis:{" "}
                  {cacheHealth.redis_available ? "Available" : "Unavailable"}
                </div>
              </div>

              <div className="bg-white/5 rounded-lg p-4 border border-gray-700">
                <div className="text-sm text-gray-400">Operations</div>
                <div className="text-sm text-gray-300 space-y-1">
                  <div className="flex justify-between">
                    <span>Set:</span>
                    <span className={getStatusColor(cacheHealth.set_success)}>
                      {cacheHealth.set_success ? "✓" : "✗"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Get:</span>
                    <span className={getStatusColor(cacheHealth.get_success)}>
                      {cacheHealth.get_success ? "✓" : "✗"}
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span>Delete:</span>
                    <span
                      className={getStatusColor(cacheHealth.delete_success)}
                    >
                      {cacheHealth.delete_success ? "✓" : "✗"}
                    </span>
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="text-red-400 text-sm">Cache status unavailable</div>
          )}

          {/* Redis Stats */}
          {cacheStats?.redis_info && (
            <div className="mt-4 bg-white/5 rounded-lg p-4 border border-gray-700">
              <h4 className="font-medium text-white mb-3">Redis Performance</h4>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <div className="text-gray-400">Memory Usage</div>
                  <div className="font-medium text-white">
                    {formatBytes(cacheStats.redis_info.used_memory_human)}
                  </div>
                </div>
                <div>
                  <div className="text-gray-400">Connections</div>
                  <div className="font-medium text-white">
                    {formatNumber(cacheStats.redis_info.connected_clients)}
                  </div>
                </div>
                <div>
                  <div className="text-gray-400">Commands</div>
                  <div className="font-medium text-white">
                    {formatNumber(
                      cacheStats.redis_info.total_commands_processed,
                    )}
                  </div>
                </div>
                <div>
                  <div className="text-gray-400">Hit Rate</div>
                  <div
                    className={`font-medium ${cacheStats.redis_info.hit_rate_percent > 80 ? "text-green-400" : cacheStats.redis_info.hit_rate_percent > 60 ? "text-yellow-400" : "text-red-400"}`}
                  >
                    {cacheStats.redis_info.hit_rate_percent.toFixed(1)}%
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Screener Status */}
        <div>
          <div className="flex items-center gap-2 mb-3">
            <Zap className="h-5 w-5 text-blue-400" />
            <h3 className="font-medium text-white">Pair Screener</h3>
          </div>

          {screenerStatusLoading ? (
            <div className="animate-pulse">
              <div className="h-4 bg-gray-700 rounded w-1/2 mb-2"></div>
              <div className="h-4 bg-gray-700 rounded w-1/3"></div>
            </div>
          ) : screenerStatus ? (
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="bg-white/5 rounded-lg p-4 border border-gray-700">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-400">Supabase</span>
                    {getStatusIcon(screenerStatus.supabase_available)}
                  </div>
                  <div
                    className={`text-lg font-semibold ${getStatusColor(screenerStatus.supabase_available)}`}
                  >
                    {screenerStatus.supabase_available
                      ? "Connected"
                      : "Disconnected"}
                  </div>
                </div>

                <div className="bg-white/5 rounded-lg p-4 border border-gray-700">
                  <div className="text-sm text-gray-400">System Health</div>
                  <div
                    className={`text-lg font-semibold ${
                      screenerStatus.system_health.health_score >= 80
                        ? "text-green-400"
                        : screenerStatus.system_health.health_score >= 60
                          ? "text-yellow-400"
                          : "text-red-400"
                    }`}
                  >
                    {screenerStatus.system_health.health_score}%
                  </div>
                  <div className="text-xs text-gray-500">
                    {screenerStatus.system_health.fresh_datasets}/
                    {screenerStatus.system_health.total_datasets} fresh
                  </div>
                </div>

                <div className="bg-white/5 rounded-lg p-4 border border-gray-700">
                  <div className="text-sm text-gray-400">Configuration</div>
                  <div className="text-sm text-gray-300">
                    <div>
                      Max Age: {screenerStatus.precompute_config.max_age_hours}h
                    </div>
                    <div>
                      Min Correlation:{" "}
                      {screenerStatus.precompute_config.min_correlation}
                    </div>
                    <div>
                      Max Pairs: {screenerStatus.precompute_config.max_pairs}
                    </div>
                  </div>
                </div>
              </div>

              {/* Data Freshness */}
              <div className="bg-white/5 rounded-lg p-4 border border-gray-700">
                <h4 className="font-medium text-white mb-3">Data Freshness</h4>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  {Object.entries(screenerStatus.data_freshness).map(
                    ([key, data]) => {
                      const [granularity, method] = key.split("_");
                      const isRecent =
                        data.top_pairs_age_hours !== null &&
                        data.top_pairs_age_hours !== undefined &&
                        data.top_pairs_age_hours < 24;

                      return (
                        <div
                          key={key}
                          className="border border-gray-700 rounded-lg p-3 bg-white/5"
                        >
                          <div className="flex items-center justify-between mb-2">
                            <span className="font-medium text-sm text-white">
                              {granularity} {method}
                            </span>
                            {getStatusIcon(isRecent)}
                          </div>
                          <div className="text-xs text-gray-400 space-y-1">
                            <div className="flex justify-between">
                              <span>Top Pairs:</span>
                              <span
                                className={
                                  data.top_pairs_available
                                    ? "text-green-400"
                                    : "text-red-400"
                                }
                              >
                                {data.top_pairs_available
                                  ? `${data.top_pairs_count} pairs`
                                  : "None"}
                              </span>
                            </div>
                            {data.top_pairs_age_hours !== null &&
                              data.top_pairs_age_hours !== undefined && (
                                <div className="flex justify-between">
                                  <span>Age:</span>
                                  <span
                                    className={
                                      isRecent
                                        ? "text-green-400"
                                        : "text-yellow-400"
                                    }
                                  >
                                    {data.top_pairs_age_hours.toFixed(1)}h
                                  </span>
                                </div>
                              )}
                          </div>
                        </div>
                      );
                    },
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="text-red-400 text-sm">
              Screener status unavailable
            </div>
          )}
        </div>

        {/* Last Updated */}
        <div className="border-t border-gray-700 pt-4">
          <div className="flex items-center gap-2 text-sm text-gray-400">
            <Clock className="h-4 w-4" />
            <span>Last updated: {new Date().toLocaleTimeString()}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
