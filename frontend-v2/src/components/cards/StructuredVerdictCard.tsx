import React from "react";
import { TrendingDown, TrendingUp, Minus } from "lucide-react";
import type { StructuredVerdict } from "../../services/marketIntel";

function stanceStyle(stance: StructuredVerdict["stance"]) {
  if (stance === "bullish") {
    return {
      badge: "bg-emerald-500/20 text-emerald-300 border-emerald-500/40",
      icon: <TrendingUp className="w-5 h-5 text-emerald-300" />,
      label: "Bullish",
    };
  }
  if (stance === "bearish") {
    return {
      badge: "bg-rose-500/20 text-rose-300 border-rose-500/40",
      icon: <TrendingDown className="w-5 h-5 text-rose-300" />,
      label: "Bearish",
    };
  }
  return {
    badge: "bg-slate-500/20 text-slate-300 border-slate-500/40",
    icon: <Minus className="w-5 h-5 text-slate-300" />,
    label: "Neutral",
  };
}

export function StructuredVerdictCard({
  ticker,
  verdict,
}: {
  ticker: string;
  verdict: StructuredVerdict;
}) {
  const style = stanceStyle(verdict.stance);
  return (
    <div className="rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900 to-slate-800 p-5">
      <div className="flex items-center justify-between gap-4">
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wider">
            Structured Verdict
          </p>
          <h3 className="text-xl font-semibold text-white mt-1">{ticker}</h3>
        </div>
        <span
          className={`inline-flex items-center gap-2 px-3 py-1 rounded-full border text-sm font-semibold ${style.badge}`}
        >
          {style.icon}
          {style.label}
        </span>
      </div>

      <p className="text-slate-200 mt-4">{verdict.headline}</p>
      <p className="text-sm text-slate-400 mt-2">
        Confidence: {(verdict.confidence * 100).toFixed(1)}%
      </p>

      <ul className="mt-4 space-y-2">
        {verdict.rationale.map((line, idx) => (
          <li key={`${line}-${idx}`} className="text-sm text-slate-300">
            {line}
          </li>
        ))}
      </ul>

      <p className="text-xs text-slate-500 mt-4">
        Provider: {verdict.model_provider} | Model Version: {verdict.model_version}
      </p>
    </div>
  );
}

