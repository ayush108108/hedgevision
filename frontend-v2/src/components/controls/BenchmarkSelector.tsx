import React from "react";
import { Bitcoin, TrendingUp, DollarSign } from "lucide-react";

export interface Benchmark {
  id: string;
  name: string;
  symbol: string; // Database symbol
  displaySymbol: string; // Display ticker
  icon: React.ReactNode;
  color: string;
}

export const BENCHMARKS: Benchmark[] = [
  {
    id: "spy",
    name: "S&P 500",
    symbol: "SPY.US",
    displaySymbol: "SPY",
    icon: <TrendingUp className="w-4 h-4" />,
    color: "#3b82f6",
  },
  {
    id: "gold",
    name: "Gold",
    symbol: "GLD.US",
    displaySymbol: "GLD",
    icon: <DollarSign className="w-4 h-4" />,
    color: "#f59e0b",
  },
  {
    id: "btc",
    name: "Bitcoin",
    symbol: "BTC-USD.CC",
    displaySymbol: "BTC",
    icon: <Bitcoin className="w-4 h-4" />,
    color: "#f97316",
  },
];

interface Props {
  selected: string;
  onSelect: (benchmarkId: string) => void;
  disabled?: boolean;
}

export function BenchmarkSelector({ selected, onSelect, disabled = false }: Props) {
  return (
    <div className="flex items-center gap-3">
      <span className="text-sm font-medium text-gray-400">
        Compare with:
      </span>
      <div className="flex gap-2">
        {BENCHMARKS.map((benchmark) => {
          const isSelected = selected === benchmark.id;
          return (
            <button
              key={benchmark.id}
              onClick={() => onSelect(benchmark.id)}
              disabled={disabled}
              className={`
                flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium
                transition-all duration-200 border
                ${
                  isSelected
                    ? "bg-blue-500/20 border-blue-500/50 text-blue-400"
                    : "bg-slate-800/50 border-slate-700/50 text-gray-400 hover:bg-slate-700/50 hover:border-slate-600/50"
                }
                ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
              `}
              style={{
                borderColor: isSelected ? benchmark.color + "80" : undefined,
                backgroundColor: isSelected ? benchmark.color + "20" : undefined,
                color: isSelected ? benchmark.color : undefined,
              }}
            >
              <span style={{ color: isSelected ? benchmark.color : undefined }}>
                {benchmark.icon}
              </span>
              <span>{benchmark.displaySymbol}</span>
            </button>
          );
        })}
      </div>
    </div>
  );
}

// Helper function to get benchmark by ID
export function getBenchmarkById(id: string): Benchmark | undefined {
  return BENCHMARKS.find((b) => b.id === id);
}

// Helper function to get benchmark symbol for API calls
export function getBenchmarkSymbol(id: string): string {
  const benchmark = getBenchmarkById(id);
  return benchmark?.symbol || "SPY.US";
}
