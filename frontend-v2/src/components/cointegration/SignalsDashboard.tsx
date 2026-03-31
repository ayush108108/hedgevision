import React from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  TrendingUp,
  TrendingDown,
  X,
  CheckCircle2,
  Clock,
  DollarSign,
  Zap,
  Target,
  AlertCircle,
} from "lucide-react";
import { updateSignal } from "../../services/cointegrationApi";

interface Signal {
  signal_id: string;
  pair_trade_id: string;
  asset1_symbol: string;
  asset2_symbol: string;
  signal_type: "long" | "short" | "exit" | "hold";
  signal_strength: number;
  signal_date: string;
  entry_zscore: number;
  current_zscore: number;
  entry_threshold: number;
  exit_threshold: number;
  stop_loss_threshold: number;
  position_size_pct: number;
  expected_hold_days: number;
  status: "active" | "filled" | "exited" | "cancelled";
  fill_price_asset1?: number;
  fill_price_asset2?: number;
  exit_price_asset1?: number;
  exit_price_asset2?: number;
  pnl?: number;
  pnl_pct?: number;
  created_at: string;
}

interface SignalsDashboardProps {
  signals: Signal[];
  isLoading: boolean;
}

export function SignalsDashboard({
  signals,
  isLoading,
}: SignalsDashboardProps) {
  const queryClient = useQueryClient();

  const updateSignalMutation = useMutation({
    mutationFn: ({
      signalId,
      status,
      fillPrice,
      exitPrice,
    }: {
      signalId: string;
      status: string;
      fillPrice?: number;
      exitPrice?: number;
    }) => updateSignal(signalId, status, fillPrice, exitPrice),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cointegration", "signals"] });
    },
  });

  if (isLoading) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {[...Array(6)].map((_, i) => (
          <div
            key={i}
            className="p-6 rounded-2xl bg-white/5 border border-white/10 animate-pulse"
          >
            <div className="h-32 bg-white/5 rounded-xl" />
          </div>
        ))}
      </div>
    );
  }

  if (!signals || signals.length === 0) {
    return (
      <div className="p-12 text-center rounded-2xl border-2 border-dashed border-white/10 bg-white/5">
        <Zap className="w-12 h-12 text-gray-500 mx-auto mb-4" />
        <p className="text-gray-400 text-lg">No active signals</p>
        <p className="text-gray-500 text-sm mt-2">
          Signals will appear when trading opportunities are detected
        </p>
      </div>
    );
  }

  const getSignalIcon = (type: string) => {
    switch (type) {
      case "long":
        return <TrendingUp className="w-5 h-5 text-green-400" />;
      case "short":
        return <TrendingDown className="w-5 h-5 text-red-400" />;
      case "exit":
        return <Target className="w-5 h-5 text-blue-400" />;
      default:
        return <Clock className="w-5 h-5 text-gray-400" />;
    }
  };

  const getSignalColor = (type: string) => {
    switch (type) {
      case "long":
        return "from-green-500/20 to-emerald-500/20 border-green-500/30";
      case "short":
        return "from-red-500/20 to-pink-500/20 border-red-500/30";
      case "exit":
        return "from-blue-500/20 to-cyan-500/20 border-blue-500/30";
      default:
        return "from-gray-500/20 to-gray-600/20 border-gray-500/30";
    }
  };

  const getStatusBadge = (status: string) => {
    const styles = {
      active: "bg-blue-500/20 text-blue-300 border-blue-500/30",
      filled: "bg-green-500/20 text-green-300 border-green-500/30",
      exited: "bg-gray-500/20 text-gray-300 border-gray-500/30",
      cancelled: "bg-red-500/20 text-red-300 border-red-500/30",
    };
    return styles[status as keyof typeof styles] || styles.active;
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-blue-500/30">
              <Zap className="w-6 h-6 text-blue-400" />
            </div>
            Trading Signals
          </h2>
          <p className="text-gray-400 mt-1">
            {signals.length} active signal{signals.length !== 1 ? "s" : ""}
          </p>
        </div>
      </div>

      {/* Signals Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {signals
          .filter(
            (signal) => signal && signal.asset1_symbol && signal.asset2_symbol,
          )
          .map((signal) => (
            <div
              key={signal.signal_id}
              className={`p-6 rounded-2xl bg-gradient-to-br ${getSignalColor(signal.signal_type)} border relative overflow-hidden group`}
            >
              {/* Status Badge */}
              <div className="absolute top-3 right-3">
                <div
                  className={`px-2.5 py-1 rounded-lg border text-xs font-medium ${getStatusBadge(signal.status)}`}
                >
                  {signal.status?.toUpperCase() ?? "UNKNOWN"}
                </div>
              </div>

              {/* Signal Header */}
              <div className="flex items-center gap-3 mb-4">
                <div className="p-2 rounded-lg bg-white/10">
                  {getSignalIcon(signal.signal_type)}
                </div>
                <div className="flex-1">
                  <div className="text-lg font-bold text-white">
                    {signal.asset1_symbol} / {signal.asset2_symbol}
                  </div>
                  <div className="text-sm text-gray-400 capitalize">
                    {signal.signal_type} Signal
                  </div>
                </div>
              </div>

              {/* Signal Strength */}
              <div className="mb-4">
                <div className="flex items-center justify-between text-sm mb-1">
                  <span className="text-gray-400">Signal Strength</span>
                  <span className="font-medium text-white">
                    {Math.round(signal.signal_strength)}%
                  </span>
                </div>
                <div className="h-2 bg-white/10 rounded-full overflow-hidden relative">
                  <div
                    className="absolute inset-y-0 left-0 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full transition-all duration-500"
                    style={{
                      width: `${Math.min(100, Math.max(0, signal.signal_strength))}%`,
                    }}
                  />
                </div>
              </div>

              {/* Metrics */}
              <div className="space-y-2 mb-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Entry Z-Score</span>
                  <span className="font-medium text-white">
                    {signal.entry_zscore.toFixed(2)}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Current Z-Score</span>
                  <span
                    className={`font-medium ${
                      Math.abs(signal.current_zscore) > 2
                        ? "text-red-400"
                        : Math.abs(signal.current_zscore) > 1
                          ? "text-yellow-400"
                          : "text-green-400"
                    }`}
                  >
                    {signal.current_zscore.toFixed(2)}
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Position Size</span>
                  <span className="font-medium text-white">
                    {signal.position_size_pct.toFixed(1)}%
                  </span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-gray-400">Expected Hold</span>
                  <span className="font-medium text-white">
                    {signal.expected_hold_days} days
                  </span>
                </div>
              </div>

              {/* P&L (if filled) */}
              {signal.status === "filled" && signal.pnl !== undefined && (
                <div
                  className={`p-3 rounded-lg border mb-4 ${
                    signal.pnl > 0
                      ? "bg-green-500/10 border-green-500/30"
                      : "bg-red-500/10 border-red-500/30"
                  }`}
                >
                  <div className="flex items-center gap-2 mb-1">
                    <DollarSign
                      className={`w-4 h-4 ${signal.pnl > 0 ? "text-green-400" : "text-red-400"}`}
                    />
                    <span className="text-xs text-gray-400">Current P&L</span>
                  </div>
                  <div
                    className={`text-lg font-bold ${signal.pnl > 0 ? "text-green-300" : "text-red-300"}`}
                  >
                    {signal.pnl > 0 ? "+" : ""}
                    {signal.pnl.toFixed(2)} ({signal.pnl_pct?.toFixed(2)}%)
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2">
                {signal.status === "active" && (
                  <button
                    onClick={() =>
                      updateSignalMutation.mutate({
                        signalId: signal.signal_id,
                        status: "filled",
                      })
                    }
                    disabled={updateSignalMutation.isPending}
                    className="flex-1 py-2 px-3 rounded-lg bg-green-500 hover:bg-green-600 text-white text-sm font-medium transition-all flex items-center justify-center gap-2"
                  >
                    <CheckCircle2 className="w-4 h-4" />
                    Fill
                  </button>
                )}
                {signal.status === "filled" && (
                  <button
                    onClick={() =>
                      updateSignalMutation.mutate({
                        signalId: signal.signal_id,
                        status: "exited",
                      })
                    }
                    disabled={updateSignalMutation.isPending}
                    className="flex-1 py-2 px-3 rounded-lg bg-blue-500 hover:bg-blue-600 text-white text-sm font-medium transition-all flex items-center justify-center gap-2"
                  >
                    <Target className="w-4 h-4" />
                    Exit
                  </button>
                )}
                {(signal.status === "active" || signal.status === "filled") && (
                  <button
                    onClick={() =>
                      updateSignalMutation.mutate({
                        signalId: signal.signal_id,
                        status: "cancelled",
                      })
                    }
                    disabled={updateSignalMutation.isPending}
                    className="py-2 px-3 rounded-lg bg-red-500/20 hover:bg-red-500/30 text-red-300 text-sm font-medium transition-all flex items-center justify-center gap-2"
                    title="Cancel signal"
                    aria-label="Cancel signal"
                  >
                    <X className="w-4 h-4" />
                  </button>
                )}
              </div>

              {/* Timestamp */}
              <div className="mt-3 pt-3 border-t border-white/10 text-xs text-gray-500">
                {new Date(signal.signal_date).toLocaleString()}
              </div>
            </div>
          ))}
      </div>
    </div>
  );
}
