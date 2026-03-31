/**
 * Shared UI utilities for consistent styling across components
 */

// ============================================
// Color Schemes
// ============================================

export const colorSchemes = {
  // Score color coding (0-100 scale)
  score: {
    excellent: {
      bg: "bg-green-500",
      text: "text-green-600",
      ring: "ring-green-500",
    },
    good: { bg: "bg-blue-500", text: "text-blue-600", ring: "ring-blue-500" },
    moderate: {
      bg: "bg-yellow-500",
      text: "text-yellow-600",
      ring: "ring-yellow-500",
    },
    poor: { bg: "bg-red-500", text: "text-red-600", ring: "ring-red-500" },
  },

  // Status indicators
  status: {
    success: {
      bg: "bg-green-100",
      text: "text-green-800",
      border: "border-green-300",
    },
    warning: {
      bg: "bg-yellow-100",
      text: "text-yellow-800",
      border: "border-yellow-300",
    },
    error: { bg: "bg-red-100", text: "text-red-800", border: "border-red-300" },
    info: {
      bg: "bg-blue-100",
      text: "text-blue-800",
      border: "border-blue-300",
    },
    neutral: {
      bg: "bg-gray-100",
      text: "text-gray-800",
      border: "border-gray-300",
    },
  },

  // Signal types
  signal: {
    long: {
      bg: "bg-green-500",
      text: "text-green-600",
      gradient: "from-green-500 to-emerald-600",
    },
    short: {
      bg: "bg-red-500",
      text: "text-red-600",
      gradient: "from-red-500 to-rose-600",
    },
    exit: {
      bg: "bg-purple-500",
      text: "text-purple-600",
      gradient: "from-purple-500 to-violet-600",
    },
    hold: {
      bg: "bg-blue-500",
      text: "text-blue-600",
      gradient: "from-blue-500 to-indigo-600",
    },
  },
};

// ============================================
// Gradient Backgrounds
// ============================================

export const gradients = {
  // Premium glass morphism cards
  card: {
    primary:
      "bg-gradient-to-br from-gray-900/50 via-blue-900/30 to-purple-900/30 backdrop-blur-sm",
    secondary:
      "bg-gradient-to-br from-gray-800/50 via-gray-900/30 to-gray-800/50 backdrop-blur-sm",
    success:
      "bg-gradient-to-br from-green-900/30 via-emerald-900/20 to-green-900/30 backdrop-blur-sm",
    warning:
      "bg-gradient-to-br from-yellow-900/30 via-orange-900/20 to-yellow-900/30 backdrop-blur-sm",
    error:
      "bg-gradient-to-br from-red-900/30 via-rose-900/20 to-red-900/30 backdrop-blur-sm",
  },

  // Overlay gradients for hover effects
  overlay: {
    hover:
      "hover:bg-gradient-to-r hover:from-blue-600/10 hover:to-purple-600/10",
    selected: "bg-gradient-to-r from-blue-600/20 to-purple-600/20",
  },

  // Hero sections
  hero: "bg-gradient-to-br from-gray-900 via-blue-900 to-purple-900",
};

// ============================================
// Shadow Utilities
// ============================================

export const shadows = {
  card: "shadow-lg shadow-black/20",
  cardHover: "hover:shadow-2xl hover:shadow-black/40",
  button: "shadow-md shadow-black/10",
  dropdown: "shadow-xl shadow-black/30",
};

// ============================================
// Border Utilities
// ============================================

export const borders = {
  card: "border border-gray-700/50",
  cardHover: "hover:border-blue-500/50",
  selected: "border-2 border-blue-500",
  input: "border border-gray-600 focus:border-blue-500",
};

// ============================================
// Animation Classes
// ============================================

export const animations = {
  fadeIn: "animate-in fade-in duration-300",
  slideIn: "animate-in slide-in-from-bottom-4 duration-300",
  scaleIn: "animate-in zoom-in-95 duration-200",
  spin: "animate-spin",
  pulse: "animate-pulse",
  bounce: "animate-bounce",
};

// ============================================
// Transition Classes
// ============================================

export const transitions = {
  default: "transition-all duration-200",
  fast: "transition-all duration-150",
  slow: "transition-all duration-300",
  colors: "transition-colors duration-200",
  transform: "transition-transform duration-200",
};

// ============================================
// Helper Functions
// ============================================

/**
 * Get color scheme based on score (0-100)
 */
export function getScoreColor(
  score: number,
): typeof colorSchemes.score.excellent {
  if (score >= 80) return colorSchemes.score.excellent;
  if (score >= 60) return colorSchemes.score.good;
  if (score >= 40) return colorSchemes.score.moderate;
  return colorSchemes.score.poor;
}

/**
 * Get color scheme based on strength label
 */
