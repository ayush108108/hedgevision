/**
 * Feature flags for HedgeVision.
 *
 * Core pages are always enabled. Optional pages can be toggled via
 * VITE_FEATURE_* environment variables. Defaults are tuned for the
 * lightweight production showcase.
 *
 * To enable an optional feature set the corresponding env var to "true"
 * in your .env.local (frontend) or at build time:
 *
 *   VITE_FEATURE_PORTFOLIO=true
 *   VITE_FEATURE_NEWS=true
 *   VITE_FEATURE_CALCULATOR=true
 *   VITE_FEATURE_WATCHLIST=true
 *   VITE_FEATURE_BACKTEST=true
 *   VITE_FEATURE_ONBOARDING=true
 *   VITE_FEATURE_AUTH=true
 */

const flag = (key: string, fallback = false): boolean => {
  const val = import.meta.env[key];
  if (val === undefined) return fallback;
  return val === "true" || val === "1";
};

export const features = {
  /** Always-on core pages */
  correlation: true,
  cointegration: true,
  pairAnalysis: true,
  signals: true,

  /** Optional pages — backtest enabled by default; others off for lean deployment */
  portfolio: flag("VITE_FEATURE_PORTFOLIO"),
  news: flag("VITE_FEATURE_NEWS"),
  calculator: flag("VITE_FEATURE_CALCULATOR"),
  watchlist: flag("VITE_FEATURE_WATCHLIST"),
  backtest: flag("VITE_FEATURE_BACKTEST", true),
  onboarding: flag("VITE_FEATURE_ONBOARDING"),
  auth: flag("VITE_FEATURE_AUTH"),
} as const;
