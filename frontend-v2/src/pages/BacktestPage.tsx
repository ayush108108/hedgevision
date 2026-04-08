import React, { useState } from "react";
import { useMutation } from "@tanstack/react-query";
import {
  Zap,
  Play,
  TrendingUp,
  TrendingDown,
  BarChart3,
  ChevronDown,
  ChevronUp,
  XCircle,
  AlertTriangle,
} from "lucide-react";
import {
  runBacktest,
  BacktestRequest,
  BacktestResult,
  BacktestAPIError,
} from "../services/backtestApi";

const DEFAULTS: Required<Omit<BacktestRequest, "symbol1" | "symbol2">> = {
  lookback_days: 365,
  initial_capital: 10000,
  position_size: 0.1,
  transaction_cost: 0.001,
  slippage: 0.0005,
  entry_threshold: 2.0,
  exit_threshold: 0.5,
  stop_loss_threshold: 3.0,
  max_holding_period: 30,
  granularity: "daily",
};

type FormState = BacktestRequest & typeof DEFAULTS;

function fmt(n: number | null | undefined, decimals = 2): string {
  if (n == null) return "N/A";
  return n.toFixed(decimals);
}

function fmtPct(n: number | null | undefined): string {
  if (n == null) return "N/A";
  return `${(n * 100).toFixed(2)}%`;
}