export function getStrengthColor(
  strength: string,
): typeof colorSchemes.score.excellent {
  const normalized = strength.toLowerCase();
  if (normalized.includes("very_strong") || normalized.includes("excellent")) {
    return colorSchemes.score.excellent;
  }
  if (normalized.includes("strong") || normalized.includes("good")) {
    return colorSchemes.score.good;
  }
  if (normalized.includes("moderate") || normalized.includes("medium")) {
    return colorSchemes.score.moderate;
  }
  return colorSchemes.score.poor;
}

/**
 * Get color scheme for P&L values
 */
export function getPnLColor(value: number): { text: string; bg: string } {
  if (value > 0) {
    return { text: "text-green-600", bg: "bg-green-100" };
  } else if (value < 0) {
    return { text: "text-red-600", bg: "bg-red-100" };
  }
  return { text: "text-gray-600", bg: "bg-gray-100" };
}

/**
 * Format percentage with color coding
 */
export function formatPercentage(value: number, decimals: number = 2): string {
  const sign = value > 0 ? "+" : "";
  return `${sign}${value.toFixed(decimals)}%`;
}

/**
 * Format large numbers with K/M/B suffixes
 */
export function formatNumber(value: number): string {
  if (Math.abs(value) >= 1e9) {
    return `${(value / 1e9).toFixed(2)}B`;
  }
  if (Math.abs(value) >= 1e6) {
    return `${(value / 1e6).toFixed(2)}M`;
  }
  if (Math.abs(value) >= 1e3) {
    return `${(value / 1e3).toFixed(2)}K`;
  }
  return value.toFixed(2);
}

/**
 * Combine class names (filters out falsy values)
 */
export function cn(
  ...classes: (string | boolean | undefined | null)[]
): string {
  return classes.filter(Boolean).join(" ");
}

// ============================================
// Common Component Classes
// ============================================

export const componentClasses = {
  // Card base styles
  card: cn(
    "rounded-lg p-6",
    gradients.card.primary,
    borders.card,
    shadows.card,
    transitions.default,
  ),

  cardHover: cn(shadows.cardHover, borders.cardHover, "cursor-pointer"),

  // Button styles
  button: {
    primary: cn(
      "px-4 py-2 rounded-lg",
      "bg-blue-600 hover:bg-blue-700",
      "text-white font-medium",
      shadows.button,
      transitions.colors,
      "disabled:opacity-50 disabled:cursor-not-allowed",
    ),

    secondary: cn(
      "px-4 py-2 rounded-lg",
      "bg-gray-700 hover:bg-gray-600",
      "text-white font-medium",
      shadows.button,
      transitions.colors,
      "disabled:opacity-50 disabled:cursor-not-allowed",
    ),

    danger: cn(
      "px-4 py-2 rounded-lg",
      "bg-red-600 hover:bg-red-700",
      "text-white font-medium",
      shadows.button,
      transitions.colors,
      "disabled:opacity-50 disabled:cursor-not-allowed",
    ),
  },

  // Input styles
  input: cn(
    "px-4 py-2 rounded-lg",
    "bg-gray-800 text-white",
    borders.input,
    transitions.colors,
    "focus:outline-none focus:ring-2 focus:ring-blue-500",
  ),

  // Badge styles
  badge: {
    base: "px-2 py-1 rounded-full text-xs font-medium",
    success: cn(
      "px-2 py-1 rounded-full text-xs font-medium",
      colorSchemes.status.success.bg,
      colorSchemes.status.success.text,
    ),
    warning: cn(
      "px-2 py-1 rounded-full text-xs font-medium",
      colorSchemes.status.warning.bg,
      colorSchemes.status.warning.text,
    ),
    error: cn(
      "px-2 py-1 rounded-full text-xs font-medium",
      colorSchemes.status.error.bg,
      colorSchemes.status.error.text,
    ),
    info: cn(
      "px-2 py-1 rounded-full text-xs font-medium",
      colorSchemes.status.info.bg,
      colorSchemes.status.info.text,
    ),
  },

  // Section header
  sectionHeader: cn(
    "text-2xl font-bold mb-6",
    "bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent",
  ),

  // Skeleton loaders
  skeleton: cn("animate-pulse bg-gray-700 rounded", "h-4 w-full"),
};

// ============================================
// Responsive Grid Patterns
// ============================================

export const gridPatterns = {
  cards: "grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4",
  pairs: "grid gap-4 grid-cols-1 md:grid-cols-2 lg:grid-cols-3",
  metrics: "grid gap-4 grid-cols-2 md:grid-cols-3 lg:grid-cols-4",
  twoColumn: "grid gap-6 grid-cols-1 lg:grid-cols-2",
  threeColumn: "grid gap-6 grid-cols-1 md:grid-cols-2 lg:grid-cols-3",
};

// ============================================
// Z-Index Layers
// ============================================

export const zIndex = {
  base: "z-0",
  dropdown: "z-10",
  sticky: "z-20",
  modal: "z-30",
  popover: "z-40",
  tooltip: "z-50",
};
