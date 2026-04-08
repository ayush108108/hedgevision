import { useState } from "react";
import { Calculator, TrendingUp, TrendingDown, Info, AlertTriangle, CheckCircle } from "lucide-react";
import { InfoTooltip } from "./common/Tooltip";
import { getPairSignalSummary } from "../utils/pairs";

interface HedgeRatioCalculatorProps {
  /** β from the OLS regression — the dollar hedge ratio */
  hedgeRatio?: number;
  asset1Name: string;
  asset2Name: string;
  /** Latest z-score of the spread (used to show current position context) */
  currentZScore?: number;
  isCointegrated?: boolean;
}

function ZScoreBadge({ z }: { z: number }) {
  const abs = Math.abs(z);
  if (abs < 1) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-gray-700/60 text-gray-300 text-xs font-medium">
        <CheckCircle size={11} />
        {z.toFixed(2)} — spread near normal
      </span>
    );
  }
  if (abs >= 1 && abs < 1.5) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-900/60 text-blue-300 text-xs font-medium">
        <Info size={11} />
        {z.toFixed(2)} — spread widening
      </span>
    );
  }
  if (abs >= 1.5 && abs < 2) {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-amber-900/60 text-amber-300 text-xs font-medium border border-amber-700/40">
        <AlertTriangle size={11} />
        {z.toFixed(2)} — potential entry zone
      </span>
    );
  }
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-red-900/60 text-red-300 text-xs font-medium border border-red-700/40">
      <AlertTriangle size={11} />
      {z.toFixed(2)} — extreme spread ⚡
    </span>
  );
}

