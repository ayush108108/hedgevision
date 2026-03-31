import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { CorrelationHeatmap } from "../components/charts/CorrelationHeatmap";
import { TopPairsTable } from "../components/tables/TopPairsTable";
import { getTopPairs, getCorrelationMatrix } from "../services/correlation";
import { Layers, TrendingUp } from "lucide-react";
import { LoadingChart } from "../components/common/LoadingChart";
import { WaitlistCTA } from "../components/common/WaitlistCTA";

export function CorrelationPage() {
  const [correlationMethod, setCorrelationMethod] = useState<
    "pearson" | "spearman"
  >("pearson");
  const [viewMode, setViewMode] = useState<"sector" | "asset">("asset");

  const { data, isLoading } = useQuery({
    queryKey: ["correlation", correlationMethod, viewMode],
    queryFn: () =>
      getCorrelationMatrix({
        method: correlationMethod,
        view_mode: viewMode,
      }),
  });

  const topPairsQuery = useQuery({
    queryKey: ["top-pairs", correlationMethod],
    queryFn: () =>
      getTopPairs({
        limit: 25,
        method: correlationMethod,
        min_correlation: 0.5,
      }),
  });

  if (isLoading) {
    return <LoadingChart />;
  }

  // Defensive shape guards to avoid runtime errors when API returns unexpected payloads
  const safeAssets = Array.isArray(data?.assets) ? data!.assets : [];
  const safeMatrix =
    data && data.matrix && typeof data.matrix === "object" ? data.matrix : {};

  return (
    <div className="space-y-6 animate-in fade-in duration-500">
      {/* Page Header with Controls */}
      <div className="premium-card p-4 sm:p-6 lg:p-8">
        <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
          <div>
            <h1 className="text-2xl sm:text-3xl font-bold text-white mb-2">
              Correlation Analysis
            </h1>
            <p className="text-sm sm:text-base text-gray-400 max-w-2xl">
              Discover market relationships and identify diversification
              opportunities
            </p>
          </div>

          {/* Control Panel */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Correlation Method Toggle */}
            <div className="flex items-center gap-2 bg-slate-800/50 rounded-lg p-1 border border-slate-700/50">
              <button
                onClick={() => setCorrelationMethod("pearson")}
                className={`px-3 sm:px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 ${
                  correlationMethod === "pearson"
                    ? "bg-blue-600 text-white shadow-lg shadow-blue-600/30"
                    : "text-gray-400 hover:text-white hover:bg-slate-700/50"
                }`}
              >
                Pearson
              </button>
              <button
                onClick={() => setCorrelationMethod("spearman")}
                className={`px-3 sm:px-4 py-2 rounded-md text-sm font-medium transition-all duration-200 ${
                  correlationMethod === "spearman"
                    ? "bg-blue-600 text-white shadow-lg shadow-blue-600/30"
                    : "text-gray-400 hover:text-white hover:bg-slate-700/50"
                }`}
              >
                Spearman
              </button>
            </div>

            {/* Dive Deep Toggle */}
            <button
              onClick={() =>
                setViewMode(viewMode === "sector" ? "asset" : "sector")
              }
              className={`flex items-center gap-2 px-3 sm:px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 border ${
                viewMode === "asset"
                  ? "bg-purple-600 text-white border-purple-500 shadow-lg shadow-purple-600/30"
                  : "bg-slate-800/50 text-gray-400 border-slate-700/50 hover:text-white hover:bg-slate-700/50"
              }`}
              title={
                viewMode === "sector"
                  ? "Switch to asset-level view"
                  : "Switch to sector-level view"
              }
            >
              {viewMode === "asset" ? (
                <TrendingUp size={16} />
              ) : (
                <Layers size={16} />
              )}
              <span>{viewMode === "asset" ? "Asset View" : "Sector View"}</span>
            </button>
          </div>
        </div>

        {/* Method Description */}
        <div className="mt-4 p-3 bg-slate-800/30 rounded-lg border border-slate-700/30">
          <p className="text-sm text-gray-400">
            {correlationMethod === "pearson" ? (
              <>
                <span className="text-blue-400 font-medium">Pearson:</span>{" "}
                Measures linear relationships between assets. Best for normally
                distributed returns and detecting linear trends.
              </>
            ) : (
              <>
                <span className="text-blue-400 font-medium">Spearman:</span>{" "}
                Measures monotonic relationships using rank ordering. More
                robust to outliers and non-linear relationships.
              </>
            )}
          </p>
        </div>
      </div>

      {/* Main Content */}
      <div className="grid grid-cols-1 xl:grid-cols-[2fr_1fr] gap-6">
        {/* Heatmap Section */}
        <div className="premium-card p-4 sm:p-6 lg:p-8 min-w-0">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 mb-4 sm:mb-6">
            <h2 className="text-base sm:text-lg font-semibold text-white">
              {viewMode === "sector"
                ? "Sector Correlation Heatmap"
                : "Asset Correlation Heatmap"}
            </h2>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <div className="w-2 h-2 rounded-full bg-blue-500"></div>
              <span>
                {correlationMethod === "pearson" ? "Linear" : "Rank-based"}
              </span>
            </div>
          </div>

          {safeAssets.length >= 2 && Object.keys(safeMatrix).length > 0 ? (
            <div className="rounded-lg overflow-visible">
              <CorrelationHeatmap
                assets={safeAssets}
                matrix={safeMatrix}
                height={viewMode === "sector" ? 500 : 650}
              />
            </div>
          ) : (
            <div className="text-center py-16 text-gray-400">
              <p>No correlation data available</p>
              <p className="text-xs text-gray-500 mt-2">
                Try switching the method or view, or refresh later if precomputed
                data is populating.
              </p>
            </div>
          )}

          {/* View Mode Info */}
          <div className="mt-4 p-3 bg-slate-800/30 rounded-lg border border-slate-700/30">
            <p className="text-xs text-gray-500">
              {viewMode === "sector" ? (
                <>
                  <span className="text-purple-400 font-medium">
                    Sector View:
                  </span>{" "}
                  High-level correlation between market sectors. Toggle "Asset
                  View" to see individual asset correlations.
                </>
              ) : (
                <>
                  <span className="text-purple-400 font-medium">
                    Asset View:
                  </span>{" "}
                  Detailed correlation matrix for all individual assets. Toggle
                  "Sector View" for a simplified high-level overview.
                </>
              )}
            </p>
          </div>
        </div>

        {/* Top Pairs Sidebar */}
        <div className="premium-card p-4 sm:p-6 lg:p-8 min-w-0">
          <h2 className="text-base sm:text-lg font-semibold text-white mb-4 sm:mb-6">
            Top Correlated Pairs
            <span className="text-sm font-normal text-gray-500 ml-2">
              ({correlationMethod})
            </span>
          </h2>
          {topPairsQuery.isLoading ? (
            <div className="text-center py-12">
              <p className="text-gray-400 text-sm">Finding top pairs...</p>
            </div>
          ) : topPairsQuery.data ? (
            <TopPairsTable pairs={topPairsQuery.data} />
          ) : (
            <div className="text-center py-12 text-gray-400">
              <p className="text-sm">No pairs data</p>
            </div>
          )}
        </div>
      </div>

      <WaitlistCTA
        title="Want Early Access to Advanced Features?"
        description="Join our waitlist to get notified when new analysis capabilities and AI-powered features go live."
        sourcePage="correlation"
        sourceLabel="correlation-page-cta"
      />
    </div>
  );
}
