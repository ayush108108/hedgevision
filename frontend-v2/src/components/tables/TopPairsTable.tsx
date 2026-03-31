import React, { useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import type { TopPair } from "../../types";
import {
  FinancialColors,
  getCorrelationColor,
} from "../../themes/financial-colors";
import { useDebounce } from "../../hooks/useDebounce";
import {
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  TrendingUp,
  TrendingDown,
  Filter,
  Search,
  ExternalLink,
  Download,
} from "lucide-react";

interface Props {
  pairs: TopPair[];
  minCorrelation?: number;
  loading?: boolean;
  error?: string | null;
  onPairSelect?: (asset1: string, asset2: string) => void;
  showActions?: boolean;
}

type SortField =
  | "rank"
  | "asset1"
  | "asset2"
  | "correlation"
  | "absCorrelation";
type SortDirection = "asc" | "desc";

export const TopPairsTable: React.FC<Props> = ({
  pairs,
  minCorrelation = 0.7,
  loading = false,
  error = null,
  onPairSelect,
  showActions = true,
}) => {
  const navigate = useNavigate();
  const [sortField, setSortField] = useState<SortField>("absCorrelation");
  const [sortDirection, setSortDirection] = useState<SortDirection>("desc");
  const [searchTerm, setSearchTerm] = useState("");
  const [filterType, setFilterType] = useState<"all" | "positive" | "negative">(
    "all",
  );

  // Debounce search term for performance (prevents excessive re-renders)
  const debouncedSearchTerm = useDebounce(searchTerm, 300);

  // Sorting logic with debounced search
  const sortedPairs = useMemo(() => {
    let filtered = [...pairs];

    // Apply search filter (using debounced value)
    if (debouncedSearchTerm) {
      const term = debouncedSearchTerm.toLowerCase();
      filtered = filtered.filter(
        (p) =>
          p.asset1.toLowerCase().includes(term) ||
          p.asset2.toLowerCase().includes(term),
      );
    }

    // Apply correlation type filter
    if (filterType === "positive") {
      filtered = filtered.filter((p) => p.correlation > 0);
    } else if (filterType === "negative") {
      filtered = filtered.filter((p) => p.correlation < 0);
    }

    // Apply sorting
    filtered.sort((a, b) => {
      let aVal: any, bVal: any;

      switch (sortField) {
        case "asset1":
          aVal = a.asset1;
          bVal = b.asset1;
          break;
        case "asset2":
          aVal = a.asset2;
          bVal = b.asset2;
          break;
        case "correlation":
          aVal = a.correlation;
          bVal = b.correlation;
          break;
        case "absCorrelation":
          aVal = Math.abs(a.correlation);
          bVal = Math.abs(b.correlation);
          break;
        default:
          return 0;
      }

      if (typeof aVal === "string") {
        return sortDirection === "asc"
          ? aVal.localeCompare(bVal)
          : bVal.localeCompare(aVal);
      }

      return sortDirection === "asc" ? aVal - bVal : bVal - aVal;
    });

    return filtered;
  }, [pairs, debouncedSearchTerm, filterType, sortField, sortDirection]);

  const handleSort = (field: SortField) => {
    if (sortField === field) {
      setSortDirection(sortDirection === "asc" ? "desc" : "asc");
    } else {
      setSortField(field);
      setSortDirection("desc");
    }
  };

  const handlePairClick = (asset1: string, asset2: string) => {
    if (onPairSelect) {
      onPairSelect(asset1, asset2);
    } else {
      navigate(`/pair-analysis?asset1=${asset1}&asset2=${asset2}&metric=correlation`);
    }
  };

  const exportToCSV = () => {
    const headers = [
      "Rank",
      "Asset 1",
      "Asset 2",
      "Correlation",
      "Abs Correlation",
    ];
    const rows = sortedPairs.map((p, i) => [
      i + 1,
      p.asset1,
      p.asset2,
      p.correlation.toFixed(3),
      Math.abs(p.correlation).toFixed(3),
    ]);

    const csv = [headers.join(","), ...rows.map((row) => row.join(","))].join(
      "\n",
    );

    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `top-pairs-${new Date().toISOString().split("T")[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const SortIcon = ({ field }: { field: SortField }) => {
    if (sortField !== field) {
      return <ArrowUpDown size={14} className="opacity-40" />;
    }
    return sortDirection === "asc" ? (
      <ArrowUp size={14} className="text-blue-400" />
    ) : (
      <ArrowDown size={14} className="text-blue-400" />
    );
  };

  const getStrengthBadge = (correlation: number) => {
    const abs = Math.abs(correlation);
    if (abs >= 0.9) {
      return {
        text: "Very Strong",
        color: "bg-green-500/20 text-green-400 border-green-500/50",
      };
    } else if (abs >= 0.7) {
      return {
        text: "Strong",
        color: "bg-blue-500/20 text-blue-400 border-blue-500/50",
      };
    } else if (abs >= 0.5) {
      return {
        text: "Moderate",
        color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/50",
      };
    }
    return {
      text: "Weak",
      color: "bg-slate-500/20 text-slate-400 border-slate-500/50",
    };
  };

  // Loading state
  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <div className="relative w-16 h-16">
          <div className="absolute inset-0 border-4 border-slate-700 rounded-full"></div>
          <div className="absolute inset-0 border-4 border-blue-500 rounded-full border-t-transparent animate-spin"></div>
        </div>
        <p className="mt-4 text-slate-400 font-medium">Loading top pairs...</p>
        <p className="mt-1 text-slate-500 text-sm">Analyzing correlations</p>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="p-6 bg-red-900/20 border border-red-500/50 rounded-lg">
        <div className="flex items-start gap-3">
          <div className="flex-shrink-0 w-10 h-10 bg-red-500/20 rounded-full flex items-center justify-center">
            <span className="text-red-400 text-xl">⚠</span>
          </div>
          <div>
            <p className="text-red-400 font-semibold text-lg">
              Error loading pairs
            </p>
            <p className="text-red-300 text-sm mt-1">{error}</p>
          </div>
        </div>
      </div>
    );
  }

  // Empty state
  if (!pairs.length) {
    return (
      <div className="flex flex-col items-center justify-center py-16">
        <div className="w-16 h-16 bg-slate-700/50 rounded-full flex items-center justify-center mb-4">
          <TrendingUp size={32} className="text-slate-500" />
        </div>
        <p className="text-slate-400 font-medium text-lg">No pairs found</p>
        <p className="text-slate-500 text-sm mt-1">
          No pairs with |correlation| &gt; {minCorrelation}
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Controls Bar */}
      <div className="flex flex-col sm:flex-row gap-3 items-start sm:items-center justify-between">
        {/* Search */}
        <div className="relative flex-1 max-w-xs">
          <Search
            size={18}
            className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400"
          />
          <input
            type="text"
            placeholder="Search assets..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            className="w-full pl-10 pr-4 py-2 bg-slate-700/50 border border-slate-600/50 rounded-lg
                     text-slate-200 placeholder-slate-500
                     focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-blue-500/50
                     transition-all duration-200"
          />
        </div>

        {/* Filter & Export */}
        <div className="flex gap-2">
          {/* Filter Buttons */}
          <div className="flex gap-1 bg-slate-700/50 rounded-lg p-1 border border-slate-600/50">
            <button
              onClick={() => setFilterType("all")}
              className={`px-3 py-1.5 rounded text-sm font-medium transition-all duration-200 ${
                filterType === "all"
                  ? "bg-blue-500 text-white"
                  : "text-slate-400 hover:text-slate-300"
              }`}
            >
              All
            </button>
            <button
              onClick={() => setFilterType("positive")}
              className={`px-3 py-1.5 rounded text-sm font-medium transition-all duration-200 flex items-center gap-1 ${
                filterType === "positive"
                  ? "bg-green-500 text-white"
                  : "text-slate-400 hover:text-slate-300"
              }`}
            >
              <TrendingUp size={14} />
              Positive
            </button>
            <button
              onClick={() => setFilterType("negative")}
              className={`px-3 py-1.5 rounded text-sm font-medium transition-all duration-200 flex items-center gap-1 ${
                filterType === "negative"
                  ? "bg-red-500 text-white"
                  : "text-slate-400 hover:text-slate-300"
              }`}
            >
              <TrendingDown size={14} />
              Negative
            </button>
          </div>

          {/* Export Button */}
          <button
            onClick={exportToCSV}
            className="px-3 py-2 bg-slate-700/50 hover:bg-slate-600/50 border border-slate-600/50 
                     hover:border-blue-500/50 rounded-lg text-slate-300 hover:text-white
                     transition-all duration-200 flex items-center gap-2"
            title="Export to CSV"
          >
            <Download size={16} />
            <span className="hidden sm:inline text-sm font-medium">Export</span>
          </button>
        </div>
      </div>

      {/* Results Count */}
      <div className="flex items-center gap-2 text-sm text-slate-400">
        <Filter size={14} />
        <span>
          Showing{" "}
          <strong className="text-slate-300">{sortedPairs.length}</strong> of{" "}
          <strong className="text-slate-300">{pairs.length}</strong> pairs
        </span>
      </div>

      {/* Table Container */}
      <div className="overflow-x-auto rounded-lg border border-slate-700/50">
        <div className="max-h-[600px] overflow-y-auto">
          <table className="w-full text-sm">
            {/* Header */}
            <thead className="sticky top-0 z-10 bg-slate-800/95 backdrop-blur-sm border-b border-slate-700/50">
              <tr>
                <th className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider">
                  #
                </th>
                <th
                  className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider
                           cursor-pointer hover:bg-slate-700/50 transition-colors group"
                  onClick={() => handleSort("asset1")}
                >
                  <div className="flex items-center gap-2">
                    Asset 1
                    <SortIcon field="asset1" />
                  </div>
                </th>
                <th
                  className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider
                           cursor-pointer hover:bg-slate-700/50 transition-colors group"
                  onClick={() => handleSort("asset2")}
                >
                  <div className="flex items-center gap-2">
                    Asset 2
                    <SortIcon field="asset2" />
                  </div>
                </th>
                <th
                  className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider
                           cursor-pointer hover:bg-slate-700/50 transition-colors group"
                  onClick={() => handleSort("correlation")}
                >
                  <div className="flex items-center gap-2">
                    Correlation
                    <SortIcon field="correlation" />
                  </div>
                </th>
                <th
                  className="px-4 py-3 text-left text-xs font-semibold text-slate-400 uppercase tracking-wider
                           cursor-pointer hover:bg-slate-700/50 transition-colors group"
                  onClick={() => handleSort("absCorrelation")}
                >
                  <div className="flex items-center gap-2">
                    Strength
                    <SortIcon field="absCorrelation" />
                  </div>
                </th>
                {showActions && (
                  <th className="px-4 py-3 text-right text-xs font-semibold text-slate-400 uppercase tracking-wider">
                    Actions
                  </th>
                )}
              </tr>
            </thead>

            {/* Body */}
            <tbody className="divide-y divide-slate-700/30">
              {sortedPairs.map((pair, index) => {
                const strength = getStrengthBadge(pair.correlation);
                const absCorr = Math.abs(pair.correlation);

                return (
                  <tr
                    key={`${pair.asset1}-${pair.asset2}`}
                    className="bg-slate-800/40 hover:bg-slate-700/50 transition-colors cursor-pointer group"
                    onClick={() => handlePairClick(pair.asset1, pair.asset2)}
                  >
                    {/* Rank */}
                    <td className="px-4 py-3 text-slate-500 font-medium">
                      {index + 1}
                    </td>

                    {/* Asset 1 */}
                    <td className="px-4 py-3">
                      <span className="text-slate-200 font-semibold group-hover:text-blue-400 transition-colors">
                        {pair.asset1}
                      </span>
                    </td>

                    {/* Asset 2 */}
                    <td className="px-4 py-3">
                      <span className="text-slate-200 font-semibold group-hover:text-blue-400 transition-colors">
                        {pair.asset2}
                      </span>
                    </td>

                    {/* Correlation Value */}
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        {pair.correlation > 0 ? (
                          <TrendingUp size={16} className="text-green-400" />
                        ) : (
                          <TrendingDown size={16} className="text-red-400" />
                        )}
                        <span
                          className="font-mono font-semibold"
                          style={{
                            color: getCorrelationColor(pair.correlation || 0),
                          }}
                        >
                          {pair.correlation?.toFixed(3) ?? "N/A"}
                        </span>
                      </div>
                    </td>

                    {/* Strength Badge */}
                    <td className="px-4 py-3">
                      <div className="flex flex-col gap-1">
                        <span
                          className={`inline-flex items-center px-2 py-1 rounded-md text-xs font-semibold border ${strength.color}`}
                        >
                          {strength.text}
                        </span>
                        <span className="text-xs text-slate-500 font-mono">
                          |{absCorr?.toFixed(3) ?? "N/A"}|
                        </span>
                      </div>
                    </td>

                    {/* Actions */}
                    {showActions && (
                      <td className="px-4 py-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            handlePairClick(pair.asset1, pair.asset2);
                          }}
                          className="inline-flex items-center gap-1.5 px-3 py-1.5 
                                   bg-blue-500/20 hover:bg-blue-500/30 
                                   text-blue-400 hover:text-blue-300
                                   border border-blue-500/50 hover:border-blue-400/50
                                   rounded-md text-xs font-medium
                                   transition-all duration-200
                                   opacity-0 group-hover:opacity-100"
                        >
                          Analyze
                          <ExternalLink size={12} />
                        </button>
                      </td>
                    )}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Footer Stats */}
      {sortedPairs.length > 0 && (
        <div className="flex items-center justify-between text-xs text-slate-500 pt-2">
          <div className="flex items-center gap-4">
            <span>
              Avg:{" "}
              <strong className="text-slate-400">
                {(
                  sortedPairs.reduce(
                    (sum, p) => sum + (p.correlation || 0),
                    0,
                  ) / sortedPairs.length
                ).toFixed(3)}
              </strong>
            </span>
            <span>
              Max:{" "}
              <strong className="text-slate-400">
                {Math.max(
                  ...sortedPairs.map((p) => p.correlation || 0),
                ).toFixed(3)}
              </strong>
            </span>
            <span>
              Min:{" "}
              <strong className="text-slate-400">
                {Math.min(
                  ...sortedPairs.map((p) => p.correlation || 0),
                ).toFixed(3)}
              </strong>
            </span>
          </div>
          <div className="text-slate-500">Click any row to analyze pair</div>
        </div>
      )}
    </div>
  );
};
