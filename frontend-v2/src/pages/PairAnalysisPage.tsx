import { useEffect, useMemo, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { getPairAnalysis } from "../services/pair";
import { getRollingMetrics, type MetricType } from "../services/rollingMetrics";
import { SyncedCharts } from "../components/charts/SyncedCharts";
import { RollingMetricsChart } from "../components/charts/RollingMetricsChart";
import {
  ALL_ASSET_NAMES,
  getSymbolFromName,
} from "../constants/assets";
import { BenchmarkSelector, getBenchmarkSymbol, getBenchmarkById } from "../components/controls/BenchmarkSelector";
import { MetricSelector } from "../components/controls/MetricSelector";
import { WindowSelector } from "../components/controls/WindowSelector";
import { RefreshCw, Mail, Maximize2, X } from "lucide-react";
import { Select } from "../components/common/Select";
import { DatePicker } from "../components/common/DatePicker";
import { LoadingChart } from "../components/common/LoadingChart";
import { HedgeRatioCalculator } from "../components/HedgeRatioCalculator";
import { InfoTooltip } from "../components/common/Tooltip";
import {
  getApiAssetSymbol,
  getDisplayAssetName,
  getPairSignalSummary,
} from "../utils/pairs";

function getInitialAssetValue(paramValue: string | null, fallback: string): string {
  return getDisplayAssetName(paramValue) || fallback;
}

export function PairAnalysisPage() {
  const [searchParams] = useSearchParams();
  const [asset1, setAsset1] = useState(getInitialAssetValue(searchParams.get("asset1"), "Apple"));
  const [asset2, setAsset2] = useState(
    getInitialAssetValue(searchParams.get("asset2"), "Microsoft"),
  );
  // Dynamic dates: last 12 months from today (data only goes back to ~2024-03-21)
  const todayStr = new Date().toISOString().slice(0, 10);
  const oneYearAgoStr = new Date(Date.now() - 365 * 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  const [startDate, setStartDate] = useState(oneYearAgoStr);
  const [endDate, setEndDate] = useState(todayStr);
  const [granularity, setGranularity] = useState<string>("daily");
  const [selectedBenchmark, setSelectedBenchmark] = useState<string>("spy");
  
  const [selectedMetrics, setSelectedMetrics] = useState<MetricType[]>(
    ["beta", "volatility"]
  );
  const [selectedWindow, setSelectedWindow] = useState<number>(60);
  // Separate asset selector for rolling metrics - use asset1 by default
  const [metricsAsset, setMetricsAsset] = useState<string>(getInitialAssetValue(searchParams.get("asset1"), "Apple"));

  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const [isChartFullscreen, setIsChartFullscreen] = useState(false);

  // Close fullscreen on Escape key
  useEffect(() => {
    if (!isChartFullscreen) return;
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setIsChartFullscreen(false);
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [isChartFullscreen]);

  useEffect(() => {
    const nextAsset1 = getInitialAssetValue(searchParams.get("asset1"), "Apple");
    const nextAsset2 = getInitialAssetValue(searchParams.get("asset2"), "Microsoft");

    setAsset1(nextAsset1);
    setAsset2(nextAsset2);
    setMetricsAsset(nextAsset1);
  }, [searchParams]);

  const { data, isLoading, error } = useQuery({
    queryKey: [
      "pair-analysis",
      asset1,
      asset2,
      startDate,
      endDate,
      granularity,
    ],
    queryFn: () => {
      // Resolve either display name or raw symbol from URL/state
      const symbol1 = getApiAssetSymbol(asset1);
      const symbol2 = getApiAssetSymbol(asset2);

      if (!symbol1 || !symbol2) {
        throw new Error(`Invalid asset selection: '${asset1}' or '${asset2}' not recognized`);
      }

      return getPairAnalysis({
        asset1: symbol1,
        asset2: symbol2,
        start_date: startDate,
        end_date: endDate,
        granularity: granularity,
      });
    },
    enabled: !!asset1 && !!asset2,
  });

  // Get benchmark data - memoized for performance
  const benchmarkSymbol = useMemo(() => getBenchmarkSymbol(selectedBenchmark), [selectedBenchmark]);
  const benchmarkInfo = useMemo(() => getBenchmarkById(selectedBenchmark), [selectedBenchmark]);
  const metricsAssetSymbol = useMemo(() => getApiAssetSymbol(metricsAsset) || metricsAsset, [metricsAsset]);

  // Query rolling metrics (unified)
  const { data: metricsData, isLoading: metricsLoading } = useQuery({
    queryKey: ["rolling-metrics", metricsAsset, selectedBenchmark, selectedWindow, selectedMetrics],
    queryFn: () =>
      getRollingMetrics({
        asset: metricsAssetSymbol,
        benchmark: benchmarkSymbol,
        window: selectedWindow,
        metrics: selectedMetrics,
      }),
    enabled: !!metricsAsset && selectedMetrics.length > 0,
  });

  const handleRefresh = () => {
    queryClient.invalidateQueries({
      queryKey: [
        "pair-analysis",
        asset1,
        asset2,
        startDate,
        endDate,
        granularity,
      ],
    });
    queryClient.invalidateQueries({ queryKey: ["rolling-metrics"] });
  };

  // Transform price data for chart - memoized for performance
  const priceData = useMemo(() => {
    return data?.price_data
      ? data.price_data.dates.map((date, i) => ({
          date,
          asset1_price: data.price_data.asset1_prices[i],
          asset2_price: data.price_data.asset2_prices[i],
        }))
      : [];
  }, [data?.price_data]);

  // Compute pair beta for header (fallback if regression_metrics missing)
  const pairBeta = useMemo(() => {
    // Prefer API-provided regression slope if available
    const slope = (data as any)?.regression_metrics?.slope;
    if (typeof slope === "number" && isFinite(slope)) return slope;

    if (!priceData.length) return undefined;
    // Compute daily returns
    const r1: number[] = [];
    const r2: number[] = [];
    for (let i = 1; i < priceData.length; i++) {
      const p1Prev = priceData[i - 1].asset1_price;
      const p1 = priceData[i].asset1_price;
      const p2Prev = priceData[i - 1].asset2_price;
      const p2 = priceData[i].asset2_price;
      if (p1Prev && p2Prev && p1 && p2) {
        r1.push((p1 - p1Prev) / p1Prev);
        r2.push((p2 - p2Prev) / p2Prev);
      }
    }
    if (r1.length < 5 || r2.length < 5) return undefined;
    const mean = (arr: number[]) => arr.reduce((a, b) => a + b, 0) / arr.length;
    const m1 = mean(r1);
    const m2 = mean(r2);
    let cov = 0;
    let var2 = 0;
    for (let i = 0; i < r1.length; i++) {
      cov += (r1[i] - m1) * (r2[i] - m2);
      var2 += (r2[i] - m2) * (r2[i] - m2);
    }
    cov /= r1.length - 1;
    var2 /= r2.length - 1;
    if (var2 === 0) return undefined;
    return cov / var2;
  }, [data, priceData]);

  // Annualized volatility for asset1 based on available price data
  const asset1Vol = useMemo(() => {
    if (!priceData.length) return undefined;
    const returns: number[] = [];
    for (let i = 1; i < priceData.length; i++) {
      const prev = priceData[i - 1].asset1_price;
      const curr = priceData[i].asset1_price;
      if (prev && curr) returns.push((curr - prev) / prev);
    }
    if (returns.length < 5) return undefined;
    const mean = returns.reduce((a, b) => a + b, 0) / returns.length;
    const variance =
      returns.reduce((s, r) => s + (r - mean) * (r - mean), 0) /
      (returns.length - 1);
    const dailyStd = Math.sqrt(variance);
    const annualized = dailyStd * Math.sqrt(252);
    return annualized;
  }, [priceData]);

  // Latest z-score for the hedge calculator
  const currentZScore = useMemo(() => {
    const sd = data?.spread_data;
    if (!sd || !sd.length) return undefined;
    const last = sd[sd.length - 1];
    return typeof last?.zscore === "number" ? last.zscore : undefined;
  }, [data?.spread_data]);

  const pairSignal = useMemo(
    () =>
      getPairSignalSummary({
        currentZScore,
        isCointegrated: data?.cointegration_results?.eg_is_cointegrated,
        asset1Name: asset1,
        asset2Name: asset2,
      }),
    [asset1, asset2, currentZScore, data?.cointegration_results?.eg_is_cointegrated],
  );

  // Compute combined chart height to fit in one screen without scrolling
  const [combinedHeight, setCombinedHeight] = useState<number>(680);
  useEffect(() => {
    const compute = () => {
      const vh = typeof window !== "undefined" ? window.innerHeight : 900;
      // Reserve space for header and controls (~280px), keep within sensible bounds
      const h = Math.max(520, Math.min(820, vh - 300));
      setCombinedHeight(h);
    };
    compute();
    window.addEventListener("resize", compute);
    return () => window.removeEventListener("resize", compute);
  }, []);

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="premium-card p-5 sm:p-8">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-white mb-2">
              Pair Analysis
            </h1>
            <p className="text-gray-400 text-sm max-w-2xl">
              Deep statistical analysis of two assets — cointegration, spread tracking, and
              position sizing for pairs trading.
            </p>
          </div>
          <div className="flex flex-wrap gap-2">
            <button
              onClick={handleRefresh}
              disabled={isLoading}
              className="premium-button flex items-center gap-2 text-sm"
            >
              <RefreshCw
                className={`h-4 w-4 ${isLoading ? "animate-spin" : ""}`}
              />
              {isLoading ? "Refreshing..." : "Refresh"}
            </button>
            <button
              onClick={() => {
                const s1 = getSymbolFromName(asset1);
                const s2 = getSymbolFromName(asset2);
                navigate(`/cointegration?asset1=${encodeURIComponent(s1 || asset1)}&asset2=${encodeURIComponent(s2 || asset2)}&view=test`);
              }}
              className="premium-button text-sm"
            >
              See Test Results
            </button>
          </div>
        </div>
      </div>

      {/* Controls */}
      <div className="premium-card p-8">
        <h2 className="text-lg font-semibold text-white mb-6">
          Configure Analysis
        </h2>
        <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-5 gap-4 overflow-visible">
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Asset 1
            </label>
            <Select
              value={asset1}
              onChange={setAsset1}
              options={ALL_ASSET_NAMES.map((n) => ({ label: n, value: n }))}
              className="w-full"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Asset 2
            </label>
            <Select
              value={asset2}
              onChange={setAsset2}
              options={ALL_ASSET_NAMES.map((n) => ({ label: n, value: n }))}
              className="w-full"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-300 mb-2">
              Timeframe
            </label>
            <Select
              value={granularity}
              onChange={setGranularity}
              options={[
                { label: "Daily", value: "daily" },
                { label: "4 Hour", value: "4h" },
                { label: "Hourly", value: "hourly" },
              ]}
              className="w-full"
            />
          </div>
          <DatePicker
            label="Start Date"
            value={startDate}
            onChange={setStartDate}
          />
          <DatePicker
            label="End Date"
            value={endDate}
            onChange={setEndDate}
          />
        </div>
      </div>

      {/* Loading/Error States */}
      {isLoading && <LoadingChart />}
      {error && (
        <div className="premium-card p-8 bg-red-500/10 border-red-500/30">
          <p className="text-red-400 text-center">
            Error: {(error as Error).message}
          </p>
        </div>
      )}

      {/* Results */}
      {data && (
        <div className="space-y-8">
          {/* Metrics */}
          <div className="premium-card p-8">
            <h3 className="text-lg font-semibold text-white mb-6">
              Pair Metrics
            </h3>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
              <div className="text-center">
                <div
                  className="text-4xl sm:text-5xl font-bold text-blue-400 mb-2"
                  style={{ textShadow: "0 0 20px rgba(125, 211, 252, 0.5)" }}
                >
                  {(
                    data.correlation || data.pair_metrics?.correlation
                  )?.toFixed(3) || "N/A"}
                </div>
                <div className="text-sm text-gray-400 uppercase tracking-wider flex items-center justify-center gap-1">
                  Correlation
                  <InfoTooltip
                    title="Correlation"
                    text="How closely the two assets move together. +1 means they move in perfect lockstep, 0 means no relationship, -1 means they move in opposite directions. For pairs trading, higher is better (above 0.7)."
                  />
                </div>
              </div>
              <div className="text-center">
                <div
                  className="text-4xl sm:text-5xl font-bold text-green-400 mb-2"
                  style={{ textShadow: "0 0 20px rgba(16, 185, 129, 0.5)" }}
                >
                  {pairBeta !== undefined ? pairBeta.toFixed(3) : "N/A"}
                </div>
                <div className="text-sm text-gray-400 uppercase tracking-wider flex items-center justify-center gap-1">
                  Hedge Ratio (β)
                  <InfoTooltip
                    title="Hedge Ratio (Beta)"
                    text={`For every $1 you put into ${asset1}, put $${pairBeta?.toFixed(2) ?? "β"} into ${asset2} to keep the trade balanced. The Hedge Ratio Calculator below uses this number to give you exact dollar amounts.`}
                  />
                </div>
              </div>
              <div className="text-center">
                <div
                  className="text-4xl sm:text-5xl font-bold text-purple-400 mb-2"
                  style={{ textShadow: "0 0 20px rgba(168, 85, 247, 0.5)" }}
                >
                  {asset1Vol !== undefined ? (asset1Vol * 100).toFixed(2) + "%" : "N/A"}
                </div>
                <div className="text-sm text-gray-400 uppercase tracking-wider flex items-center justify-center gap-1">
                  {asset1} Volatility
                  <InfoTooltip
                    title="Annual Volatility"
                    text={`How much ${asset1}'s price typically swings in a year, expressed as a percentage. Higher volatility = bigger potential swings. A 20% vol means the price could reasonably move ±20% over the next year. Pairs traders look at both assets' volatility when sizing positions.`}
                  />
                </div>
              </div>
            </div>

            {/* Essential Cointegration Metrics Row */}
            {data.cointegration_results && (
              <div className="mt-8 pt-8 border-t border-gray-700/50">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-6">
                    <div className="text-xs">
                      <div className="text-gray-500 uppercase tracking-wide mb-1 flex items-center gap-1">ADF Test
                        <InfoTooltip title="ADF Test" text="The Augmented Dickey-Fuller test checks whether the spread between two assets is stationary (i.e. it tends to revert to a mean). A p-value below 0.05 is the green light for pairs trading." />
                      </div>
                      <div className="text-white font-semibold">
                        {data.cointegration_results.adf_statistic?.toFixed(3) || "N/A"}
                        <span className={`ml-2 text-xs ${(data.cointegration_results.adf_pvalue ?? 1) < 0.05 ? 'text-green-400' : 'text-red-400'}`}>
                          (p={data.cointegration_results.adf_pvalue?.toFixed(3) || "N/A"})
                        </span>
                      </div>
                    </div>
                    <div className="text-xs">
                      <div className="text-gray-500 uppercase tracking-wide mb-1 flex items-center gap-1">EG Test
                        <InfoTooltip title="Engle-Granger Cointegration" text="A statistical test that confirms whether two assets are cointegrated — i.e. they share a long-run equilibrium price relationship that they keep returning to over time. This is the core test for pairs trading eligibility." />
                      </div>
                      <div className="text-white font-semibold">
                        {data.cointegration_results.eg_is_cointegrated ? (
                          <span className="text-green-400">Cointegrated</span>
                        ) : (
                          <span className="text-red-400">Not Cointegrated</span>
                        )}
                      </div>
                    </div>
                    <div className="text-xs">
                      <div className="text-gray-500 uppercase tracking-wide mb-1 flex items-center gap-1">Half-Life
                        <InfoTooltip title="Mean-Reversion Half-Life" text="How many days it typically takes for a spread deviation to close halfway back to normal. A half-life of 10 days means your money is usually tied up for about 1–2 weeks. Shorter is generally better for active trading." />
                      </div>
                      <div className="text-white font-semibold">
                        {(data.cointegration_results as Record<string, unknown>)["half_life"] != null
                          ? Number((data.cointegration_results as Record<string, unknown>)["half_life"]).toFixed(1)
                          : "N/A"} days
                      </div>
                    </div>
                  </div>
                  <button
                    onClick={() => {
                      const s1 = getSymbolFromName(asset1);
                      const s2 = getSymbolFromName(asset2);
                      navigate(`/cointegration?asset1=${encodeURIComponent(s1 || asset1)}&asset2=${encodeURIComponent(s2 || asset2)}&view=test`);
                    }}
                    className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-500/10 hover:bg-blue-500/20 border border-blue-500/30 text-blue-400 text-sm"
                    title="View detailed cointegration analysis"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                    </svg>
                    Full Analysis
                  </button>
                </div>
              </div>
            )}
          </div>

          {/* Combined Price + Spread Charts with unified range selector */}
          {priceData.length > 0 && data.spread_data && (
            <>
              {/* Fullscreen overlay */}
              {isChartFullscreen && (
                <div className="fixed inset-0 z-[200] bg-[#0a0e27] flex flex-col">
                  {/* Fullscreen header */}
                  <div className="flex items-center justify-between px-6 py-4 border-b border-white/10 shrink-0">
                    <div>
                      <h3 className="text-lg font-semibold text-white">{asset1} / {asset2} — Price & Spread</h3>
                      <p className="text-xs text-gray-500 mt-0.5">Scroll to zoom · Drag to pan · Press Esc to exit</p>
                    </div>
                    <button
                      onClick={() => setIsChartFullscreen(false)}
                      className="p-2 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-gray-300 hover:text-white transition-all"
                      title="Exit fullscreen (Esc)"
                    >
                      <X size={18} />
                    </button>
                  </div>
                  {/* Fullscreen chart — fills remaining space */}
                  <div className="flex-1 p-4 min-h-0">
                    <SyncedCharts
                      priceData={priceData}
                      spreadData={data.spread_data}
                      asset1Name={asset1}
                      asset2Name={asset2}
                      totalHeight={window.innerHeight - 120}
                    />
                  </div>
                </div>
              )}

              {/* Normal (inline) card */}
              <div className="premium-card p-6">
                <div className="flex items-center justify-between mb-4">
                  <h3 className="text-lg font-semibold text-white">
                    Price & Spread (Unified Range)
                  </h3>
                  <button
                    onClick={() => setIsChartFullscreen(true)}
                    className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-gray-400 hover:text-white transition-all text-xs"
                    title="Expand to fullscreen"
                  >
                    <Maximize2 size={13} />
                    <span className="hidden sm:inline">Fullscreen</span>
                  </button>
                </div>
                <div className="rounded-xl overflow-hidden min-h-96">
                  <SyncedCharts
                    priceData={priceData}
                    spreadData={data.spread_data}
                    asset1Name={asset1}
                    asset2Name={asset2}
                    totalHeight={combinedHeight}
                  />
                </div>
                <div className="text-xs text-gray-500 mt-2">
                  Tip: Hover over charts to see synchronized crosshairs. Mouse wheel to zoom, drag to pan.
                </div>
              </div>
            </>
          )}

          {/* Key Statistical Metrics */}
          {data.cointegration_results && (
            <div className="premium-card p-5">
              <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4">Key Statistical Metrics</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4">
                <div className="bg-white/5 rounded-xl p-3 text-center">
                  <div className="text-xs text-gray-500 mb-1">EG P-Value</div>
                  <div className={`text-lg font-bold ${
                    (data.cointegration_results.eg_pvalue ?? 1) < 0.05 ? 'text-green-400' : 'text-yellow-400'
                  }`}>
                    {data.cointegration_results.eg_pvalue != null
                      ? data.cointegration_results.eg_pvalue.toFixed(4)
                      : 'N/A'}
                  </div>
                  <div className="text-xs text-gray-600 mt-1">
                    {(data.cointegration_results.eg_pvalue ?? 1) < 0.05 ? 'Significant' : 'Not Significant'}
                  </div>
                </div>
                <div className="bg-white/5 rounded-xl p-3 text-center">
                  <div className="text-xs text-gray-500 mb-1">Half-Life</div>
                  <div className="text-lg font-bold text-blue-400">
                    {(data.cointegration_results as Record<string, unknown>)["half_life"] != null
                      ? `${Number((data.cointegration_results as Record<string, unknown>)["half_life"]).toFixed(1)}d`
                      : 'N/A'}
                  </div>
                  <div className="text-xs text-gray-600 mt-1">Mean Reversion</div>
                </div>
                <div className="bg-white/5 rounded-xl p-3 text-center">
                  <div className="text-xs text-gray-500 mb-1">Hedge Ratio (β)</div>
                  <div className="text-lg font-bold text-purple-400">
                    {pairBeta != null ? pairBeta.toFixed(3) : 'N/A'}
                  </div>
                  <div className="text-xs text-gray-600 mt-1">Position Size</div>
                </div>
                <div className="bg-white/5 rounded-xl p-3 text-center">
                  <div className="text-xs text-gray-500 mb-1">Current Z-Score</div>
                  <div className={`text-lg font-bold ${
                    pairSignal.tone === 'red'
                      ? 'text-red-400'
                      : pairSignal.tone === 'yellow'
                        ? 'text-yellow-400'
                        : pairSignal.tone === 'blue'
                          ? 'text-blue-400'
                          : 'text-green-400'
                  }`}>
                    {currentZScore != null ? currentZScore.toFixed(2) : 'N/A'}
                  </div>
                  <div className="text-xs text-gray-600 mt-1">
                    {pairSignal.label}
                  </div>
                </div>
                <div className="bg-white/5 rounded-xl p-3 text-center">
                  <div className="text-xs text-gray-500 mb-1">Cointegrated</div>
                  <div className={`text-lg font-bold ${
                    data.cointegration_results.eg_is_cointegrated ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {data.cointegration_results.eg_is_cointegrated ? '✓ Yes' : '✗ No'}
                  </div>
                  <div className="text-xs text-gray-600 mt-1">Engle-Granger</div>
                </div>
              </div>
            </div>
          )}

          {/* Hedge Ratio Calculator */}
          {data.spread_data && (
            <HedgeRatioCalculator
              hedgeRatio={pairBeta}
              asset1Name={asset1}
              asset2Name={asset2}
              currentZScore={currentZScore}
              isCointegrated={data.cointegration_results?.eg_is_cointegrated}
            />
          )}

          {/* Unified Rolling Metrics Section */}
          <div className="premium-card p-8">
            <h3 className="text-lg font-semibold text-white mb-8">
              Risk & Performance Metrics
            </h3>

            {/* Dynamic descriptor above chart */}
            <div className="text-sm text-gray-400 mb-4">
              Rolling Metrics: <span className="text-gray-200 font-medium">{metricsAsset}</span>
              {benchmarkInfo?.name ? (
                <>
                  {" "}vs{" "}
                  <span className="text-gray-200 font-medium">{benchmarkInfo.name}</span>
                </>
              ) : null} {" "}
              (<span className="text-gray-300">{selectedWindow}d window</span>)
            </div>

            {/* Controls Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8 overflow-visible">
              <div>
                <label className="block text-sm font-medium text-gray-300 mb-2">Metrics For</label>
                <Select
                  value={metricsAsset}
                  onChange={setMetricsAsset}
                  options={ALL_ASSET_NAMES.map((n) => ({ label: n, value: n }))}
                  className="w-full"
                />
              </div>
              <BenchmarkSelector
                selected={selectedBenchmark}
                onSelect={setSelectedBenchmark}
                disabled={isLoading}
              />
              <WindowSelector
                selected={selectedWindow}
                onSelect={setSelectedWindow}
              />
            </div>

            {/* Metric Selector */}
            <div className="mb-8">
              <MetricSelector
                selected={selectedMetrics}
                onSelect={setSelectedMetrics}
                availableMetrics={["beta", "volatility", "sharpe"]}
                maxSelection={3}
              />
            </div>

            {/* Unified Metrics Chart */}
            <div className="rounded-xl overflow-hidden min-h-96" style={{ height: "550px" }}>
              {metricsLoading && <LoadingChart />}
              {!metricsLoading && metricsData && (
                <RollingMetricsChart
                  data={metricsData.data}
                  assetName={metricsAsset}
                  benchmarkName={benchmarkInfo?.name}
                  rollingWindow={selectedWindow}
                  dataSource={undefined as any}
                  cachedAt={undefined}
                  height={500}
                />
              )}
              {!metricsLoading && !metricsData && selectedMetrics.length > 0 && (
                <div className="text-center py-16 text-gray-400">
                  No metrics data available
                </div>
              )}
            </div>
          </div>

          {/* Regression and Cointegration sections removed as functionality is covered elsewhere */}

          {/* CTA Section */}
          <div className="mt-12 px-6 py-8 rounded-2xl bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/20 text-center">
            <h3 className="text-2xl font-bold text-white mb-3">
              Want Early Access to Advanced Features?
            </h3>
            <p className="text-gray-300 mb-6 max-w-xl mx-auto">
              Join our waitlist to get notified when new analysis capabilities and advanced pair metrics go live
            </p>
            <div className="flex justify-center gap-4 flex-wrap">
              <input
                type="email"
                placeholder="Enter your email"
                className="px-4 py-3 bg-white/5 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
              />
              <button className="px-6 py-3 rounded-lg bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-medium flex items-center gap-2 shadow-lg shadow-blue-500/25">
                <Mail className="h-4 w-4" />
                Join Waitlist
              </button>
            </div>
            <p className="text-xs text-gray-500 mt-4">
              No spam. Unsubscribe anytime. We respect your privacy.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
