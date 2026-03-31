import React, { useState, useEffect } from "react";
import { Calculator, DollarSign, TrendingUp, AlertTriangle, Info, Target, Percent, BarChart3 } from "lucide-react";

export function TradingCalculatorPage() {
  // Position sizing inputs
  const [accountBalance, setAccountBalance] = useState<string>("10000");
  const [riskPercentage, setRiskPercentage] = useState<string>("2");
  const [entryPrice, setEntryPrice] = useState<string>("100");
  const [stopLoss, setStopLoss] = useState<string>("95");
  
  // Pair trading inputs
  const [hedgeRatio, setHedgeRatio] = useState<string>("1.0");
  const [asset1Price, setAsset1Price] = useState<string>("100");
  const [asset2Price, setAsset2Price] = useState<string>("50");
  
  // Transaction costs
  const [commissionRate, setCommissionRate] = useState<string>("0.1");
  const [slippageRate, setSlippageRate] = useState<string>("0.05");

  // Calculated values
  const [positionSize, setPositionSize] = useState<number>(0);
  const [sharesLong, setSharesLong] = useState<number>(0);
  const [sharesShort, setSharesShort] = useState<number>(0);
  const [totalCost, setTotalCost] = useState<number>(0);
  const [riskAmount, setRiskAmount] = useState<number>(0);
  const [rewardRiskRatio, setRewardRiskRatio] = useState<number>(0);

  useEffect(() => {
    calculatePosition();
  }, [accountBalance, riskPercentage, entryPrice, stopLoss, hedgeRatio, asset1Price, asset2Price, commissionRate, slippageRate]);

  const calculatePosition = () => {
    const balance = parseFloat(accountBalance) || 0;
    const riskPct = parseFloat(riskPercentage) || 0;
    const entry = parseFloat(entryPrice) || 0;
    const stop = parseFloat(stopLoss) || 0;
    const ratio = parseFloat(hedgeRatio) || 1;
    const price1 = parseFloat(asset1Price) || 0;
    const price2 = parseFloat(asset2Price) || 0;
    const commission = parseFloat(commissionRate) / 100 || 0;
    const slippage = parseFloat(slippageRate) / 100 || 0;

    // Calculate risk amount
    const risk = (balance * riskPct) / 100;
    setRiskAmount(risk);

    // Calculate position size for single asset
    const priceRisk = Math.abs(entry - stop);
    if (priceRisk > 0) {
      const shares = risk / priceRisk;
      setPositionSize(shares);

      // Calculate pair trading positions
      const longShares = shares;
      const shortShares = shares * ratio;
      setSharesLong(longShares);
      setSharesShort(shortShares);

      // Calculate total cost including transaction costs
      const longValue = longShares * price1;
      const shortValue = shortShares * price2;
      const totalValue = longValue + shortValue;
      const transactionCosts = totalValue * (commission + slippage);
      setTotalCost(totalValue + transactionCosts);

      // Calculate reward:risk ratio (assuming 2x stop distance as target)
      const targetPrice = entry + (entry - stop) * 2;
      const potentialReward = Math.abs(targetPrice - entry) * shares;
      setRewardRiskRatio(risk > 0 ? potentialReward / risk : 0);
    }
  };

  const formatCurrency = (value: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value);
  };

  const formatNumber = (value: number, decimals: number = 2) => {
    return value.toFixed(decimals);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900/20 to-gray-900">
      {/* Header */}
      <div className="border-b border-white/10 bg-gradient-to-r from-blue-500/10 to-purple-500/10 backdrop-blur-xl">
        <div className="max-w-[1920px] mx-auto px-6 py-8">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-lg bg-blue-500/20 border border-blue-500/30">
              <Calculator className="h-6 w-6 text-blue-400" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-white">Trading Calculator</h1>
              <p className="text-gray-400 text-sm mt-1">
                Calculate position sizes, risk/reward ratios, and pair trading metrics
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Content */}
      <div className="max-w-[1920px] mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Input Section */}
          <div className="space-y-6">
            {/* Account & Risk Parameters */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-lg p-6">
              <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                <DollarSign className="w-5 h-5 text-green-400" />
                Account & Risk Parameters
              </h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Account Balance
                  </label>
                  <div className="relative">
                    <DollarSign className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                    <input
                      type="number"
                      value={accountBalance}
                      onChange={(e) => setAccountBalance(e.target.value)}
                      className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-blue-500/50"
                      placeholder="10000"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Risk Per Trade (%)
                  </label>
                  <div className="relative">
                    <Percent className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                    <input
                      type="number"
                      value={riskPercentage}
                      onChange={(e) => setRiskPercentage(e.target.value)}
                      className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-blue-500/50"
                      placeholder="2"
                      step="0.1"
                    />
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Recommended: 1-2% for conservative, 3-5% for aggressive</p>
                </div>
              </div>
            </div>

            {/* Entry & Stop Loss */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-lg p-6">
              <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                <Target className="w-5 h-5 text-blue-400" />
                Entry & Exit Levels
              </h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Entry Price
                  </label>
                  <div className="relative">
                    <TrendingUp className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                    <input
                      type="number"
                      value={entryPrice}
                      onChange={(e) => setEntryPrice(e.target.value)}
                      className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-blue-500/50"
                      placeholder="100"
                      step="0.01"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Stop Loss Price
                  </label>
                  <div className="relative">
                    <AlertTriangle className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
                    <input
                      type="number"
                      value={stopLoss}
                      onChange={(e) => setStopLoss(e.target.value)}
                      className="w-full pl-10 pr-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-blue-500/50"
                      placeholder="95"
                      step="0.01"
                    />
                  </div>
                  <p className="text-xs text-gray-500 mt-1">
                    Risk per share: {formatCurrency(Math.abs(parseFloat(entryPrice || "0") - parseFloat(stopLoss || "0")))}
                  </p>
                </div>
              </div>
            </div>

            {/* Pair Trading Parameters */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-lg p-6">
              <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-purple-400" />
                Pair Trading Parameters
              </h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Hedge Ratio
                  </label>
                  <input
                    type="number"
                    value={hedgeRatio}
                    onChange={(e) => setHedgeRatio(e.target.value)}
                    className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-blue-500/50"
                    placeholder="1.0"
                    step="0.01"
                  />
                  <p className="text-xs text-gray-500 mt-1">Asset 2 shares = Asset 1 shares × Hedge Ratio</p>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Asset 1 Price
                    </label>
                    <input
                      type="number"
                      value={asset1Price}
                      onChange={(e) => setAsset1Price(e.target.value)}
                      className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-blue-500/50"
                      placeholder="100"
                      step="0.01"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Asset 2 Price
                    </label>
                    <input
                      type="number"
                      value={asset2Price}
                      onChange={(e) => setAsset2Price(e.target.value)}
                      className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-blue-500/50"
                      placeholder="50"
                      step="0.01"
                    />
                  </div>
                </div>
              </div>
            </div>

            {/* Transaction Costs */}
            <div className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-lg p-6">
              <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                <Info className="w-5 h-5 text-yellow-400" />
                Transaction Costs
              </h2>
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Commission Rate (%)
                  </label>
                  <input
                    type="number"
                    value={commissionRate}
                    onChange={(e) => setCommissionRate(e.target.value)}
                    className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-blue-500/50"
                    placeholder="0.1"
                    step="0.01"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2">
                    Slippage Rate (%)
                  </label>
                  <input
                    type="number"
                    value={slippageRate}
                    onChange={(e) => setSlippageRate(e.target.value)}
                    className="w-full px-4 py-2 bg-white/5 border border-white/10 rounded-lg text-white focus:outline-none focus:border-blue-500/50"
                    placeholder="0.05"
                    step="0.01"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Results Section */}
          <div className="space-y-6">
            {/* Position Size Results */}
            <div className="bg-gradient-to-br from-blue-500/20 to-purple-500/20 backdrop-blur-xl border border-blue-500/30 rounded-lg p-6">
              <h2 className="text-xl font-semibold text-white mb-4">Calculated Position</h2>
              <div className="space-y-4">
                <div className="flex justify-between items-center pb-3 border-b border-white/10">
                  <span className="text-gray-300">Risk Amount</span>
                  <span className="text-2xl font-bold text-red-400">{formatCurrency(riskAmount)}</span>
                </div>
                <div className="flex justify-between items-center pb-3 border-b border-white/10">
                  <span className="text-gray-300">Position Size (shares)</span>
                  <span className="text-2xl font-bold text-white">{formatNumber(positionSize, 0)}</span>
                </div>
                <div className="flex justify-between items-center pb-3 border-b border-white/10">
                  <span className="text-gray-300">Position Value</span>
                  <span className="text-2xl font-bold text-green-400">
                    {formatCurrency(positionSize * parseFloat(entryPrice || "0"))}
                  </span>
                </div>
              </div>
            </div>

            {/* Pair Trading Results */}
            <div className="bg-gradient-to-br from-purple-500/20 to-pink-500/20 backdrop-blur-xl border border-purple-500/30 rounded-lg p-6">
              <h2 className="text-xl font-semibold text-white mb-4">Pair Trading Allocation</h2>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm text-gray-400">Long Position (Asset 1)</span>
                    <span className="text-sm font-mono text-green-400">LONG</span>
                  </div>
                  <div className="flex justify-between items-center pb-3 border-b border-white/10">
                    <span className="text-gray-300">Shares</span>
                    <span className="text-xl font-bold text-white">{formatNumber(sharesLong, 0)}</span>
                  </div>
                  <div className="flex justify-between items-center mt-2">
                    <span className="text-gray-300">Value</span>
                    <span className="text-lg font-semibold text-green-400">
                      {formatCurrency(sharesLong * parseFloat(asset1Price || "0"))}
                    </span>
                  </div>
                </div>
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm text-gray-400">Short Position (Asset 2)</span>
                    <span className="text-sm font-mono text-red-400">SHORT</span>
                  </div>
                  <div className="flex justify-between items-center pb-3 border-b border-white/10">
                    <span className="text-gray-300">Shares</span>
                    <span className="text-xl font-bold text-white">{formatNumber(sharesShort, 0)}</span>
                  </div>
                  <div className="flex justify-between items-center mt-2">
                    <span className="text-gray-300">Value</span>
                    <span className="text-lg font-semibold text-red-400">
                      {formatCurrency(sharesShort * parseFloat(asset2Price || "0"))}
                    </span>
                  </div>
                </div>
                <div className="pt-3 border-t border-white/10">
                  <div className="flex justify-between items-center">
                    <span className="text-gray-300 font-semibold">Total Capital Required</span>
                    <span className="text-2xl font-bold text-blue-400">{formatCurrency(totalCost)}</span>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Includes transaction costs and slippage</p>
                </div>
              </div>
            </div>

            {/* Risk Metrics */}
            <div className="bg-gradient-to-br from-green-500/20 to-blue-500/20 backdrop-blur-xl border border-green-500/30 rounded-lg p-6">
              <h2 className="text-xl font-semibold text-white mb-4">Risk Metrics</h2>
              <div className="space-y-4">
                <div className="flex justify-between items-center pb-3 border-b border-white/10">
                  <span className="text-gray-300">Reward:Risk Ratio</span>
                  <span className={`text-2xl font-bold ${rewardRiskRatio >= 2 ? 'text-green-400' : 'text-yellow-400'}`}>
                    {formatNumber(rewardRiskRatio, 2)}:1
                  </span>
                </div>
                <div className="flex justify-between items-center pb-3 border-b border-white/10">
                  <span className="text-gray-300">Risk as % of Account</span>
                  <span className="text-xl font-bold text-red-400">{riskPercentage}%</span>
                </div>
                <div className="flex justify-between items-center">
                  <span className="text-gray-300">Capital Allocation</span>
                  <span className="text-xl font-bold text-blue-400">
                    {formatNumber((totalCost / parseFloat(accountBalance || "1")) * 100, 1)}%
                  </span>
                </div>
              </div>
            </div>

            {/* Risk Warning */}
            <div className="bg-yellow-500/10 border border-yellow-500/30 rounded-lg p-4">
              <div className="flex items-start gap-3">
                <AlertTriangle className="w-5 h-5 text-yellow-400 mt-0.5 flex-shrink-0" />
                <div>
                  <h4 className="text-yellow-300 font-semibold mb-1">Risk Disclaimer</h4>
                  <p className="text-yellow-200/80 text-sm">
                    These calculations are for educational purposes only. Always verify calculations independently 
                    and consider your personal risk tolerance, market conditions, and trading strategy before 
                    executing any trades. Past performance does not guarantee future results.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
