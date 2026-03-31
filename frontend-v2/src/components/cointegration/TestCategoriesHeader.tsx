import React from "react";
import { Activity, TrendingUp, BarChart3, Waves, LineChart, Maximize2, Repeat, BarChart2, Zap, Award } from "lucide-react";

type HeaderCategory =
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
  | "trading-quality";

interface TestCategoriesHeaderProps {
  selected?: HeaderCategory;
  onSelect?: (category: HeaderCategory) => void;
}

export function TestCategoriesHeader({ selected = "overall", onSelect }: TestCategoriesHeaderProps) {
  const categories = [
    {
      id: "overall",
      icon: Activity,
      title: "Overall Assessment",
      description: "Composite score and summary",
      color: "blue",
    },
    {
      id: "correlation",
      icon: TrendingUp,
      title: "Correlation Metrics",
      description: "Pearson, Spearman coefficients",
      color: "purple",
    },
    {
      id: "engle-granger",
      icon: Waves,
      title: "Engle-Granger Test",
      description: "Residual cointegration analysis",
      color: "green",
    },
    {
      id: "johansen",
      icon: BarChart3,
      title: "Johansen Test",
      description: "Multivariate cointegration",
      color: "orange",
    },
    {
      id: "adf",
      icon: LineChart,
      title: "ADF Test",
      description: "Augmented Dickey-Fuller stationarity",
      color: "cyan",
    },
    {
      id: "phillips-perron",
      icon: Waves,
      title: "Phillips-Perron Test",
      description: "Non-parametric stationarity",
      color: "pink",
    },
    {
      id: "kpss",
      icon: TrendingUp,
      title: "KPSS Test",
      description: "Trend stationarity verification",
      color: "indigo",
    },
    {
      id: "regression",
      icon: Maximize2,
      title: "Linear Regression",
      description: "OLS regression analysis",
      color: "emerald",
    },
    {
      id: "mean-reversion",
      icon: Repeat,
      title: "Mean Reversion",
      description: "Half-life and Hurst exponent",
      color: "teal",
    },
    {
      id: "spread-stats",
      icon: BarChart2,
      title: "Spread Statistics",
      description: "Distribution metrics",
      color: "violet",
    },
    {
      id: "zscore",
      icon: Zap,
      title: "Z-Score Analysis",
      description: "Entry/exit signal thresholds",
      color: "yellow",
    },
    {
      id: "trading-quality",
      icon: Award,
      title: "Trading Quality",
      description: "Sharpe ratio and performance",
      color: "rose",
    },
  ];

  const colorStyles: Record<string, string> = {
    blue: "bg-blue-500/10 border-blue-500/30 text-blue-300",
    purple: "bg-purple-500/10 border-purple-500/30 text-purple-300",
    green: "bg-green-500/10 border-green-500/30 text-green-300",
    orange: "bg-orange-500/10 border-orange-500/30 text-orange-300",
    cyan: "bg-cyan-500/10 border-cyan-500/30 text-cyan-300",
    pink: "bg-pink-500/10 border-pink-500/30 text-pink-300",
    indigo: "bg-indigo-500/10 border-indigo-500/30 text-indigo-300",
    emerald: "bg-emerald-500/10 border-emerald-500/30 text-emerald-300",
    teal: "bg-teal-500/10 border-teal-500/30 text-teal-300",
    violet: "bg-violet-500/10 border-violet-500/30 text-violet-300",
    yellow: "bg-yellow-500/10 border-yellow-500/30 text-yellow-300",
    rose: "bg-rose-500/10 border-rose-500/30 text-rose-300",
  };

  return (
    <div className="border-b border-white/10 bg-gradient-to-r from-gray-900/50 to-gray-900/30 backdrop-blur-sm">
      <div className="max-w-[1920px] mx-auto px-6 py-4">
        <div className="mb-3">
          <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider">
            Test Categories
          </h3>
          <p className="text-xs text-gray-500 mt-1">
            12 comprehensive test categories for pair cointegration analysis
          </p>
        </div>
        
        {/* Row 1: Core Statistical Tests (7) */}
        <div className="mb-3">
          <p className="text-xs text-gray-400 font-medium mb-2">Core Statistical Tests</p>
          <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
            {categories.slice(0, 7).map((category) => {
              const Icon = category.icon;
              const isActive = selected === (category.id as HeaderCategory);
              return (
                <div
                  key={category.id}
                  onClick={() => onSelect?.(category.id as HeaderCategory)}
                  className={`p-3 rounded-xl border ${colorStyles[category.color]} transition-all hover:scale-105 cursor-pointer ${isActive ? "ring-2 ring-offset-0 ring-white/30" : ""}`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <Icon className="w-4 h-4" />
                    <div className="text-xs font-semibold truncate">
                      {category.title}
                    </div>
                  </div>
                  <div className="text-[10px] opacity-70 truncate">
                    {category.description}
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Row 2: Trading & Analysis Metrics (5) */}
        <div>
          <p className="text-xs text-gray-400 font-medium mb-2">Trading & Analysis Metrics</p>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            {categories.slice(7, 12).map((category) => {
              const Icon = category.icon;
              const isActive = selected === (category.id as HeaderCategory);
              return (
                <div
                  key={category.id}
                  onClick={() => onSelect?.(category.id as HeaderCategory)}
                  className={`p-3 rounded-xl border ${colorStyles[category.color]} transition-all hover:scale-105 cursor-pointer ${isActive ? "ring-2 ring-offset-0 ring-white/30" : ""}`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <Icon className="w-4 h-4" />
                    <div className="text-xs font-semibold truncate">
                      {category.title}
                    </div>
                  </div>
                  <div className="text-[10px] opacity-70 truncate">
                    {category.description}
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
