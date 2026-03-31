import React from "react";
import {
  TrendingUp,
  Activity,
  BarChart3,
  Target,
  Zap,
  Mail,
} from "lucide-react";

export function BacktestPage() {
  return (
    <div className="space-y-8 animate-in fade-in duration-500">
      {/* Hero Section */}
      <div className="premium-card p-12 text-center">
        <div className="flex justify-center mb-6">
          <div className="p-4 bg-blue-500/10 rounded-full">
            <Zap className="h-16 w-16 text-blue-400" />
          </div>
        </div>

        <h1 className="text-4xl font-bold text-white mb-4">
          Backtesting Engine
        </h1>
        <div className="inline-block px-4 py-2 bg-yellow-500/10 border border-yellow-500/30 rounded-full text-yellow-400 text-sm font-medium mb-6">
          Coming Soon
        </div>

        <p className="text-xl text-gray-300 max-w-2xl mx-auto mb-8">
          Professional-grade backtesting for pair trading strategies with
          detailed performance analytics and risk metrics
        </p>

        <div className="flex justify-center gap-4">
          <button className="premium-button flex items-center gap-2">
            <Mail className="h-4 w-4" />
            Get Notified When Live
          </button>
          <a
            href="https://github.com/correlatex/hedgevision"
            target="_blank"
            rel="noopener noreferrer"
            className="px-6 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-white font-medium transition-all flex items-center gap-2"
          >
            View Documentation
          </a>
        </div>
      </div>

      {/* Features Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div className="premium-card p-6">
          <div className="p-3 bg-green-500/10 rounded-lg w-fit mb-4">
            <BarChart3 className="h-6 w-6 text-green-400" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">
            Historical Strategy Testing
          </h3>
          <p className="text-gray-400 text-sm">
            Test your pair trading strategies against years of historical data
            with configurable parameters and entry/exit rules
          </p>
        </div>

        <div className="premium-card p-6">
          <div className="p-3 bg-blue-500/10 rounded-lg w-fit mb-4">
            <TrendingUp className="h-6 w-6 text-blue-400" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">
            Monte Carlo Simulations
          </h3>
          <p className="text-gray-400 text-sm">
            Run thousands of simulated scenarios to understand strategy
            robustness and potential outcomes under varying market conditions
          </p>
        </div>

        <div className="premium-card p-6">
          <div className="p-3 bg-purple-500/10 rounded-lg w-fit mb-4">
            <Activity className="h-6 w-6 text-purple-400" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">
            Walk-Forward Optimization
          </h3>
          <p className="text-gray-400 text-sm">
            Avoid overfitting with walk-forward analysis that validates strategy
            parameters on out-of-sample data
          </p>
        </div>

        <div className="premium-card p-6">
          <div className="p-3 bg-red-500/10 rounded-lg w-fit mb-4">
            <Target className="h-6 w-6 text-red-400" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">
            Transaction Cost Modeling
          </h3>
          <p className="text-gray-400 text-sm">
            Accurate P&L calculations including slippage, commissions, and
            market impact for realistic performance estimates
          </p>
        </div>

        <div className="premium-card p-6">
          <div className="p-3 bg-amber-500/10 rounded-lg w-fit mb-4">
            <BarChart3 className="h-6 w-6 text-amber-400" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">
            Risk Metrics Calculation
          </h3>
          <p className="text-gray-400 text-sm">
            Comprehensive risk analysis including Sharpe ratio, maximum
            drawdown, VaR, CVaR, and custom risk-adjusted returns
          </p>
        </div>

        <div className="premium-card p-6">
          <div className="p-3 bg-teal-500/10 rounded-lg w-fit mb-4">
            <Activity className="h-6 w-6 text-teal-400" />
          </div>
          <h3 className="text-lg font-semibold text-white mb-2">
            Performance Attribution
          </h3>
          <p className="text-gray-400 text-sm">
            Detailed breakdown of returns by time period, market regime, and
            trading pair to identify strengths and weaknesses
          </p>
        </div>
      </div>

      {/* Roadmap Section */}
      <div className="premium-card p-8">
        <h2 className="text-2xl font-bold text-white mb-6 text-center">
          Development Roadmap
        </h2>

        <div className="space-y-4 max-w-3xl mx-auto">
          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-green-500/20 border-2 border-green-500 flex items-center justify-center">
              <div className="w-3 h-3 rounded-full bg-green-500"></div>
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-1">
                <h4 className="font-semibold text-white">
                  Phase 1: Data Infrastructure
                </h4>
                <span className="text-xs px-2 py-1 bg-green-500/20 text-green-400 rounded-full">
                  Completed
                </span>
              </div>
              <p className="text-sm text-gray-400">
                Multi-provider data ingestion, correlation analysis, and pair
                discovery
              </p>
            </div>
          </div>

          <div className="flex items-start gap-4">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-blue-500/20 border-2 border-blue-500 flex items-center justify-center">
              <div className="w-3 h-3 rounded-full bg-blue-500 animate-pulse"></div>
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-1">
                <h4 className="font-semibold text-white">
                  Phase 2: Backtesting Engine
                </h4>
                <span className="text-xs px-2 py-1 bg-blue-500/20 text-blue-400 rounded-full">
                  In Progress
                </span>
              </div>
              <p className="text-sm text-gray-400">
                Core backtesting framework with transaction costs and slippage
                modeling
              </p>
              <div className="mt-2 text-xs text-gray-500">ETA: 4-6 weeks</div>
            </div>
          </div>

          <div className="flex items-start gap-4 opacity-60">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-500/20 border-2 border-gray-500 flex items-center justify-center">
              <div className="w-3 h-3 rounded-full bg-gray-500"></div>
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-1">
                <h4 className="font-semibold text-white">
                  Phase 3: Advanced Analytics
                </h4>
                <span className="text-xs px-2 py-1 bg-gray-500/20 text-gray-400 rounded-full">
                  Planned
                </span>
              </div>
              <p className="text-sm text-gray-400">
                Monte Carlo simulations, walk-forward optimization, and risk
                attribution
              </p>
              <div className="mt-2 text-xs text-gray-500">ETA: 8-10 weeks</div>
            </div>
          </div>

          <div className="flex items-start gap-4 opacity-40">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gray-500/20 border-2 border-gray-500 flex items-center justify-center">
              <div className="w-3 h-3 rounded-full bg-gray-500"></div>
            </div>
            <div className="flex-1">
              <div className="flex items-center gap-3 mb-1">
                <h4 className="font-semibold text-white">
                  Phase 4: Live Trading Integration
                </h4>
                <span className="text-xs px-2 py-1 bg-gray-500/20 text-gray-400 rounded-full">
                  Planned
                </span>
              </div>
              <p className="text-sm text-gray-400">
                Paper trading, broker integration, and automated strategy
                execution
              </p>
              <div className="mt-2 text-xs text-gray-500">ETA: 12-16 weeks</div>
            </div>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="premium-card p-8 text-center bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/20">
        <h3 className="text-2xl font-bold text-white mb-3">
          Want Early Access?
        </h3>
        <p className="text-gray-300 mb-6 max-w-xl mx-auto">
          Join our waitlist to get notified when backtesting features go live
          and receive exclusive early access
        </p>
        <div className="flex justify-center gap-4">
          <input
            type="email"
            placeholder="Enter your email"
            className="px-4 py-3 bg-white/5 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-blue-500 w-80"
          />
          <button className="premium-button flex items-center gap-2">
            <Mail className="h-4 w-4" />
            Join Waitlist
          </button>
        </div>
        <p className="text-xs text-gray-500 mt-4">
          No spam. Unsubscribe anytime. We respect your privacy.
        </p>
      </div>
    </div>
  );
}
