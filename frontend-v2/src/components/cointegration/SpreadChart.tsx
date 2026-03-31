import React from "react";
import { useQuery } from "@tanstack/react-query";
import ReactECharts from "echarts-for-react";
import { TrendingUp, Loader2, AlertCircle } from "lucide-react";
import { getSpreadHistory } from "../../services/cointegrationApi";

interface SpreadChartProps {
  asset1: string;
  asset2: string;
  granularity?: "daily" | "intraday";
  limit?: number;
}

export function SpreadChart({
  asset1,
  asset2,
  granularity = "daily",
  limit = 252,
}: SpreadChartProps) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["spread-history", asset1, asset2, granularity, limit],
    queryFn: () => getSpreadHistory(asset1, asset2, granularity, limit),
    enabled: !!asset1 && !!asset2,
  });

  if (isLoading) {
    return (
      <div className="h-96 flex items-center justify-center rounded-2xl bg-white/5 border border-white/10">
        <div className="text-center">
          <Loader2 className="w-12 h-12 text-blue-500 animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading spread data...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-96 flex items-center justify-center rounded-2xl bg-red-500/10 border border-red-500/30">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
          <p className="text-red-300">Failed to load spread data</p>
          <p className="text-red-300/70 text-sm mt-2">
            {error instanceof Error ? error.message : "Unknown error"}
          </p>
        </div>
      </div>
    );
  }

  const spreadData = data?.spread_data || [];

  if (spreadData.length === 0) {
    return (
      <div className="h-96 flex items-center justify-center rounded-2xl bg-white/5 border border-white/10">
        <div className="text-center">
          <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <p className="text-gray-400">No spread data available</p>
          <p className="text-gray-500 text-sm mt-2">
            Run a cointegration test first
          </p>
        </div>
      </div>
    );
  }

  // Calculate statistics
  const spreadValues = spreadData.map((d) => d.spread_value);
  const zScores = spreadData.map((d) => d.z_score);
  const mean = spreadValues.reduce((a, b) => a + b, 0) / spreadValues.length;
  const std = Math.sqrt(
    spreadValues.reduce((a, b) => a + Math.pow(b - mean, 2), 0) /
      spreadValues.length,
  );
  const currentSpread = spreadValues[spreadValues.length - 1];
  const currentZScore = zScores[zScores.length - 1];

  // Format data for chart
  const chartData = spreadData.map((point) => ({
    timestamp: new Date(point.timestamp).toLocaleDateString(),
    spread: point.spread_value,
    zscore: point.z_score,
    mean: mean,
    upper1sd: mean + std,
    lower1sd: mean - std,
    upper2sd: mean + 2 * std,
    lower2sd: mean - 2 * std,
  }));

  const getZScoreColor = (zscore: number) => {
    if (Math.abs(zscore) > 2) return "text-red-400";
    if (Math.abs(zscore) > 1) return "text-yellow-400";
    return "text-green-400";
  };

  const timestamps = chartData.map((d) => d.timestamp);

  // Build markArea pairs for |z| > 1.5 zones in z-score chart
  const zMarkAreaData: [{ xAxis: string; itemStyle: { color: string } }, { xAxis: string }][] = [];
  let segStart: number | null = null;
  let segPositive = false;
  chartData.forEach((d, i) => {
    const extreme = Math.abs(d.zscore) > 1.5;
    if (extreme && segStart === null) {
      segStart = i;
      segPositive = d.zscore > 0;
    } else if (!extreme && segStart !== null) {
      zMarkAreaData.push([
        {
          xAxis: chartData[segStart].timestamp,
          itemStyle: { color: segPositive ? "rgba(239,68,68,0.15)" : "rgba(34,197,94,0.15)" },
        },
        { xAxis: chartData[i - 1].timestamp },
      ]);
      segStart = null;
    }
  });
  if (segStart !== null) {
    zMarkAreaData.push([
      {
        xAxis: chartData[segStart].timestamp,
        itemStyle: { color: segPositive ? "rgba(239,68,68,0.15)" : "rgba(34,197,94,0.15)" },
      },
      { xAxis: chartData[chartData.length - 1].timestamp },
    ]);
  }

  const spreadChartOption = {
    backgroundColor: "transparent",
    grid: { left: 60, right: 20, top: 20, bottom: 40, containLabel: false },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(17,24,39,0.95)",
      borderColor: "rgba(255,255,255,0.1)",
      textStyle: { color: "#fff", fontSize: 12 },
      formatter: (params: { name: string; value: number }[]) => {
        const p = params[0];
        return `${p.name}<br/>Spread: ${typeof p.value === "number" ? p.value.toFixed(4) : "N/A"}`;
      },
    },
    xAxis: {
      type: "category" as const,
      data: timestamps,
      axisLine: { lineStyle: { color: "#374151" } },
      axisTick: { show: false },
      axisLabel: { color: "#9ca3af", fontSize: 11, interval: Math.floor(timestamps.length / 6) },
      splitLine: { show: false },
    },
    yAxis: {
      type: "value" as const,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: "#9ca3af", fontSize: 11, formatter: (v: number) => v.toFixed(3) },
      splitLine: { lineStyle: { color: "#ffffff10" } },
    },
    series: [
      {
        name: "±2σ Band",
        type: "line" as const,
        data: chartData.map((d) => d.upper2sd),
        lineStyle: { opacity: 0 },
        areaStyle: { color: "rgba(239,68,68,0.08)" },
        symbol: "none",
        stack: "band",
        z: 0,
      },
      {
        name: "lower2sd",
        type: "line" as const,
        data: chartData.map((d) => d.lower2sd),
        lineStyle: { opacity: 0 },
        areaStyle: { color: "rgba(239,68,68,0.08)" },
        symbol: "none",
        stack: "band2",
        z: 0,
      },
      {
        name: "Mean",
        type: "line" as const,
        data: chartData.map((d) => d.mean),
        lineStyle: { color: "#8b5cf6", type: "dashed" as const, width: 1 },
        symbol: "none",
        z: 1,
      },
      {
        name: "Spread",
        type: "line" as const,
        data: chartData.map((d) => d.spread),
        lineStyle: { color: "#3b82f6", width: 2 },
        symbol: "none",
        z: 2,
      },
    ],
  };

  const zScoreChartOption = {
    backgroundColor: "transparent",
    grid: { left: 50, right: 20, top: 20, bottom: 40, containLabel: false },
    tooltip: {
      trigger: "axis",
      backgroundColor: "rgba(17,24,39,0.95)",
      borderColor: "rgba(255,255,255,0.1)",
      textStyle: { color: "#fff", fontSize: 12 },
      formatter: (params: { name: string; value: number }[]) => {
        const p = params[0];
        return `${p.name}<br/>Z-Score: ${typeof p.value === "number" ? p.value.toFixed(2) : "N/A"}`;
      },
    },
    xAxis: {
      type: "category" as const,
      data: timestamps,
      axisLine: { lineStyle: { color: "#374151" } },
      axisTick: { show: false },
      axisLabel: { color: "#9ca3af", fontSize: 11, interval: Math.floor(timestamps.length / 6) },
      splitLine: { show: false },
    },
    yAxis: {
      type: "value" as const,
      min: -3,
      max: 3,
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: "#9ca3af", fontSize: 11 },
      splitLine: { lineStyle: { color: "#ffffff10" } },
    },
    series: [
      {
        name: "Z-Score",
        type: "line" as const,
        data: chartData.map((d) => d.zscore),
        lineStyle: { color: "#f59e0b", width: 2 },
        symbol: "none",
        markLine: {
          silent: true,
          symbol: "none",
          data: [
            {
              yAxis: 2,
              lineStyle: { color: "#ef4444", type: "dashed" as const },
              label: { formatter: "Short Entry", color: "#ef4444", fontSize: 10 },
            },
            {
              yAxis: -2,
              lineStyle: { color: "#22c55e", type: "dashed" as const },
              label: { formatter: "Long Entry", color: "#22c55e", fontSize: 10 },
            },
            {
              yAxis: 1.5,
              lineStyle: { color: "#f59e0b", type: "dashed" as const, width: 1 },
              label: { formatter: "⚡ 1.5σ", color: "#f59e0b", fontSize: 10 },
            },
            {
              yAxis: -1.5,
              lineStyle: { color: "#f59e0b", type: "dashed" as const, width: 1 },
              label: { formatter: "⚡ -1.5σ", color: "#f59e0b", fontSize: 10 },
            },
            {
              yAxis: 0,
              lineStyle: { color: "#8b5cf6", type: "dashed" as const },
              label: { show: false },
            },
          ],
        },
        markArea: {
          silent: true,
          data: zMarkAreaData,
        },
      },
    ],
  };

  return (
    <div className="space-y-6">
      {/* Header with Stats */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-blue-500/30">
              <TrendingUp className="w-6 h-6 text-blue-400" />
            </div>
            Spread Analysis
          </h2>
          <p className="text-gray-400 mt-1">
            {asset1} / {asset2} • {granularity} • {spreadData.length} data
            points
          </p>
        </div>
      </div>

      {/* Current Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-white/5 border border-white/10">
          <div className="text-sm text-gray-400 mb-1">Current Spread</div>
          <div className="text-2xl font-bold text-white">
            {currentSpread?.toFixed(4) ?? "N/A"}
          </div>
        </div>
        <div className="p-4 rounded-xl bg-white/5 border border-white/10">
          <div className="text-sm text-gray-400 mb-1">Z-Score</div>
          <div className={`text-2xl font-bold ${getZScoreColor(currentZScore || 0)}`}>
            {currentZScore?.toFixed(2) ?? "N/A"}
          </div>
        </div>
        <div className="p-4 rounded-xl bg-white/5 border border-white/10">
          <div className="text-sm text-gray-400 mb-1">Mean</div>
          <div className="text-2xl font-bold text-white">
            {mean?.toFixed(4) ?? "N/A"}
          </div>
        </div>
        <div className="p-4 rounded-xl bg-white/5 border border-white/10">
          <div className="text-sm text-gray-400 mb-1">Std Dev</div>
          <div className="text-2xl font-bold text-white">
            {std?.toFixed(4) ?? "N/A"}
          </div>
        </div>
      </div>

      {/* Spread Time Series Chart */}
      <div className="p-6 rounded-2xl bg-gradient-to-br from-white/5 to-white/[0.02] border border-white/10">
        <h3 className="text-lg font-semibold text-white mb-4">
          Spread Time Series
        </h3>
        <ReactECharts option={spreadChartOption} style={{ height: 300 }} theme="dark" />
      </div>

      {/* Z-Score Chart */}
      <div className="p-6 rounded-2xl bg-gradient-to-br from-white/5 to-white/[0.02] border border-white/10">
        <h3 className="text-lg font-semibold text-white mb-4">
          Z-Score with Entry/Exit Bands
        </h3>
        <ReactECharts option={zScoreChartOption} style={{ height: 250 }} theme="dark" />
      </div>

      {/* Trading Signal */}
      <div
        className={`p-4 rounded-xl border ${
          Math.abs(currentZScore) > 2
            ? "bg-green-500/10 border-green-500/30"
            : Math.abs(currentZScore) > 1
              ? "bg-yellow-500/10 border-yellow-500/30"
              : "bg-gray-500/10 border-gray-500/30"
        }`}
      >
        <div className="flex items-center justify-between">
          <div>
            <div className="text-sm font-medium text-gray-300">
              Current Signal
            </div>
            <div
              className={`text-lg font-bold mt-1 ${
                currentZScore > 2
                  ? "text-red-400"
                  : currentZScore < -2
                    ? "text-green-400"
                    : Math.abs(currentZScore) > 1
                      ? "text-yellow-400"
                      : "text-gray-400"
              }`}
            >
              {currentZScore > 2
                ? "SHORT OPPORTUNITY"
                : currentZScore < -2
                  ? "LONG OPPORTUNITY"
                  : Math.abs(currentZScore) > 1
                    ? "WATCH"
                    : "NO SIGNAL"}
            </div>
          </div>
          <div className="text-right">
            <div className="text-sm text-gray-400">Signal Strength</div>
            <div className="text-2xl font-bold text-white">
              {Math.min((Math.abs(currentZScore) / 2) * 100, 100).toFixed(0)}%
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
