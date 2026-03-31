import React, { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import {
  Play,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Settings,
  TrendingUp,
} from "lucide-react";
import { testPair, TestPairRequest, getTopPairs } from "../../services/cointegrationApi";

interface CointegrationTestPanelProps {
  onTestComplete: (result: any) => void;
}

export function CointegrationTestPanel({
  onTestComplete,
}: CointegrationTestPanelProps) {
  const [asset1, setAsset1] = useState("");
  const [asset2, setAsset2] = useState("");
  const [lookbackDays, setLookbackDays] = useState(252);
  const [granularity, setGranularity] = useState<"daily" | "intraday">("daily");
  const [showAdvanced, setShowAdvanced] = useState(false);

  // Fetch currently cointegrated pairs from precomputed results
  const { data: topPairsData, isLoading: loadingPairs } = useQuery({
    queryKey: ["cointegration", "top-pairs-for-testing"],
    queryFn: () => getTopPairs({ limit: 50, min_score: 60.0, granularity: "daily" }),
    staleTime: 5 * 60 * 1000, // Cache for 5 minutes
    refetchInterval: 60000, // Refresh every minute
  });

  // Extract unique asset symbols from cointegrated pairs
  const availableAssets = React.useMemo(() => {
    if (!topPairsData?.pairs) return [];
    const assetsSet = new Set<string>();
    topPairsData.pairs.forEach((pair: any) => {
      if (pair.asset1_symbol) assetsSet.add(pair.asset1_symbol.replace(".US", ""));
      if (pair.asset2_symbol) assetsSet.add(pair.asset2_symbol.replace(".US", ""));
    });
    return Array.from(assetsSet).sort();
  }, [topPairsData]);

  // Mutation for testing pair
  const testMutation = useMutation({
    mutationFn: (request: TestPairRequest) => testPair(request),
    onSuccess: (data) => {
      onTestComplete(data);
    },
  });

  const handleTest = () => {
    if (!asset1 || !asset2) return;

    testMutation.mutate({
      asset1: asset1?.toUpperCase() ?? "",
      asset2: asset2?.toUpperCase() ?? "",
      lookback_days: lookbackDays,
      granularity,
    });
  };

  const isValid =
    asset1.trim().length > 0 && asset2.trim().length > 0 && asset1 !== asset2;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-blue-500/30">
              <TrendingUp className="w-6 h-6 text-blue-400" />
            </div>
            Test Pair Cointegration
          </h2>
          <p className="text-gray-400 mt-1">
            Deep dive into cointegration tests for currently screened pairs
          </p>
        </div>
        <button
          onClick={() => setShowAdvanced(!showAdvanced)}
          className="p-2 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 hover:border-white/20 transition-all"
          title="Toggle advanced options"
          aria-label="Toggle advanced options"
        >
          <Settings
            className={`w-5 h-5 text-gray-400 transition-transform ${showAdvanced ? "rotate-90" : ""}`}
          />
        </button>
      </div>

      {/* Main Form */}
      <div className="p-6 rounded-2xl bg-gradient-to-br from-white/5 to-white/[0.02] border border-white/10 space-y-6">
        {/* Asset Selection */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Asset 1 */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-300">
              Asset 1 (Long)
            </label>
            {loadingPairs ? (
              <div className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-gray-500 flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Loading cointegrated pairs...
              </div>
            ) : (
              <select
                value={asset1}
                onChange={(e) => setAsset1(e.target.value)}
                className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all"
                disabled={testMutation.isPending || availableAssets.length === 0}
              >
                <option value="" className="bg-gray-900">Select asset...</option>
                {availableAssets.map((symbol) => (
                  <option key={symbol} value={symbol} className="bg-gray-900">
                    {symbol}
                  </option>
                ))}
              </select>
            )}
            <p className="text-xs text-gray-500">
              {availableAssets.length > 0 
                ? `${availableAssets.length} cointegrated assets available`
                : "No cointegrated pairs found"}
            </p>
          </div>

          {/* Asset 2 */}
          <div className="space-y-2">
            <label className="block text-sm font-medium text-gray-300">
              Asset 2 (Short)
            </label>
            {loadingPairs ? (
              <div className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-gray-500 flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Loading cointegrated pairs...
              </div>
            ) : (
              <select
                value={asset2}
                onChange={(e) => setAsset2(e.target.value)}
                className="w-full px-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white focus:outline-none focus:ring-2 focus:ring-purple-500 focus:border-transparent transition-all"
                disabled={testMutation.isPending || availableAssets.length === 0}
              >
                <option value="" className="bg-gray-900">Select asset...</option>
                {availableAssets.map((symbol) => (
                  <option key={symbol} value={symbol} className="bg-gray-900">
                    {symbol}
                  </option>
                ))}
              </select>
            )}
            <p className="text-xs text-gray-500">
              {availableAssets.length > 0 
                ? `${availableAssets.length} cointegrated assets available`
                : "No cointegrated pairs found"}
            </p>
          </div>
        </div>

        {/* Advanced Options */}
        {showAdvanced && (
          <div className="pt-6 border-t border-white/10 space-y-6 animate-in fade-in slide-in-from-top-4 duration-300">
            {/* Lookback Period */}
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <label className="block text-sm font-medium text-gray-300">
                  Lookback Period
                </label>
                <span className="text-sm font-medium text-white">
                  {lookbackDays} days
                </span>
              </div>
              <input
                type="range"
                min="30"
                max="756"
                step="30"
                value={lookbackDays}
                onChange={(e) => setLookbackDays(Number(e.target.value))}
                className="w-full h-2 bg-white/10 rounded-lg appearance-none cursor-pointer accent-blue-500"
                disabled={testMutation.isPending}
                title={`Lookback period: ${lookbackDays} days`}
                aria-label="Lookback period slider"
              />
              <div className="flex justify-between text-xs text-gray-500">
                <span>30d (1M)</span>
                <span>126d (6M)</span>
                <span>252d (1Y)</span>
                <span>504d (2Y)</span>
                <span>756d (3Y)</span>
              </div>
            </div>

            {/* Granularity */}
            <div className="space-y-2">
              <label className="block text-sm font-medium text-gray-300">
                Data Granularity
              </label>
              <div className="grid grid-cols-2 gap-3">
                <button
                  onClick={() => setGranularity("daily")}
                  className={`p-3 rounded-xl border transition-all ${
                    granularity === "daily"
                      ? "bg-blue-500/20 border-blue-500 text-blue-300"
                      : "bg-white/5 border-white/10 text-gray-400 hover:bg-white/10 hover:border-white/20"
                  }`}
                  disabled={testMutation.isPending}
                >
                  <div className="font-medium">Daily</div>
                  <div className="text-xs opacity-70">End-of-day prices</div>
                </button>
                <button
                  onClick={() => setGranularity("intraday")}
                  className={`p-3 rounded-xl border transition-all ${
                    granularity === "intraday"
                      ? "bg-purple-500/20 border-purple-500 text-purple-300"
                      : "bg-white/5 border-white/10 text-gray-400 hover:bg-white/10 hover:border-white/20"
                  }`}
                  disabled={testMutation.isPending}
                >
                  <div className="font-medium">Intraday</div>
                  <div className="text-xs opacity-70">4-hour candles</div>
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Validation Messages */}
        {asset1 && asset2 && asset1 === asset2 && (
          <div className="flex items-center gap-2 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span className="text-sm">Please select two different assets</span>
          </div>
        )}

        {/* Test Button */}
        <button
          onClick={handleTest}
          disabled={!isValid || testMutation.isPending}
          className={`w-full py-4 rounded-xl font-medium text-white transition-all duration-300 flex items-center justify-center gap-3 ${
            isValid && !testMutation.isPending
              ? "bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 shadow-lg hover:shadow-xl"
              : "bg-gray-700 cursor-not-allowed opacity-50"
          }`}
        >
          {testMutation.isPending ? (
            <>
              <Loader2 className="w-5 h-5 animate-spin" />
              Running Statistical Tests...
            </>
          ) : (
            <>
              <Play className="w-5 h-5" />
              Run Cointegration Test
            </>
          )}
        </button>

        {/* Success Message */}
        {testMutation.isSuccess && (
          <div className="flex items-center gap-2 p-4 rounded-xl bg-green-500/10 border border-green-500/30 text-green-300 animate-in fade-in slide-in-from-bottom-4">
            <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
            <span className="text-sm">
              Test completed successfully! View results below.
            </span>
          </div>
        )}

        {/* Error Message */}
        {testMutation.isError && (
          <div className="flex items-center gap-2 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 animate-in fade-in slide-in-from-bottom-4">
            <AlertCircle className="w-5 h-5 flex-shrink-0" />
            <span className="text-sm">
              {testMutation.error instanceof Error
                ? testMutation.error.message
                : "Test failed. Please try again."}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
