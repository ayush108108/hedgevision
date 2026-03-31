import React, { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  Sparkles,
  TrendingUp,
  Activity,
  ChevronRight,
  RefreshCw,
  Play,
  Filter,
  Download,
  Info,
  XCircle,
  Grid3x3,
  Star,
  Mail,
} from "lucide-react";
// Removed CointegrationTestPanel per new UX: selection from Overview only
import { TopPairsGrid } from "../components/cointegration/TopPairsGrid";
import { PairTestResults } from "../components/cointegration/PairTestResults";
// Spread analysis and signals moved out of this page
import { ScreeningStatus } from "../components/cointegration/ScreeningStatus";
import { TestCategoriesHeader } from "../components/cointegration/TestCategoriesHeader";
import { getTopPairs, startScreening, testPair } from "../services/cointegrationApi";
import { addToWatchlist } from "../services/watchlist";
import { ErrorDisplay, InlineError } from "../components/common/ErrorDisplay";

export function CointegrationPage() {
  const [searchParams] = useSearchParams();
  const queryClient = useQueryClient();
  const [selectedPair, setSelectedPair] = useState<any>(null);
  const [viewMode, setViewMode] = useState<
    "overview" | "test" | "spread" | "signals"
  >("overview");
  const [selectedCategory, setSelectedCategory] = useState<
    | "overall"
    | "correlation"
    | "engle-granger"
    | "johansen"
    | "adf"
    | "phillips-perron"
    | "kpss"
    | "regression"
    | "mean-reversion"
    | "spread-stats"
    | "zscore"
    | "trading-quality"
  >("overall");
  const [screeningJobId, setScreeningJobId] = useState<string | null>(null);
  const [watchlistMessage, setWatchlistMessage] = useState<string | null>(null);

  // Fetch top cointegrated pairs
  const {
    data: topPairs,
    isLoading: loadingPairs,
    error: pairsError,
    refetch: refetchPairs,
  } = useQuery({
    queryKey: ["cointegration", "top-pairs"],
    queryFn: () =>
      getTopPairs({ limit: 50, min_score: 60.0, granularity: "daily" }),
    refetchInterval: 30000, // Refresh every 30s
    retry: 2,
  });

  // Fetch active trading signals
  // Removed: signals moved to dedicated page

  // Start screening mutation
  const startScreeningMutation = useMutation({
    mutationFn: startScreening,
    onSuccess: (data: any) => {
      setScreeningJobId(data.job_id);
      queryClient.invalidateQueries({ queryKey: ["cointegration"] });
    },
  });

  const handleStartScreening = () => {
    startScreeningMutation.mutate({
      granularity: "daily",
      lookback_days: 252,
      min_correlation: 0.7,
    });
  };

  const [isTestingPair, setIsTestingPair] = useState(false);
  const [testError, setTestError] = useState<string | null>(null);

  const handlePairSelect = async (pair: any) => {
    // Reset error state
    setTestError(null);
    setSelectedPair(pair);
    setViewMode("test");
    setSelectedCategory("overall");

    // Validate pair data
    if (!pair?.asset1_symbol || !pair?.asset2_symbol) {
      setTestError("Invalid pair data: missing asset symbols");
      return;
    }

    // Check if pair has incomplete test data (missing critical values)
    const needsFullTest = 
      pair.adf_test_statistic === null || 
      pair.adf_test_statistic === undefined ||
      pair.pp_test_statistic === null ||
      pair.pp_test_statistic === undefined ||
      pair.kpss_test_statistic === null ||
      pair.kpss_test_statistic === undefined;

    if (needsFullTest) {
      setIsTestingPair(true);
      try {
        // Run full test to populate all missing values
        const fullResults = await testPair({
          asset1: pair.asset1_symbol,
          asset2: pair.asset2_symbol,
          granularity: pair.granularity || "daily",
          lookback_days: pair.lookback_days || 252,
        });
        
        // Validate response
        if (!fullResults) {
          throw new Error("No results returned from test");
        }
        
        // Update selected pair with full results
        setSelectedPair(fullResults);
      } catch (error: any) {
        console.error("Failed to compute full test results:", error);
        
        // Set user-friendly error message
        const errorMessage = error?.message || 
                           error?.response?.data?.message || 
                           "Failed to compute test results. Please try again.";
        setTestError(errorMessage);
        
        // Keep partial results visible
      } finally {
        setIsTestingPair(false);
      }
    }
  };

  // Deep-link support: /cointegration?asset1=AAA&asset2=BBB&view=test
  useEffect(() => {
    const view = searchParams.get("view");
    const a1 = searchParams.get("asset1");
    const a2 = searchParams.get("asset2");
    if (view === "test" && a1 && a2) {
      setViewMode("test");
      setIsTestingPair(true);
      testPair({ asset1: a1, asset2: a2, granularity: "daily", lookback_days: 252 })
        .then((res) => setSelectedPair(res))
        .catch((err) => {
          console.error("Failed to fetch deep-linked test pair", err);
          setSelectedPair(null);
        })
        .finally(() => setIsTestingPair(false));
    }
  }, [searchParams]);

  const handleAddToWatchlist = () => {
    if (selectedPair?.asset1_symbol && selectedPair?.asset2_symbol) {
      addToWatchlist(
        selectedPair.asset1_symbol,
        selectedPair.asset2_symbol,
        "daily",
        `Score: ${selectedPair.overall_score}, Cointegration strength: ${selectedPair.cointegration_strength}`
      );
      // Invalidate watchlist query to reflect new additions
      queryClient.invalidateQueries({ queryKey: ["watchlist"] });
      setWatchlistMessage(`${selectedPair.asset1_symbol} / ${selectedPair.asset2_symbol} added to watchlist!`);
      setTimeout(() => setWatchlistMessage(null), 3000);
    }
  };

  const stats = {
    totalPairs:
      (topPairs as any)?.total_pairs || topPairs?.pairs?.length || 0,
    cointegrated:
      (topPairs as any)?.total_pairs || topPairs?.pairs?.length || 0, // Show total cointegrated pairs (all returned pairs pass cointegration threshold)
    avgScore: topPairs?.pairs?.length
      ? (
          topPairs.pairs.reduce(
            (sum: number, p: any) => sum + (p.overall_score || 0),
            0,
          ) / topPairs.pairs.length
        ).toFixed(1)
      : "0.0",
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900/20 to-gray-900">
      {/* Hero Header */}
      <div className="border-b border-white/10 bg-gradient-to-r from-blue-500/10 to-purple-500/10 backdrop-blur-xl">
        <div className="max-w-[1920px] mx-auto px-4 sm:px-6 py-4 sm:py-8">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="space-y-1 sm:space-y-2 min-w-0">
              <div className="flex items-center gap-2 sm:gap-3">
                <div className="p-2 sm:p-3 rounded-xl sm:rounded-2xl bg-gradient-to-br from-blue-500 to-purple-500 shadow-xl shadow-blue-500/25 shrink-0">
                  <Sparkles className="w-5 h-5 sm:w-7 sm:h-7 text-white" />
                </div>
                <div>
                  <h1 className="text-xl sm:text-3xl lg:text-4xl font-bold text-white tracking-tight">
                    Cointegration Screener
                  </h1>
                  <p className="text-blue-200/70 text-xs sm:text-base mt-0.5">
                    Advanced statistical pair analysis with 12 test categories
                  </p>
                </div>
              </div>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <button
                onClick={() => refetchPairs()}
                disabled={loadingPairs}
                className="px-3 sm:px-5 py-2 sm:py-3 rounded-xl bg-white/5 hover:bg-white/10 active:bg-white/15 border border-white/10 text-white transition-colors flex items-center gap-1.5 sm:gap-2"
              >
                <RefreshCw
                  size={15}
                  className={`${loadingPairs ? "animate-spin" : ""} transition-transform duration-500`}
                />
                <span className="text-sm font-medium">Refresh</span>
              </button>

              <button
                onClick={handleStartScreening}
                disabled={startScreeningMutation.isPending}
                className="px-3 sm:px-6 py-2 sm:py-3 rounded-xl bg-gradient-to-r from-blue-500 to-purple-500 hover:from-blue-600 hover:to-purple-600 text-white font-medium shadow-xl shadow-blue-500/25 transition-all duration-200 flex items-center gap-1.5 sm:gap-2"
              >
                {startScreeningMutation.isPending ? (
                  <>
                    <RefreshCw size={15} className="animate-spin" />
                    <span className="text-sm">Screening...</span>
                  </>
                ) : (
                  <>
                    <Play size={15} />
                    <span className="text-sm">Screen</span>
                  </>
                )}
              </button>
            </div>
          </div>

          {/* Stats Bar - dynamic: global in overview, pair-specific in test */}
          {viewMode !== "test" || !selectedPair ? (
            <div className="grid grid-cols-3 gap-2 sm:gap-4 mt-4 sm:mt-8">
              <div className="p-3 sm:p-5 rounded-xl sm:rounded-2xl bg-gradient-to-br from-blue-500/20 to-blue-600/10 border border-blue-500/30 backdrop-blur-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-blue-200/60 text-xs sm:text-sm font-medium mb-0.5 sm:mb-1">Total Pairs</div>
                    <div className="text-xl sm:text-3xl font-bold text-white">{stats.totalPairs}</div>
                  </div>
                  <div className="hidden sm:flex p-2 sm:p-3 rounded-xl bg-blue-500/20">
                    <Grid3x3 className="w-5 h-5 sm:w-6 sm:h-6 text-blue-400" />
                  </div>
                </div>
              </div>
              <div className="p-3 sm:p-5 rounded-xl sm:rounded-2xl bg-gradient-to-br from-green-500/20 to-green-600/10 border border-green-500/30 backdrop-blur-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-green-200/60 text-xs sm:text-sm font-medium mb-0.5 sm:mb-1">Cointegrated</div>
                    <div className="text-xl sm:text-3xl font-bold text-white">{stats.cointegrated}</div>
                  </div>
                  <div className="hidden sm:flex p-2 sm:p-3 rounded-xl bg-green-500/20">
                    <TrendingUp className="w-5 h-5 sm:w-6 sm:h-6 text-green-400" />
                  </div>
                </div>
              </div>
              <div className="p-3 sm:p-5 rounded-xl sm:rounded-2xl bg-gradient-to-br from-orange-500/20 to-orange-600/10 border border-orange-500/30 backdrop-blur-sm">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="text-orange-200/60 text-xs sm:text-sm font-medium mb-0.5 sm:mb-1">Avg Score</div>
                    <div className="text-xl sm:text-3xl font-bold text-white">{stats.avgScore}</div>
                  </div>
                  <div className="hidden sm:flex p-2 sm:p-3 rounded-xl bg-orange-500/20">
                    <Activity className="w-5 h-5 sm:w-6 sm:h-6 text-orange-400" />
                  </div>
                </div>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-3 gap-2 sm:gap-4 mt-4 sm:mt-8">
              <div className="p-3 sm:p-5 rounded-xl sm:rounded-2xl bg-gradient-to-br from-blue-500/20 to-blue-600/10 border border-blue-500/30 backdrop-blur-sm">
                <div className="text-blue-200/60 text-xs sm:text-sm font-medium mb-0.5">Pair</div>
                <div className="text-base sm:text-2xl font-bold text-white">{selectedPair.asset1_symbol} / {selectedPair.asset2_symbol}</div>
              </div>
              <div className="p-3 sm:p-5 rounded-xl sm:rounded-2xl bg-gradient-to-br from-green-500/20 to-green-600/10 border border-green-500/30 backdrop-blur-sm">
                <div className="text-green-200/60 text-xs sm:text-sm font-medium mb-0.5">Score</div>
                <div className="text-xl sm:text-3xl font-bold text-white">{selectedPair.overall_score?.toFixed ? selectedPair.overall_score.toFixed(1) : selectedPair.overall_score || "-"}</div>
              </div>
              <div className="p-3 sm:p-5 rounded-xl sm:rounded-2xl bg-gradient-to-br from-orange-500/20 to-orange-600/10 border border-orange-500/30 backdrop-blur-sm">
                <div className="text-orange-200/60 text-xs sm:text-sm font-medium mb-0.5">EG Test</div>
                <div className="text-sm sm:text-2xl font-bold text-white">{selectedPair.eg_is_cointegrated ? "Cointegrated" : "Not Cointegrated"}</div>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Screening Status Banner */}
      {screeningJobId && (
        <div className="max-w-[1920px] mx-auto px-6 py-4">
          <ScreeningStatus
            jobId={screeningJobId}
            onComplete={() => setScreeningJobId(null)}
          />
        </div>
      )}

        {/* Test Categories Header - Only show in Test mode */}
        {viewMode === "test" && (
          <TestCategoriesHeader
            selected={
              [
                "overall",
                "correlation",
                "engle-granger",
                "johansen",
                "adf",
                "phillips-perron",
                "kpss",
              ].includes(selectedCategory)
                ? (selectedCategory as any)
                : "overall"
            }
            onSelect={(c) => setSelectedCategory(c)}
          />
        )}

      {/* Main Content */}
      <div className="max-w-[1920px] mx-auto px-6 py-6">
        {/* View Mode Tabs */}
        <div className="mb-6 flex items-center gap-2 p-1.5 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-sm w-fit">
          {[
            { id: "overview", label: "Overview", icon: Grid3x3 },
            { id: "test", label: "Test Pair", icon: Activity },
          ].map((mode) => (
            <button
              key={mode.id}
              onClick={() => setViewMode(mode.id as any)}
              className={`px-5 py-2.5 rounded-xl font-medium transition-all duration-200 flex items-center gap-2 ${
                viewMode === mode.id
                  ? "bg-gradient-to-r from-blue-500 to-purple-500 text-white shadow-lg shadow-blue-500/25"
                  : "text-gray-400 hover:text-white hover:bg-white/5"
              }`}
            >
              <mode.icon size={18} />
              <span>{mode.label}</span>
            </button>
          ))}
        </div>

        {/* Content Area */}
        <div className="grid grid-cols-12 gap-6">
          {viewMode === "overview" && (
            <>
              {/* Top Pairs Grid */}
              <div className="col-span-12">
                <TopPairsGrid
                  pairs={topPairs?.pairs || []}
                  isLoading={loadingPairs}
                  onPairSelect={handlePairSelect}
                />
              </div>
            </>
          )}

          {viewMode === "test" && (
            <div className="col-span-12 space-y-4">
              {/* Error Banner */}
              {testError && (
                <div className="p-4 rounded-xl bg-red-500/10 border border-red-500/30 flex items-start gap-3">
                  <div className="flex-shrink-0">
                    <XCircle className="w-5 h-5 text-red-400" />
                  </div>
                  <div className="flex-1">
                    <h4 className="text-sm font-semibold text-red-300 mb-1">
                      Test Computation Failed
                    </h4>
                    <p className="text-sm text-red-200/80">{testError}</p>
                  </div>
                  <button
                    onClick={() => setTestError(null)}
                    className="flex-shrink-0 text-red-400 hover:text-red-300"
                    title="Dismiss error"
                    aria-label="Dismiss error message"
                  >
                    <XCircle className="w-5 h-5" />
                  </button>
                </div>
              )}

              {/* Watchlist Success Message */}
              {watchlistMessage && (
                <div className="p-4 rounded-xl bg-green-500/10 border border-green-500/30 flex items-start gap-3 animate-pulse">
                  <div className="flex-shrink-0">
                    <Star className="w-5 h-5 text-green-400 fill-green-400" />
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-green-200">{watchlistMessage}</p>
                  </div>
                  <button
                    onClick={() => setWatchlistMessage(null)}
                    className="flex-shrink-0 text-green-400 hover:text-green-300"
                    title="Dismiss"
                  >
                    <XCircle className="w-5 h-5" />
                  </button>
                </div>
              )}

              {/* Test Results */}
              {isTestingPair ? (
                <div className="h-full flex items-center justify-center p-12 rounded-2xl border border-white/10 bg-white/5">
                  <div className="text-center space-y-3">
                    <RefreshCw className="w-12 h-12 text-blue-400 mx-auto animate-spin" />
                    <p className="text-white text-lg font-medium">
                      Computing Full Test Results...
                    </p>
                    <p className="text-gray-400 text-sm">
                      Running comprehensive analysis across 12 test categories
                    </p>
                  </div>
                </div>
              ) : selectedPair ? (
                <>
                  <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-semibold text-white">Test Results: {selectedPair.asset1_symbol} / {selectedPair.asset2_symbol}</h3>
                    <button
                      onClick={handleAddToWatchlist}
                      className="px-4 py-2 rounded-xl bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600 text-white font-medium shadow-lg shadow-yellow-500/25 hover:shadow-yellow-500/40 transition-all duration-200 flex items-center gap-2"
                    >
                      <Star className="w-4 h-4" />
                      <span>Add to Watchlist</span>
                    </button>
                  </div>
                  <PairTestResults
                    testResult={selectedPair}
                    selectedCategory={selectedCategory as any}
                  />
                </>
              ) : (
                <div className="h-full flex items-center justify-center p-12 rounded-2xl border-2 border-dashed border-white/10 bg-white/5">
                  <div className="text-center space-y-3">
                    <Info className="w-12 h-12 text-gray-500 mx-auto" />
                    <p className="text-gray-400 text-lg">
                      Select a pair from Overview to view test results
                    </p>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Spread analysis and signals moved to dedicated pages */}
        </div>

        {/* CTA Section */}
        <div className="mt-12 px-6 py-8 rounded-2xl bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/20 text-center">
          <h3 className="text-2xl font-bold text-white mb-3">
            Want Early Access to Advanced Features?
          </h3>
          <p className="text-gray-300 mb-6 max-w-xl mx-auto">
            Join our waitlist to get notified when new screening capabilities and AI-powered features go live
          </p>
          <div className="flex justify-center gap-4 flex-wrap">
            <input
              type="email"
              placeholder="Enter your email"
              className="px-4 py-3 bg-white/5 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
            />
            <button className="px-6 py-3 rounded-lg bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-medium transition-all flex items-center gap-2 shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40">
              <Mail className="h-4 w-4" />
              Join Waitlist
            </button>
          </div>
          <p className="text-xs text-gray-500 mt-4">
            No spam. Unsubscribe anytime. We respect your privacy.
          </p>
        </div>
      </div>
    </div>
  );
}

 