export function HedgeRatioCalculator({
  hedgeRatio,
  asset1Name,
  asset2Name,
  currentZScore,
  isCointegrated,
}: HedgeRatioCalculatorProps) {
  const [capital, setCapital] = useState<string>("10000");

  const capitalNum = parseFloat(capital.replace(/,/g, "")) || 0;
  const hr = hedgeRatio && Math.abs(hedgeRatio) > 0.001 ? Math.abs(hedgeRatio) : undefined;

  const longAmount = hr ? capitalNum / (1 + hr) : undefined;
  const shortAmount = hr ? capitalNum * hr / (1 + hr) : undefined;

  // Direction: if spread z-score is positive, conventional stat-arb is:
  //   Short Asset1 (overvalued relative to Asset2), Long Asset2
  // If negative: Long Asset1, Short Asset2
  const z = currentZScore;
  const signal = getPairSignalSummary({
    currentZScore: z,
    isCointegrated,
    asset1Name,
    asset2Name,
  });

  const longAsset = signal.longAsset ?? asset1Name;
  const shortAsset = signal.shortAsset ?? asset2Name;

  const formatUSD = (n: number) =>
    new Intl.NumberFormat("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 }).format(n);

  return (
    <div className="premium-card rounded-xl p-5 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-2">
        <div className="w-8 h-8 rounded-lg bg-blue-500/20 flex items-center justify-center shrink-0">
          <Calculator size={16} className="text-blue-400" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-white">
            Hedge Ratio Calculator
            <InfoTooltip
              title="What is this?"
              text="Enter your total trading budget and this calculator tells you exactly how much to put on each asset so the trade is balanced — limiting your risk from overall market moves."
            />
          </h3>
          <p className="text-xs text-gray-500 mt-0.5">
            Enter your budget → get exact dollar amounts for each leg
          </p>
        </div>
      </div>

      {/* Capital Input */}
      <div className="space-y-2">
        <label className="text-xs text-gray-400 flex items-center gap-1">
          Total Trading Budget (USD)
          <InfoTooltip
            title="Trading Budget"
            text="The total amount of money you're willing to deploy in this trade. It will be split across both assets based on their historical relationship."
          />
        </label>
        <div className="relative">
          <span className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 text-sm font-medium">$</span>
          <input
            type="number"
            min={0}
            value={capital}
            onChange={(e) => setCapital(e.target.value)}
            className="w-full bg-white/5 border border-white/10 rounded-lg pl-8 pr-4 py-2.5 text-white text-sm focus:outline-none focus:border-blue-500/50 focus:bg-white/8 transition-colors"
            placeholder="10000"
          />
        </div>
        {/* Quick presets */}
        <div className="flex flex-wrap gap-1.5">
          {[1000, 5000, 10000, 25000, 50000].map((amt) => (
            <button
              key={amt}
              onClick={() => setCapital(String(amt))}
              className={`px-2.5 py-1 rounded-md text-xs transition-colors ${
                capital === String(amt)
                  ? "bg-blue-500/30 text-blue-300 border border-blue-500/40"
                  : "bg-white/5 text-gray-400 hover:text-white hover:bg-white/10 border border-white/5"
              }`}
            >
              {formatUSD(amt)}
            </button>
          ))}
        </div>
      </div>

      {/* Hedge Ratio Display */}
      {hr !== undefined ? (
        <div className="bg-white/3 rounded-lg border border-white/8 p-3 flex items-center justify-between">
          <span className="text-xs text-gray-400 flex items-center gap-1">
            Hedge Ratio (β)
            <InfoTooltip
              title="Hedge Ratio"
              text={`For every $1 you put into ${asset1Name}, you put $${hr.toFixed(2)} into ${asset2Name}. This ratio is calculated from their historical price relationship so the trade stays balanced.`}
            />
          </span>
          <span className="text-sm font-semibold text-white font-mono">{hr.toFixed(4)}</span>
        </div>
      ) : (
        <div className="bg-amber-900/20 rounded-lg border border-amber-700/30 p-3 text-xs text-amber-400">
          Hedge ratio not yet computed. Select a pair and run the analysis first.
        </div>
      )}

      {/* Position Sizing Results */}
      {hr !== undefined && capitalNum > 0 && longAmount !== undefined && shortAmount !== undefined && (
        <div className="space-y-3">
          <div className="text-xs text-gray-500 uppercase tracking-wider">Recommended Position Sizes</div>

          {/* Long leg */}
          <div className="flex items-center justify-between bg-emerald-900/20 rounded-lg border border-emerald-700/25 px-4 py-3">
            <div className="flex items-center gap-2">
              <TrendingUp size={15} className="text-emerald-400 shrink-0" />
              <div>
                <div className="text-xs text-gray-400">
                  Buy (Long)
                  <InfoTooltip
                    title="Long position"
                    text={`You profit when ${longAsset} rises relative to ${shortAsset}. This is the asset you expect to go up (or be undervalued right now).`}
                  />
                </div>
                <div className="text-sm font-semibold text-white">{longAsset}</div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-base font-bold text-emerald-400">{formatUSD(longAmount)}</div>
              <div className="text-xs text-gray-500">{((longAmount / capitalNum) * 100).toFixed(1)}% of budget</div>
            </div>
          </div>

          {/* Short leg */}
          <div className="flex items-center justify-between bg-red-900/20 rounded-lg border border-red-700/25 px-4 py-3">
            <div className="flex items-center gap-2">
              <TrendingDown size={15} className="text-red-400 shrink-0" />
              <div>
                <div className="text-xs text-gray-400">
                  Sell Short
                  <InfoTooltip
                    title="Short position"
                    text={`You profit when ${shortAsset} falls relative to ${longAsset}. You borrow and sell shares you don’t own, hoping to buy them back cheaper later.`}
                  />
                </div>
                <div className="text-sm font-semibold text-white">{shortAsset}</div>
              </div>
            </div>
            <div className="text-right">
              <div className="text-base font-bold text-red-400">{formatUSD(shortAmount)}</div>
              <div className="text-xs text-gray-500">{((shortAmount / capitalNum) * 100).toFixed(1)}% of budget</div>
            </div>
          </div>

          {/* Plain-English summary */}
          <div className="bg-blue-900/20 border border-blue-700/25 rounded-lg px-4 py-3 text-xs text-blue-200 leading-relaxed">
            <span className="font-semibold text-blue-300">How to read this: </span>
            Put <strong>{formatUSD(longAmount)}</strong> into {longAsset} (buy it) and
            {" "}<strong>{formatUSD(shortAmount)}</strong> into {shortAsset} (sell short). If the spread returns to normal,
            you profit on both sides. The ratio ensures a market move up or down doesn't hurt you — only the
            <em> relative</em> movement between the two assets matters.
          </div>
        </div>
      )}

      {/* Current Z-Score Signal */}
      {z !== undefined && (
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-gray-400 flex items-center gap-1">
              Current Spread (Z-Score)
              <InfoTooltip
                title="Z-Score"
                text="Measures how far the current spread is from its historical average, in units of standard deviation. A z-score above 1.5 or below -1.5 suggests the spread is stretched and may snap back — this is your trading opportunity."
              />
            </span>
            <ZScoreBadge z={z} />
          </div>
          <div
            className={`text-xs rounded-lg px-3 py-2 border ${
              signal.tone === "red"
                ? "bg-red-900/20 border-red-700/30 text-red-300"
                : signal.tone === "yellow"
                ? "bg-amber-900/20 border-amber-700/30 text-amber-300"
                : signal.tone === "blue"
                ? "bg-blue-900/20 border-blue-700/30 text-blue-300"
                : "bg-white/3 border-white/8 text-gray-400"
            }`}
          >
            <span className="font-medium">{signal.label}:</span> {signal.detail}
          </div>
        </div>
      )}
    </div>
  );
}
