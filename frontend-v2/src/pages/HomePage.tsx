import React from "react";
import { useNavigate } from "react-router-dom";
import { TrendingUp, Activity, BarChart3, Target, Zap, Shield, BookOpen } from "lucide-react";

export function HomePage() {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <div className="relative overflow-hidden">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-600/20 via-purple-600/20 to-pink-600/20" />
        <div className="absolute inset-0 bg-[url('/grid.svg')] opacity-10" />
        
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-20 pb-24">
          <div className="text-center">
            <h1 className="text-3xl sm:text-5xl md:text-7xl font-bold text-white mb-6 animate-in fade-in duration-700">
              Statistical Arbitrage
              <span className="block text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-400 mt-2">
                Powered by Data
              </span>
            </h1>
            <p className="text-xl md:text-2xl text-gray-300 mb-8 max-w-3xl mx-auto animate-in fade-in duration-700 delay-100">
              Advanced quantitative analysis tools for discovering market relationships,
              identifying trading opportunities, and managing portfolio risk.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center animate-in fade-in duration-700 delay-200">
              <button
                onClick={() => navigate("/cointegration")}
                className="px-8 py-4 rounded-lg bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-semibold text-lg shadow-lg shadow-blue-500/30 hover:shadow-blue-500/50 transition-all"
              >
                View Top Pairs
              </button>
              <button
                onClick={() => navigate("/correlation")}
                className="px-8 py-4 rounded-lg bg-white/5 border border-gray-700 hover:bg-white/10 text-white font-semibold text-lg transition-all"
              >
                Explore Correlations
              </button>
              <button
                onClick={() => navigate("/learn")}
                className="px-8 py-4 rounded-lg bg-white/5 border border-gray-700 hover:bg-white/10 text-white font-semibold text-lg transition-all flex items-center gap-2 justify-center"
              >
                <BookOpen size={18} />
                How It Works
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Features Grid */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-24">
        <div className="text-center mb-16">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            Powerful Analysis Tools
          </h2>
          <p className="text-lg text-gray-400 max-w-2xl mx-auto">
            Everything you need to analyze market relationships and discover trading opportunities
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {/* Feature 1 */}
          <div 
            onClick={() => navigate("/correlation")}
            className="premium-card p-8 hover:scale-105 transition-transform duration-300 cursor-pointer"
          >
            <div className="w-12 h-12 rounded-lg bg-blue-500/20 flex items-center justify-center mb-4">
              <Activity className="text-blue-400" size={24} />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">
              Correlation Analysis
            </h3>
            <p className="text-gray-400">
              Discover relationships between assets using Pearson and Spearman correlation methods
              with interactive heatmaps and sector-level aggregation.
            </p>
          </div>

          {/* Feature 2 */}
          <div 
            onClick={() => navigate("/pair-analysis")}
            className="premium-card p-8 hover:scale-105 transition-transform duration-300 cursor-pointer"
          >
            <div className="w-12 h-12 rounded-lg bg-purple-500/20 flex items-center justify-center mb-4">
              <TrendingUp className="text-purple-400" size={24} />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">
              Pair Analysis
            </h3>
            <p className="text-gray-400">
              Deep dive into asset pairs with cointegration tests, rolling metrics, and
              comprehensive statistical analysis for identifying mean-reversion opportunities.
            </p>
          </div>

          {/* Feature 3 */}
          <div 
            onClick={() => navigate("/cointegration")}
            className="premium-card p-8 hover:scale-105 transition-transform duration-300 cursor-pointer"
          >
            <div className="w-12 h-12 rounded-lg bg-pink-500/20 flex items-center justify-center mb-4">
              <BarChart3 className="text-pink-400" size={24} />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">
              Smart Screener
            </h3>
            <p className="text-gray-400">
              Filter and rank asset pairs by correlation strength, volatility, and custom metrics
              to find the most promising trading opportunities.
            </p>
          </div>

          {/* Feature 4 */}
          <div 
            onClick={() => navigate("/pair-analysis")}
            className="premium-card p-8 hover:scale-105 transition-transform duration-300 cursor-pointer"
          >
            <div className="w-12 h-12 rounded-lg bg-green-500/20 flex items-center justify-center mb-4">
              <Target className="text-green-400" size={24} />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">
              Rolling Metrics
            </h3>
            <p className="text-gray-400">
              Track beta, volatility, and Sharpe ratio over time to understand how asset
              relationships evolve and identify regime changes.
            </p>
          </div>

          {/* Feature 5 */}
          <div 
            onClick={() => navigate("/correlation")}
            className="premium-card p-8 hover:scale-105 transition-transform duration-300 cursor-pointer"
          >
            <div className="w-12 h-12 rounded-lg bg-yellow-500/20 flex items-center justify-center mb-4">
              <Zap className="text-yellow-400" size={24} />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">
              Real-time Data
            </h3>
            <p className="text-gray-400">
              Access live market data with daily and intraday granularity for stocks, ETFs,
              crypto, and forex pairs powered by Yahoo Finance.
            </p>
          </div>

          {/* Feature 6 */}
          <div 
            onClick={() => navigate("/cointegration")}
            className="premium-card p-8 hover:scale-105 transition-transform duration-300 cursor-pointer"
          >
            <div className="w-12 h-12 rounded-lg bg-red-500/20 flex items-center justify-center mb-4">
              <Shield className="text-red-400" size={24} />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">
              Risk Management
            </h3>
            <p className="text-gray-400">
              Evaluate portfolio risk with cointegration testing, regression analysis, and
              diversification metrics for better risk-adjusted returns.
            </p>
          </div>

          {/* Feature 7 — Education */}
          <div 
            onClick={() => navigate("/learn")}
            className="premium-card p-8 hover:scale-105 transition-transform duration-300 cursor-pointer border-blue-500/20"
          >
            <div className="w-12 h-12 rounded-lg bg-blue-500/20 flex items-center justify-center mb-4">
              <BookOpen className="text-blue-400" size={24} />
            </div>
            <h3 className="text-xl font-semibold text-white mb-3">
              Learn Stat-Arb
            </h3>
            <p className="text-gray-400">
              New to pairs trading? Our plain-English guide explains what statistical arbitrage is,
              why it works, and how to read every metric on this platform.
            </p>
          </div>
        </div>
      </div>

      {/* CTA Section */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pb-24">
        <div className="premium-card p-12 text-center bg-gradient-to-br from-blue-500/10 to-purple-500/10">
          <h2 className="text-3xl md:text-4xl font-bold text-white mb-4">
            Ready to start analyzing?
          </h2>
          <p className="text-lg text-gray-300 mb-8 max-w-2xl mx-auto">
            Explore market relationships and discover trading opportunities with our
            comprehensive suite of quantitative analysis tools.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <button
              onClick={() => navigate("/correlation")}
              className="px-8 py-4 rounded-lg bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-semibold text-lg shadow-lg shadow-blue-500/30 hover:shadow-blue-500/50 transition-all"
            >
              Get Started
            </button>
            <button
              onClick={() => navigate("/pair-analysis")}
              className="px-8 py-4 rounded-lg bg-white/5 border border-gray-700 hover:bg-white/10 text-white font-semibold text-lg transition-all"
            >
              View Demo
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
