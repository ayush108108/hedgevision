/**
 * Custom ECharts Dark Theme for HedgeVision
 * Professional financial charting theme with glass morphism effects
 */

import { FinancialColors } from "./financial-colors";
import type { EChartsOption } from "echarts";

export const HedgeVisionDarkTheme: EChartsOption = {
  // Color palette for series
  color: [...FinancialColors.series] as string[],

  // Background
  backgroundColor: "transparent", // Let parent container handle background

  // Text styles
  textStyle: {
    fontFamily:
      '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif',
    fontSize: 12,
    color: FinancialColors.text.secondary,
  },

  // Title
  title: {
    textStyle: {
      color: FinancialColors.text.primary,
      fontSize: 18,
      fontWeight: 600,
    },
    subtextStyle: {
      color: FinancialColors.text.secondary,
      fontSize: 12,
    },
  },

  // Legend
  legend: {
    textStyle: {
      color: FinancialColors.text.secondary,
      fontSize: 12,
    },
    inactiveColor: FinancialColors.text.disabled,
    itemGap: 16,
    itemWidth: 20,
    itemHeight: 12,
    icon: "roundRect",
  },

  // Tooltip
  tooltip: {
    backgroundColor: FinancialColors.background.overlay,
    borderColor: FinancialColors.border.medium,
    borderWidth: 1,
    textStyle: {
      color: FinancialColors.text.primary,
      fontSize: 12,
    },
    padding: [12, 16],
    extraCssText: `
      backdrop-filter: blur(12px);
      border-radius: 8px;
      box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    `,
  },

  // Axis
  categoryAxis: {
    axisLine: {
      lineStyle: {
        color: FinancialColors.border.light,
      },
    },
    axisTick: {
      lineStyle: {
        color: FinancialColors.border.light,
      },
    },
    axisLabel: {
      color: FinancialColors.text.tertiary,
      fontSize: 11,
    },
    splitLine: {
      lineStyle: {
        color: FinancialColors.grid.subtle,
        type: "dashed",
      },
    },
  },

  valueAxis: {
    axisLine: {
      lineStyle: {
        color: FinancialColors.border.light,
      },
    },
    axisTick: {
      lineStyle: {
        color: FinancialColors.border.light,
      },
    },
    axisLabel: {
      color: FinancialColors.text.tertiary,
      fontSize: 11,
    },
    splitLine: {
      lineStyle: {
        color: FinancialColors.grid.light,
        type: "dashed",
      },
    },
  },

  // Grid
  grid: {
    borderColor: FinancialColors.border.subtle,
  },

  // Line series
  line: {
    smooth: true,
    symbolSize: 6,
    lineStyle: {
      width: 2,
    },
    emphasis: {
      focus: "series",
      lineStyle: {
        width: 3,
      },
    },
  },

  // Bar series
  bar: {
    itemStyle: {
      borderRadius: [4, 4, 0, 0],
    },
    emphasis: {
      focus: "series",
    },
  },

  // Scatter series
  scatter: {
    symbolSize: 8,
    emphasis: {
      focus: "series",
      scale: 1.5,
    },
  },

  // Candlestick series
  candlestick: {
    itemStyle: {
      color: FinancialColors.financial.bullish,
      color0: FinancialColors.financial.bearish,
      borderColor: FinancialColors.financial.bullish,
      borderColor0: FinancialColors.financial.bearish,
      borderWidth: 1,
    },
    emphasis: {
      itemStyle: {
        borderWidth: 2,
      },
    },
  },

  // Heatmap
  heatmap: {
    itemStyle: {
      borderWidth: 1,
      borderColor: FinancialColors.border.subtle,
    },
    emphasis: {
      itemStyle: {
        borderWidth: 2,
        borderColor: FinancialColors.border.strong,
        shadowBlur: 10,
        shadowColor: "rgba(0, 0, 0, 0.5)",
      },
    },
  },

  // Visual map (for heatmaps)
  visualMap: {
    textStyle: {
      color: FinancialColors.text.secondary,
      fontSize: 11,
    },
    itemWidth: 20,
    itemHeight: 140,
  },

  // Data zoom
  dataZoom: {
    backgroundColor: FinancialColors.background.card,
    dataBackground: {
      lineStyle: {
        color: FinancialColors.brand.primary,
        opacity: 0.3,
      },
      areaStyle: {
        color: FinancialColors.brand.primary,
        opacity: 0.1,
      },
    },
    fillerColor: "rgba(59, 130, 246, 0.15)",
    handleStyle: {
      color: FinancialColors.brand.primary,
      borderColor: FinancialColors.border.medium,
    },
    textStyle: {
      color: FinancialColors.text.tertiary,
      fontSize: 11,
    },
  } as any, // Type assertion for complex nested options

  // Timeline
  timeline: {
    lineStyle: {
      color: FinancialColors.border.light,
    },
    itemStyle: {
      color: FinancialColors.brand.primary,
    },
    controlStyle: {
      color: FinancialColors.brand.primary,
      borderColor: FinancialColors.brand.primary,
    },
    checkpointStyle: {
      color: FinancialColors.brand.accent,
      borderColor: FinancialColors.border.medium,
    },
    label: {
      color: FinancialColors.text.secondary,
    },
    emphasis: {
      itemStyle: {
        color: FinancialColors.brand.primary,
      },
      controlStyle: {
        color: FinancialColors.brand.primary,
        borderColor: FinancialColors.brand.primary,
      },
      label: {
        color: FinancialColors.text.primary,
      },
    },
  },
};

export default HedgeVisionDarkTheme;
