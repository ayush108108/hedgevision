import React from "react";
import { TrendingUp, Activity, Award, TrendingDown, AlertTriangle, BarChart3, Zap, Waves, GitMerge } from "lucide-react";
import type { MetricType } from "../../services/rollingMetrics";

export interface MetricOption {
  id: MetricType;
  name: string;
  description: string;
  icon: React.ReactNode;
  color: string;
  unit: string;
  format: (value: number) => string;
}

export const METRIC_OPTIONS: MetricOption[] = [
  {
    id: "beta",
    name: "Beta",
    description: "Market correlation coefficient",
    icon: <TrendingUp className="w-4 h-4" />,
    color: "#8b5cf6",
    unit: "",
    format: (v) => v.toFixed(3),
  },
  {
    id: "volatility",
    name: "Volatility",
    description: "Annualized price volatility",
    icon: <Activity className="w-4 h-4" />,
    color: "#3b82f6",
    unit: "%",
    format: (v) => (v * 100).toFixed(2) + "%",
  },
  {
    id: "sharpe",
    name: "Sharpe Ratio",
    description: "Risk-adjusted return",
    icon: <Award className="w-4 h-4" />,
    color: "#10b981",
    unit: "",
    format: (v) => v.toFixed(3),
  },
  {
    id: "sortino",
    name: "Sortino Ratio",
    description: "Downside risk-adjusted return",
    icon: <TrendingDown className="w-4 h-4" />,
    color: "#06b6d4",
    unit: "",
    format: (v) => v.toFixed(3),
  },
  {
    id: "max_drawdown",
    name: "Max Drawdown",
    description: "Largest peak-to-trough decline",
    icon: <AlertTriangle className="w-4 h-4" />,
    color: "#ef4444",
    unit: "%",
    format: (v) => (v * 100).toFixed(2) + "%",
  },
  {
    id: "var_95",
    name: "VaR (95%)",
    description: "Value at Risk at 95% confidence",
    icon: <BarChart3 className="w-4 h-4" />,
    color: "#f59e0b",
    unit: "%",
    format: (v) => (v * 100).toFixed(2) + "%",
  },
  {
    id: "cvar_95",
    name: "CVaR (95%)",
    description: "Conditional Value at Risk",
    icon: <Zap className="w-4 h-4" />,
    color: "#f97316",
    unit: "%",
    format: (v) => (v * 100).toFixed(2) + "%",
  },
  {
    id: "hurst",
    name: "Hurst Exponent",
    description: "Mean reversion indicator",
    icon: <Waves className="w-4 h-4" />,
    color: "#ec4899",
    unit: "",
    format: (v) => v.toFixed(3),
  },
];

interface Props {
  selected: MetricType[];
  onSelect: (metrics: MetricType[]) => void;
  availableMetrics?: MetricType[];
  disabled?: boolean;
  maxSelection?: number;
}

export function MetricSelector({
  selected,
  onSelect,
  availableMetrics = ["beta", "volatility"],
  disabled = false,
  maxSelection = 3,
}: Props) {
  const handleToggle = (metricId: MetricType) => {
    if (selected.includes(metricId)) {
      // Remove metric
      onSelect(selected.filter((m) => m !== metricId));
    } else {
      // Add metric (respect max selection)
      if (selected.length < maxSelection) {
        onSelect([...selected, metricId]);
      }
    }
  };

  // Filter to only show available metrics
  const options = METRIC_OPTIONS.filter((opt) =>
    availableMetrics.includes(opt.id)
  );

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-gray-400">
          Select Metrics ({selected.length}/{maxSelection})
        </span>
        {selected.length > 0 && (
          <button
            onClick={() => onSelect([])}
            disabled={disabled}
            className="text-xs text-blue-400 hover:text-blue-300 transition-colors"
          >
            Clear All
          </button>
        )}
      </div>

      <div className="grid grid-cols-2 gap-2">
        {options.map((metric) => {
          const isSelected = selected.includes(metric.id);
          const isDisabled = disabled || (!isSelected && selected.length >= maxSelection);

          return (
            <button
              key={metric.id}
              onClick={() => handleToggle(metric.id)}
              disabled={isDisabled}
              className={`
                flex items-start gap-3 p-3 rounded-lg border transition-all duration-200
                ${
                  isSelected
                    ? "bg-opacity-20 border-opacity-50"
                    : "bg-slate-800/50 border-slate-700/50 hover:bg-slate-700/50 hover:border-slate-600/50"
                }
                ${isDisabled && !isSelected ? "opacity-40 cursor-not-allowed" : "cursor-pointer"}
              `}
              style={{
                backgroundColor: isSelected ? `${metric.color}20` : undefined,
                borderColor: isSelected ? `${metric.color}80` : undefined,
              }}
            >
              <div
                className="flex-shrink-0 mt-0.5"
                style={{ color: isSelected ? metric.color : undefined }}
              >
                {metric.icon}
              </div>
              <div className="flex-1 text-left min-w-0">
                <div
                  className="text-sm font-medium"
                  style={{ color: isSelected ? metric.color : undefined }}
                >
                  {metric.name}
                </div>
                <div className="text-xs text-gray-500 mt-0.5 truncate">
                  {metric.description}
                </div>
              </div>
            </button>
          );
        })}
      </div>

      {selected.length === 0 && (
        <div className="text-center py-4 text-gray-500 text-sm">
          Select up to {maxSelection} metrics to display
        </div>
      )}
    </div>
  );
}

// Helper function to get metric option by ID
export function getMetricOption(id: MetricType): MetricOption | undefined {
  return METRIC_OPTIONS.find((opt) => opt.id === id);
}