function fmtUsd(n: number | null | undefined): string {
  if (n == null) return "N/A";
  return `$${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function MetricCard({
  label,
  value,
  positive,
}: {
  label: string;
  value: string;
  positive?: boolean | null;
}) {
  const color =
    positive == null
      ? "text-white"
      : positive
        ? "text-green-400"
        : "text-red-400";
  return (
    <div className="premium-card p-5">
      <p className="text-xs text-gray-400 uppercase tracking-wider mb-1">{label}</p>
      <p className={`text-2xl font-bold ${color}`}>{value}</p>
    </div>
  );
}

export function BacktestPage() {
  const [symbol1, setSymbol1] = useState("");
  const [symbol2, setSymbol2] = useState("");
  const [params, setParams] = useState<typeof DEFAULTS>({ ...DEFAULTS });
  const [advanced, setAdvanced] = useState(false);

  const mutation = useMutation<BacktestResult, BacktestAPIError | Error, BacktestRequest>({
    mutationFn: runBacktest,
  });

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    mutation.mutate({ symbol1: symbol1.trim().toUpperCase(), symbol2: symbol2.trim().toUpperCase(), ...params });
  }

  function setParam<K extends keyof typeof DEFAULTS>(key: K, value: (typeof DEFAULTS)[K]) {
    setParams((prev) => ({ ...prev, [key]: value }));
  }

  const result = mutation.data;
  const metrics = result?.metrics;

  const equityCurveEntries = result
    ? Object.entries(result.equity_curve).sort(([a], [b]) => a.localeCompare(b))
    : [];
  const firstCapital = equityCurveEntries[0]?.[1];
  const lastCapital = equityCurveEntries[equityCurveEntries.length - 1]?.[1];

  const recentTrades = result?.trades.slice(-10).reverse() ?? [];

  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Header */}
      <div className="premium-card p-8">
        <div className="flex items-center gap-4 mb-2">
          <div className="p-3 bg-blue-500/10 rounded-lg">
            <Zap className="h-7 w-7 text-blue-400" />
          </div>
          <div>
            <h1 className="text-3xl font-bold text-white">Backtesting Engine</h1>
            <p className="text-gray-400 mt-0.5">
              Test pair trading strategies against historical data
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">
        {/* Form */}
        <div className="lg:col-span-2">
          <form onSubmit={handleSubmit} className="premium-card p-6 space-y-5">
            <h2 className="text-lg font-semibold text-white">Configuration</h2>

            <div className="space-y-1">
              <label className="block text-sm text-gray-400">Symbol 1</label>
              <input
                className="w-full bg-white/5 border border-gray-700 rounded-lg px-3 py-2 text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 uppercase"
                placeholder="e.g. AAPL"
                value={symbol1}
                onChange={(e) => setSymbol1(e.target.value)}
                required
                maxLength={20}
              />
            </div>

            <div className="space-y-1">
              <label className="block text-sm text-gray-400">Symbol 2</label>
              <input
                className="w-full bg-white/5 border border-gray-700 rounded-lg px-3 py-2 text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 uppercase"
                placeholder="e.g. MSFT"
                value={symbol2}
                onChange={(e) => setSymbol2(e.target.value)}
                required
                maxLength={20}
              />
            </div>

            <div className="space-y-1">
              <label className="block text-sm text-gray-400">Lookback Days</label>
              <input
                type="number"
                min={30}
                max={1460}
                className="w-full bg-white/5 border border-gray-700 rounded-lg px-3 py-2 text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                value={params.lookback_days}
                onChange={(e) => setParam("lookback_days", Number(e.target.value))}
              />
            </div>

            <div className="space-y-1">
              <label className="block text-sm text-gray-400">Initial Capital ($)</label>
              <input
                type="number"
                min={100}
                step={100}
                className="w-full bg-white/5 border border-gray-700 rounded-lg px-3 py-2 text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                value={params.initial_capital}
                onChange={(e) => setParam("initial_capital", Number(e.target.value))}
              />
            </div>

            {/* Advanced toggle */}
            <button
              type="button"
              className="flex items-center gap-1 text-sm text-gray-400 hover:text-gray-200 transition-colors"
              onClick={() => setAdvanced((v) => !v)}
            >
              {advanced ? <ChevronUp className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
              Advanced Parameters
            </button>

            {advanced && (
              <div className="space-y-4 border-t border-gray-700 pt-4">
                {([
                  ["Entry Threshold (Z)", "entry_threshold", 0.1, 5, 0.1],
                  ["Exit Threshold (Z)", "exit_threshold", 0, 3, 0.1],
                  ["Stop Loss (Z)", "stop_loss_threshold", 0.5, 6, 0.1],
                  ["Max Holding Period (bars)", "max_holding_period", 1, 252, 1],
                  ["Position Size", "position_size", 0.01, 10, 0.01],
                  ["Transaction Cost", "transaction_cost", 0, 0.05, 0.0001],
                  ["Slippage", "slippage", 0, 0.05, 0.0001],
                ] as const).map(([label, key, min, max, step]) => (
                  <div key={key} className="space-y-1">
                    <label className="block text-sm text-gray-400">{label}</label>
                    <input
                      type="number"
                      min={min}
                      max={max}
                      step={step}
                      className="w-full bg-white/5 border border-gray-700 rounded-lg px-3 py-2 text-white focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                      value={params[key as keyof typeof DEFAULTS] as number}
                      onChange={(e) =>
                        setParam(key as keyof typeof DEFAULTS, Number(e.target.value) as never)
                      }
                    />
                  </div>
                ))}
              </div>
            )}

            <button
              type="submit"
              disabled={mutation.isPending}
              className="premium-button w-full flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <Play className="h-4 w-4" />
              {mutation.isPending ? "Running..." : "Run Backtest"}
            </button>
          </form>
        </div>

        {/* Results */}
        <div className="lg:col-span-3 space-y-6">
          {mutation.isError && (
            <div className="premium-card p-4 border border-red-500/30 bg-red-500/5 flex items-start gap-3">
              <XCircle className="h-5 w-5 text-red-400 flex-shrink-0 mt-0.5" />
              <div>
                <p className="text-red-400 font-medium">Backtest failed</p>
                <p className="text-gray-400 text-sm mt-1">{mutation.error?.message}</p>
              </div>
            </div>
          )}

          {!result && !mutation.isPending && !mutation.isError && (
            <div className="premium-card p-12 text-center">
              <BarChart3 className="h-16 w-16 text-gray-600 mx-auto mb-4" />
              <p className="text-gray-400">Configure a pair and run the backtest to see results here.</p>
            </div>
          )}

          {mutation.isPending && (
            <div className="premium-card p-12 text-center">
              <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4" />
              <p className="text-gray-400">Running backtest...</p>
            </div>
          )}

          {result && metrics && (
            <>
              {/* Metrics grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                <MetricCard
                  label="Total Return"
                  value={fmtPct(metrics.total_return)}
                  positive={metrics.total_return >= 0}
                />
                <MetricCard
                  label="Final Capital"
                  value={fmtUsd(metrics.final_capital)}
                  positive={metrics.final_capital >= metrics.initial_capital}
                />
                <MetricCard label="Trade Count" value={String(metrics.trade_count)} />
                <MetricCard
                  label="Win Rate"
                  value={fmtPct(metrics.win_rate)}
                  positive={metrics.win_rate != null ? metrics.win_rate >= 0.5 : null}
                />
                <MetricCard
                  label="Max Drawdown"
                  value={fmtPct(metrics.max_drawdown)}
                  positive={metrics.max_drawdown == null || metrics.max_drawdown > -0.15}
                />
                <MetricCard
                  label="Avg Trade P&L"
                  value={fmtUsd(metrics.average_trade)}
                  positive={metrics.average_trade != null ? metrics.average_trade >= 0 : null}
                />
              </div>

              {/* Equity summary */}
              {equityCurveEntries.length > 0 && (
                <div className="premium-card p-5">
                  <h3 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">Equity Curve</h3>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-400">
                      Start: <span className="text-white font-medium">{fmtUsd(firstCapital)}</span>
                    </span>
                    <span className="text-gray-400">
                      End:{" "}
                      <span
                        className={`font-medium ${
                          lastCapital != null && firstCapital != null && lastCapital >= firstCapital
                            ? "text-green-400"
                            : "text-red-400"
                        }`}
                      >
                        {fmtUsd(lastCapital)}
                      </span>
                    </span>
                    <span className="text-gray-400">
                      Periods: <span className="text-white font-medium">{equityCurveEntries.length}</span>
                    </span>
                  </div>
                </div>
              )}

              {/* Warning if no trades */}
              {metrics.trade_count === 0 && (
                <div className="premium-card p-4 border border-yellow-500/30 bg-yellow-500/5 flex items-start gap-3">
                  <AlertTriangle className="h-5 w-5 text-yellow-400 flex-shrink-0 mt-0.5" />
                  <p className="text-yellow-300 text-sm">
                    No trades were triggered with the current thresholds. Try lowering the entry threshold.
                  </p>
                </div>
              )}

              {/* Trades table */}
              {recentTrades.length > 0 && (
                <div className="premium-card p-5">
                  <h3 className="text-sm font-semibold text-gray-300 mb-3 uppercase tracking-wider">
                    Recent Trades{recentTrades.length < result.trades.length ? ` (last ${recentTrades.length} of ${result.trades.length})` : ""}
                  </h3>
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-left text-gray-500 border-b border-gray-700">
                          <th className="pb-2 pr-4">Entry</th>
                          <th className="pb-2 pr-4">Exit</th>
                          <th className="pb-2 pr-4">Type</th>
                          <th className="pb-2 pr-4">P&L</th>
                          <th className="pb-2">Reason</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-gray-800">
                        {recentTrades.map((trade, i) => (
                          <tr key={i} className="text-gray-300 hover:bg-white/5">
                            <td className="py-2 pr-4 text-gray-400">{trade.entry_date?.slice(0, 10)}</td>
                            <td className="py-2 pr-4 text-gray-400">{trade.exit_date?.slice(0, 10)}</td>
                            <td className="py-2 pr-4">
                              {trade.position_type === "long" ? (
                                <span className="flex items-center gap-1 text-green-400">
                                  <TrendingUp className="h-3 w-3" /> Long
                                </span>
                              ) : (
                                <span className="flex items-center gap-1 text-red-400">
                                  <TrendingDown className="h-3 w-3" /> Short
                                </span>
                              )}
                            </td>
                            <td
                              className={`py-2 pr-4 font-medium ${
                                trade.pnl >= 0 ? "text-green-400" : "text-red-400"
                              }`}
                            >
                              {trade.pnl >= 0 ? "+" : ""}
                              {fmtUsd(trade.pnl)}
                            </td>
                            <td className="py-2 text-gray-500 text-xs">{trade.exit_reason}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}
