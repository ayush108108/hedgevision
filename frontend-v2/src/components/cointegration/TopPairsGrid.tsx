import React from "react";
import {
  Activity,
  CheckCircle2,
  AlertCircle,
  ArrowRight,
  Star,
} from "lucide-react";
import { CointegrationTestResult } from "../../services/cointegrationApi";
import { ErrorDisplay } from "../common/ErrorDisplay";
import { getDisplayAssetName } from "../../utils/pairs";

interface TopPairsGridProps {
  pairs: CointegrationTestResult[];
  isLoading: boolean;
  error?: Error | unknown;
  onPairSelect: (pair: CointegrationTestResult) => void;
  onRetry?: () => void;
}

export function TopPairsGrid({
  pairs,
  isLoading,
  error,
  onPairSelect,
  onRetry,
}: TopPairsGridProps) {
  if (error) {
    return (
      <ErrorDisplay error={error} context="Load Top Pairs" onRetry={onRetry} />
    );
  }

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[...Array(6)].map((_, i) => (
          <div
            key={i}
            className="p-6 rounded-2xl bg-white/5 border border-white/10 animate-pulse"
          >
            <div className="h-24 bg-white/5 rounded-xl" />
          </div>
        ))}
      </div>
    );
  }

  if (!pairs || pairs.length === 0) {
    return (
      <div className="p-12 text-center rounded-2xl border-2 border-dashed border-white/10 bg-white/5">
        <Activity className="w-12 h-12 text-gray-500 mx-auto mb-4" />
        <p className="text-gray-400 text-lg">No cointegrated pairs found</p>
        <p className="text-gray-500 text-sm mt-2">
          Try running a screening or adjusting filters
        </p>
      </div>
    );
  }

  const getScoreColor = (score: number) => {
    if (score >= 80) return "from-green-500 to-emerald-500";
    if (score >= 70) return "from-blue-500 to-cyan-500";
    if (score >= 60) return "from-yellow-500 to-orange-500";
    return "from-red-500 to-pink-500";
  };

  const getStrengthBadge = (strength: string | undefined) => {
    const colors = {
      very_strong: "bg-green-500/20 text-green-300 border-green-500/30",
      strong: "bg-blue-500/20 text-blue-300 border-blue-500/30",
      moderate: "bg-yellow-500/20 text-yellow-300 border-yellow-500/30",
      weak: "bg-orange-500/20 text-orange-300 border-orange-500/30",
    };
    if (!strength) return colors.moderate;
    return colors[strength as keyof typeof colors] || colors.moderate;
  };

  const getSuitabilityIcon = (suitability: string) => {
    if (suitability === "excellent" || suitability === "good") {
      return <CheckCircle2 className="w-4 h-4 text-green-400" />;
    }
    return <AlertCircle className="w-4 h-4 text-yellow-400" />;
  };

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold text-white">
          Top Cointegrated Pairs
        </h2>
        <div className="text-sm text-gray-400">
          Showing {pairs.length} pairs
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
        {pairs
          .filter((pair) => pair && pair.asset1_symbol && pair.asset2_symbol && (pair.overall_score ?? 0) > 0)
          .sort((a, b) => (b.overall_score ?? 0) - (a.overall_score ?? 0))
          .map((pair, index) => (
            <button
              key={`${pair.asset1_symbol}-${pair.asset2_symbol}-${index}`}
              onClick={() => onPairSelect(pair)}
              className="group relative p-6 rounded-2xl bg-gradient-to-br from-white/5 to-white/[0.02] border border-white/10 hover:border-white/20 hover:from-white/10 hover:to-white/5 transition-all duration-300 text-left overflow-hidden"
            >
              {/* Rank Badge */}
              {index < 3 && (
                <div className="absolute top-3 right-3">
                  <div className="p-1.5 rounded-lg bg-gradient-to-br from-yellow-500/20 to-orange-500/20 border border-yellow-500/30">
                    <Star className="w-4 h-4 text-yellow-400 fill-yellow-400" />
                  </div>
                </div>
              )}

              {/* Score Circle */}
              <div className="mb-4 flex items-center gap-4">
                <div className="relative">
                  <svg className="w-16 h-16 -rotate-90">
                    <circle
                      cx="32"
                      cy="32"
                      r="28"
                      fill="none"
                      stroke="currentColor"
                      strokeWidth="4"
                      className="text-white/10"
                    />
                    <circle
                      cx="32"
                      cy="32"
                      r="28"
                      fill="none"
                      stroke="url(#gradient)"
                      strokeWidth="4"
                      strokeLinecap="round"
                      strokeDasharray={`${(pair.overall_score / 100) * 176} 176`}
                      className="transition-all duration-1000"
                    />
                    <defs>
                      <linearGradient
                        id="gradient"
                        x1="0%"
                        y1="0%"
                        x2="100%"
                        y2="100%"
                      >
                        <stop
                          offset="0%"
                          className={`text-${getScoreColor(pair.overall_score).split("-")[1]}-400`}
                          stopColor="currentColor"
                        />
                        <stop
                          offset="100%"
                          className={`text-${getScoreColor(pair.overall_score).split("-")[3]}-400`}
                          stopColor="currentColor"
                        />
                      </linearGradient>
                    </defs>
                  </svg>
                  <div className="absolute inset-0 flex items-center justify-center">
                    <span className="text-lg font-bold text-white">
                      {Math.round(pair.overall_score)}
                    </span>
                  </div>
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="text-lg font-bold text-white truncate">
                      {getDisplayAssetName(pair.asset1_symbol) ?? pair.asset1_symbol}
                    </span>
                    <ArrowRight className="w-4 h-4 text-gray-500 flex-shrink-0" />
                    <span className="text-lg font-bold text-white truncate">
                      {getDisplayAssetName(pair.asset2_symbol) ?? pair.asset2_symbol}
                    </span>
                  </div>
                  <div
                    className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg border text-xs font-medium ${getStrengthBadge(pair.cointegration_strength)}`}
                  >
                    <span className="capitalize">
                      {pair.cointegration_strength
                        ? pair.cointegration_strength.replace("_", " ")
                        : "score pending"}
                    </span>
                  </div>
                </div>
              </div>

              {/* Metrics Grid */}
              <div className="space-y-2 mb-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Correlation</span>
                  <span className="font-medium text-white">
                    {pair.pearson_correlation?.toFixed(3) ?? "N/A"}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">P-Value</span>
                  <span
                    className={`font-medium ${pair.eg_pvalue && pair.eg_pvalue < 0.05 ? "text-green-400" : "text-yellow-400"}`}
                  >
                    {pair.eg_pvalue?.toFixed(4) ?? "N/A"}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Half-Life</span>
                  <span className="font-medium text-white">
                    {pair.half_life_days?.toFixed(1) ?? "N/A"} days
                  </span>
                </div>
              </div>

              {/* Status Footer */}
              <div className="pt-3 border-t border-white/10 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  {getSuitabilityIcon(pair.trading_suitability)}
                  <span className="text-xs text-gray-400 capitalize">
                    {pair.trading_suitability || "Awaiting full test"}
                  </span>
                </div>
                <div
                  className={`px-2 py-0.5 rounded-full text-xs font-medium ${
                    pair.eg_is_cointegrated
                      ? "bg-green-500/20 text-green-400"
                      : "bg-gray-500/20 text-gray-300"
                  }`}
                >
                  {pair.eg_is_cointegrated ? "Cointegrated" : "Needs confirmation"}
                </div>
              </div>

              {/* Hover Effect */}
              <div className="absolute inset-0 rounded-2xl bg-gradient-to-br from-blue-500/0 to-purple-500/0 group-hover:from-blue-500/10 group-hover:to-purple-500/10 transition-all duration-300 pointer-events-none" />
            </button>
          ))}
      </div>
    </div>
  );
}
