import React from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Briefcase,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Percent,
  PieChart,
} from "lucide-react";
import {
  getPortfolioMetrics,
  getPositions,
  type Position,
  type PortfolioMetrics,
} from "../services/api";

export function PortfolioPage() {
  // Fetch portfolio metrics
  const {
    data: metrics,
    isLoading: metricsLoading,
    error: metricsError,
    refetch: refetchMetrics,
  } = useQuery({
    queryKey: ["portfolioMetrics"],
    queryFn: getPortfolioMetrics,
    refetchInterval: 10000,
  });

  // Fetch open positions
  const {
    data: positions,
    isLoading: positionsLoading,
    error: positionsError,
    refetch: refetchPositions,
    isFetching,
  } = useQuery({
    queryKey: ["positions", "open"],
    queryFn: () => getPositions("open"),
    refetchInterval: 10000,
  });

  const isLoading = metricsLoading || positionsLoading;
  const hasError = metricsError || positionsError;

  const handleRefresh = () => {
    refetchMetrics();
    refetchPositions();
  };

  // Mock data
  const mockMetrics: PortfolioMetrics = {
    total_value: 12450.75,
    total_pnl: 2450.75,
    total_pnl_percent: 24.51,
    number_of_positions: 3,
    win_rate: 68.5,
    sharpe_ratio: 1.85,
    max_drawdown: -8.3,
    invested_capital: 7250.75,
    cash_balance: 5200.0,
    total_return: 24.51,
    average_win: 1350.25,
    average_loss: -580.50,
    profit_factor: 2.33,
    sortino_ratio: 2.15,
    calmar_ratio: 2.95,
  };

  const mockPositions: Position[] = [
    {
      id: "1",
      user_id: "demo_user",
      pair: "BTC-ETH",
      asset1: "BTC",
      asset2: "ETH",
      type: "long-short" as const,
      hedge_ratio: 15.2,
      entry_date: new Date().toISOString(),
      position_size: 2500.0,
      entry_spread: 0.045,
      current_spread: 0.052,
      unrealized_pnl: 175.5,
      unrealized_pnl_percent: 7.02,
      status: "open" as const,
    },
    {
      id: "2",
      user_id: "demo_user",
      pair: "SOL-AVAX",
      asset1: "SOL",
      asset2: "AVAX",
      type: "long-short" as const,
      hedge_ratio: 3.8,
      entry_date: new Date().toISOString(),
      position_size: 1800.0,
      entry_spread: 0.032,
      current_spread: 0.028,
      unrealized_pnl: -72.0,
      unrealized_pnl_percent: -4.0,
      status: "open" as const,
    },
    {
      id: "3",
      user_id: "demo_user",
      pair: "ADA-DOT",
      asset1: "ADA",
      asset2: "DOT",
      type: "short-long" as const,
      hedge_ratio: 2.1,
      entry_date: new Date().toISOString(),
      position_size: 3200.0,
      entry_spread: 0.018,
      current_spread: 0.024,
      unrealized_pnl: 192.0,
      unrealized_pnl_percent: 6.0,
      status: "open" as const,
    },
  ];

  const displayMetrics: PortfolioMetrics = metrics || mockMetrics;
  const displayPositions: Position[] = positions || mockPositions;

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat("en-US", {
      style: "currency",
      currency: "USD",
    }).format(value);
  };

  const formatPercent = (value: number) => {
    return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="flex items-center space-x-2">
          <RefreshCw className="w-6 h-6 animate-spin text-blue-500" />
          <span className="text-gray-600">Loading portfolio data...</span>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Briefcase className="w-8 h-8 text-blue-400" />
          <h1 className="text-3xl font-bold text-white">Portfolio</h1>
        </div>
        <button
          onClick={handleRefresh}
          disabled={isFetching}
          className="flex items-center space-x-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          <RefreshCw className={`w-4 h-4 ${isFetching ? "animate-spin" : ""}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* Portfolio Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {/* Total Portfolio Value */}
        <div className="bg-neutral-900/80 border border-white/10 rounded-lg p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-300">
              Total Portfolio Value
            </span>
            <DollarSign className="w-5 h-5 text-blue-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {formatCurrency(displayMetrics.total_value)}
          </div>
          <div className="mt-2 text-sm text-gray-400">
            {displayMetrics.number_of_positions} active positions
          </div>
        </div>

        {/* Unrealized P&L */}
        <div className="bg-neutral-900/80 border border-white/10 rounded-lg p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-300">
              Unrealized P&L
            </span>
            {displayMetrics.total_pnl >= 0 ? (
              <TrendingUp className="w-5 h-5 text-green-600" />
            ) : (
              <TrendingDown className="w-5 h-5 text-red-600" />
            )}
          </div>
          <div
            className={`text-2xl font-bold ${
              displayMetrics.total_pnl >= 0 ? "text-green-600" : "text-red-600"
            }`}
          >
            {formatCurrency(displayMetrics.total_pnl)}
          </div>
          <div
            className={`mt-2 text-sm ${
              displayMetrics.total_pnl >= 0 ? "text-green-600" : "text-red-600"
            }`}
          >
            {formatPercent(displayMetrics.total_pnl_percent)}
          </div>
        </div>

        {/* Win Rate */}
        <div className="bg-neutral-900/80 border border-white/10 rounded-lg p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-300">Win Rate</span>
            <Percent className="w-5 h-5 text-purple-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {displayMetrics.win_rate.toFixed(1)}%
          </div>
          <div className="mt-2 text-sm text-gray-400">
            Sharpe: {displayMetrics.sharpe_ratio.toFixed(2)}
          </div>
        </div>

        {/* Available Cash */}
        <div className="bg-neutral-900/80 border border-white/10 rounded-lg p-6">
          <div className="flex items-center justify-between mb-2">
            <span className="text-sm font-medium text-gray-300">
              Available Cash
            </span>
            <PieChart className="w-5 h-5 text-orange-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {formatCurrency(displayMetrics.cash_balance)}
          </div>
          <div className="mt-2 text-sm text-gray-400">
            Invested: {formatCurrency(displayMetrics.invested_capital)}
          </div>
        </div>
      </div>

      {/* Positions Table */}
      <div className="bg-neutral-900/80 border border-white/10 rounded-lg overflow-hidden">
        <div className="px-6 py-4 border-b border-white/10">
          <h2 className="text-xl font-semibold text-white">
            Open Positions
          </h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead className="bg-neutral-800">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Pair
                </th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Entry Date
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Position Size
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Entry Spread
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Current Spread
                </th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-300 uppercase tracking-wider">
                  Unrealized P&L
                </th>
              </tr>
            </thead>
            <tbody className="bg-neutral-900 divide-y divide-white/10">
              {displayPositions.map((position) => (
                <tr key={position.id} className="hover:bg-white/5">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center">
                      <div>
                        <div className="text-sm font-medium text-white">
                          {position.pair}
                        </div>
                        <div className="text-sm text-gray-400">
                          {position.asset1} / {position.asset2}
                        </div>
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-300">
                    {new Date(position.entry_date).toLocaleDateString()}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-white text-right">
                    {formatCurrency(position.position_size)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-white text-right">
                    {position.entry_spread.toFixed(4)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-white text-right">
                    {position.current_spread.toFixed(4)}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div
                      className={`text-sm font-medium ${
                        position.unrealized_pnl >= 0
                          ? "text-green-600"
                          : "text-red-600"
                      }`}
                    >
                      {formatCurrency(position.unrealized_pnl)}
                    </div>
                    <div
                      className={`text-xs ${
                        position.unrealized_pnl >= 0
                          ? "text-green-600"
                          : "text-red-600"
                      }`}
                    >
                      {formatPercent(position.unrealized_pnl_percent)}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* Additional Metrics Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Risk Metrics */}
        <div className="bg-neutral-900/80 border border-white/10 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            <span className="text-white">Risk Metrics</span>
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-300">Sharpe Ratio</span>
              <span className="text-sm font-medium text-white">
                {displayMetrics.sharpe_ratio.toFixed(2)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-300">Max Drawdown</span>
              <span className="text-sm font-medium text-red-600">
                {displayMetrics.max_drawdown.toFixed(2)}%
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-300">Win Rate</span>
              <span className="text-sm font-medium text-white">
                {displayMetrics.win_rate.toFixed(1)}%
              </span>
            </div>
          </div>
        </div>

        {/* Capital Allocation */}
        <div className="bg-neutral-900/80 border border-white/10 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            <span className="text-white">Capital Allocation</span>
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-300">Total Value</span>
              <span className="text-sm font-medium text-white">
                {formatCurrency(displayMetrics.total_value)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-300">Invested</span>
              <span className="text-sm font-medium text-white">
                {formatCurrency(displayMetrics.invested_capital)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-300">Available Cash</span>
              <span className="text-sm font-medium text-white">
                {formatCurrency(displayMetrics.cash_balance)}
              </span>
            </div>
          </div>
        </div>

        {/* Position Statistics */}
        <div className="bg-neutral-900/80 border border-white/10 rounded-lg p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">
            <span className="text-white">Position Statistics</span>
          </h3>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-300">Open Positions</span>
              <span className="text-sm font-medium text-white">
                {displayMetrics.number_of_positions}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-300">Total P&L</span>
              <span
                className={`text-sm font-medium ${
                  displayMetrics.total_pnl >= 0
                    ? "text-green-600"
                    : "text-red-600"
                }`}
              >
                {formatCurrency(displayMetrics.total_pnl)}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-300">P&L %</span>
              <span
                className={`text-sm font-medium ${
                  displayMetrics.total_pnl_percent >= 0
                    ? "text-green-600"
                    : "text-red-600"
                }`}
              >
                {formatPercent(displayMetrics.total_pnl_percent)}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="bg-white/5 rounded-lg p-4 text-sm text-gray-300">
        <p>
          {positions?.length
            ? "Live Portfolio Tracking Active"
            : "Demo Mode: Displaying sample portfolio data. Connect to backend API for live tracking."}
        </p>
      </div>
    </div>
  );
}
