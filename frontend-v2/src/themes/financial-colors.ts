/**
 * Financial Colors Palette for HedgeVision
 * Industry-standard colors for financial data visualization
 */

export const FinancialColors = {
  // Background colors
  background: {
    primary: "rgba(15, 23, 42, 0.5)", // Main app background
    card: "rgba(30, 41, 59, 0.8)", // Card backgrounds
    chart: "rgba(15, 23, 42, 0.95)", // Chart backgrounds
    overlay: "rgba(15, 23, 42, 0.98)", // Modal/tooltip overlays
  },

  // Financial data colors (standard across industry)
  financial: {
    bullish: "#10b981", // Green - positive returns, long positions, gains
    bearish: "#ef4444", // Red - negative returns, short positions, losses
    neutral: "#64748b", // Gray - neutral, no change
    volume: "#3b82f6", // Blue - volume bars
  },

  // Brand colors (HedgeVision identity)
  brand: {
    primary: "#3b82f6", // Blue - primary actions, main data series
    secondary: "#06b6d4", // Cyan - secondary data series
    accent: "#8b5cf6", // Purple - highlights, special indicators
    success: "#10b981", // Green - success states
    warning: "#f59e0b", // Amber - warnings, alerts
    error: "#ef4444", // Red - errors, critical issues
    info: "#3b82f6", // Blue - informational messages
  },

  // Text hierarchy
  text: {
    primary: "#f1f5f9", // High emphasis (titles, key values)
    secondary: "#94a3b8", // Medium emphasis (labels, descriptions)
    tertiary: "#64748b", // Low emphasis (captions, metadata)
    disabled: "#475569", // Disabled state
    inverse: "#0f172a", // Text on light backgrounds
  },

  // Correlation heatmap gradient (blue-white-red scale)
  correlation: {
    strongNegative: "#dc2626", // -1.0 (strong negative correlation)
    negative: "#f87171", // -0.5 (moderate negative)
    neutral: "#f8fafc", // 0.0 (no correlation)
    positive: "#60a5fa", // +0.5 (moderate positive)
    strongPositive: "#2563eb", // +1.0 (strong positive correlation)
  },

  // Chart series colors (for multi-line charts)
  series: [
    "#3b82f6", // Blue
    "#10b981", // Green
    "#f59e0b", // Amber
    "#8b5cf6", // Purple
    "#06b6d4", // Cyan
    "#ec4899", // Pink
    "#14b8a6", // Teal
    "#f97316", // Orange
  ],

  // Border and divider colors
  border: {
    subtle: "rgba(255, 255, 255, 0.05)", // Very subtle borders
    light: "rgba(255, 255, 255, 0.1)", // Light borders
    medium: "rgba(255, 255, 255, 0.2)", // Medium borders
    strong: "rgba(255, 255, 255, 0.3)", // Strong borders
  },

  // Overlay colors (for tooltips, modals)
  overlay: {
    subtle: "rgba(0, 0, 0, 0.2)",
    medium: "rgba(0, 0, 0, 0.5)",
    strong: "rgba(0, 0, 0, 0.8)",
  },

  // Grid colors (for chart gridlines)
  grid: {
    subtle: "rgba(255, 255, 255, 0.03)",
    light: "rgba(255, 255, 255, 0.05)",
    medium: "rgba(255, 255, 255, 0.1)",
  },
} as const;

// Helper function to get correlation color based on value
export function getCorrelationColor(value: number): string {
  if (value <= -0.75) return FinancialColors.correlation.strongNegative;
  if (value <= -0.25) return FinancialColors.correlation.negative;
  if (value <= 0.25) return FinancialColors.correlation.neutral;
  if (value <= 0.75) return FinancialColors.correlation.positive;
  return FinancialColors.correlation.strongPositive;
}

// Helper function to get financial color (bullish/bearish)
export function getFinancialColor(
  value: number,
  threshold: number = 0,
): string {
  if (value > threshold) return FinancialColors.financial.bullish;
  if (value < threshold) return FinancialColors.financial.bearish;
  return FinancialColors.financial.neutral;
}

// Helper function to get series color by index
export function getSeriesColor(index: number): string {
  return FinancialColors.series[index % FinancialColors.series.length];
}

// Export type for TypeScript
export type FinancialColorsType = typeof FinancialColors;
