/**
 * ECharts Configuration Utilities for HedgeVision
 * Reusable chart configurations and helper functions
 */

import { EChartsOption } from "echarts";
import { HedgeVisionDarkTheme } from "./echarts-dark";
import { FinancialColors } from "./financial-colors";

/**
 * Get base chart configuration with HedgeVision theme
 */
export function getBaseChartConfig(
  customOptions: EChartsOption = {},
): EChartsOption {
  return {
    ...HedgeVisionDarkTheme,
    ...customOptions,
    animation: true,
    animationDuration: 300,
    animationEasing: "cubicOut",
  };
}

/**
 * Common tooltip configuration for financial charts
 */
export function getFinancialTooltipConfig(): EChartsOption["tooltip"] {
  return {
    trigger: "axis",
    axisPointer: {
      type: "cross",
      crossStyle: {
        color: FinancialColors.text.tertiary,
        opacity: 0.5,
      },
      lineStyle: {
        type: "dashed",
        color: FinancialColors.text.tertiary,
        opacity: 0.5,
      },
    },
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
  };
}

/**
 * Common grid configuration for consistent spacing
 */
export function getChartGridConfig(): EChartsOption["grid"] {
  return {
    left: "3%",
    right: "4%",
    bottom: "10%",
    top: "15%",
    containLabel: true,
  };
}

/**
 * Configuration for zoom/pan data zoom
 */
export function getDataZoomConfig(
  show: boolean = true,
): EChartsOption["dataZoom"] {
  return [
    {
      type: "inside",
      start: 0,
      end: 100,
      zoomOnMouseWheel: true,
      moveOnMouseMove: true,
    },
    ...(show
      ? [
          {
            type: "slider",
            show: true,
            start: 0,
            end: 100,
            height: 30,
            bottom: 10,
            backgroundColor: FinancialColors.background.card,
            fillerColor: "rgba(59, 130, 246, 0.15)",
            borderColor: FinancialColors.border.light,
            handleStyle: {
              color: FinancialColors.brand.primary,
            },
            textStyle: {
              color: FinancialColors.text.tertiary,
            },
          } as any,
        ]
      : []),
  ];
}

/**
 * Format large numbers with K, M, B suffixes
 */
export function formatLargeNumber(value: number): string {
  if (value >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(2)}K`;
  return value.toFixed(2);
}

/**
 * Format percentage values
 */
export function formatPercentage(value: number, decimals: number = 2): string {
  return `${(value * 100).toFixed(decimals)}%`;
}

/**
 * Format currency values
 */
export function formatCurrency(
  value: number,
  currency: string = "USD",
): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

/**
 * Format date for chart axis
 */
export function formatChartDate(
  date: string | Date,
  format: "short" | "medium" | "long" = "short",
): string {
  const d = typeof date === "string" ? new Date(date) : date;

  switch (format) {
    case "short":
      return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
    case "medium":
      return d.toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "2-digit",
      });
    case "long":
      return d.toLocaleDateString("en-US", {
        month: "long",
        day: "numeric",
        year: "numeric",
      });
    default:
      return d.toLocaleDateString();
  }
}

/**
 * Get color based on positive/negative value
 */
export function getValueColor(value: number, threshold: number = 0): string {
  if (value > threshold) return FinancialColors.financial.bullish;
  if (value < threshold) return FinancialColors.financial.bearish;
  return FinancialColors.financial.neutral;
}

/**
 * Calculate dynamic font size based on chart dimensions and data density
 * @param baseSize - Base font size in pixels
 * @param containerWidth - Width of the chart container
 * @param containerHeight - Height of the chart container
 * @param dataPoints - Number of data points (for density calculation)
 * @returns Scaled font size (minimum 8px)
 */
export function getDynamicFontSize(
  baseSize: number,
  containerWidth: number = 800,
  containerHeight: number = 600,
  dataPoints: number = 10,
): number {
  let scaleFactor = 1;

  // Scale based on data density
  if (dataPoints > 100) {
    scaleFactor = 0.5;
  } else if (dataPoints > 50) {
    scaleFactor = 0.6;
  } else if (dataPoints > 30) {
    scaleFactor = 0.7;
  } else if (dataPoints > 20) {
    scaleFactor = 0.8;
  } else if (dataPoints > 10) {
    scaleFactor = 0.9;
  }

  // Adjust for container width
  if (containerWidth < 400) {
    scaleFactor *= 0.7;
  } else if (containerWidth < 600) {
    scaleFactor *= 0.8;
  } else if (containerWidth < 800) {
    scaleFactor *= 0.9;
  }

  // Adjust for container height
  if (containerHeight < 400) {
    scaleFactor *= 0.9;
  }

  return Math.max(Math.round(baseSize * scaleFactor), 8); // Minimum 8px
}

/**
 * Get responsive font sizes for chart elements
 * @param containerWidth - Width of the chart container
 * @param containerHeight - Height of the chart container
 * @param dataPoints - Number of data points
 * @returns Object with font sizes for different chart elements
 */
export function getResponsiveFontSizes(
  containerWidth: number = 800,
  containerHeight: number = 600,
  dataPoints: number = 10,
) {
  return {
    title: getDynamicFontSize(18, containerWidth, containerHeight, dataPoints),
    subtitle: getDynamicFontSize(
      14,
      containerWidth,
      containerHeight,
      dataPoints,
    ),
    axisLabel: getDynamicFontSize(
      11,
      containerWidth,
      containerHeight,
      dataPoints,
    ),
    axisName: getDynamicFontSize(
      12,
      containerWidth,
      containerHeight,
      dataPoints,
    ),
    legend: getDynamicFontSize(12, containerWidth, containerHeight, dataPoints),
    tooltip: getDynamicFontSize(
      13,
      containerWidth,
      containerHeight,
      dataPoints,
    ),
    seriesLabel: getDynamicFontSize(
      10,
      containerWidth,
      containerHeight,
      dataPoints,
    ),
    emphasis: getDynamicFontSize(
      12,
      containerWidth,
      containerHeight,
      dataPoints,
    ),
  };
}

/**
 * Configuration for correlation heatmap
 */
export function getCorrelationHeatmapConfig(
  data: Array<[number, number, number]>,
): EChartsOption {
  return {
    ...getBaseChartConfig(),
    tooltip: {
      position: "top",
      formatter: (params: any) => {
        const value = params.data[2];
        return `<strong>Correlation:</strong> ${value.toFixed(3)}`;
      },
    },
    visualMap: {
      min: -1,
      max: 1,
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: "5%",
      inRange: {
        color: [
          FinancialColors.correlation.strongNegative,
          FinancialColors.correlation.negative,
          FinancialColors.correlation.neutral,
          FinancialColors.correlation.positive,
          FinancialColors.correlation.strongPositive,
        ],
      },
      textStyle: {
        color: FinancialColors.text.secondary,
      },
    },
    series: [
      {
        type: "heatmap",
        data: data,
        label: {
          show: true,
          fontSize: 10,
          color: FinancialColors.text.primary,
          formatter: (params: any) => params.data[2].toFixed(2),
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: "rgba(0, 0, 0, 0.5)",
          },
        },
      },
    ],
  };
}

/**
 * Configuration for line chart with multiple series
 */
export function getLineChartConfig(options: {
  xAxisData: string[];
  series: Array<{ name: string; data: number[]; color?: string }>;
  title?: string;
  yAxisLabel?: string;
}): EChartsOption {
  const { xAxisData, series, title, yAxisLabel } = options;

  return {
    ...getBaseChartConfig(),
    title: title
      ? {
          text: title,
          left: "center",
          textStyle: {
            color: FinancialColors.text.primary,
            fontSize: 18,
            fontWeight: 600,
          },
        }
      : undefined,
    tooltip: getFinancialTooltipConfig(),
    legend: {
      data: series.map((s) => s.name),
      top: title ? "10%" : "5%",
      textStyle: {
        color: FinancialColors.text.secondary,
      },
    },
    grid: getChartGridConfig(),
    xAxis: {
      type: "category",
      data: xAxisData,
      axisLabel: {
        color: FinancialColors.text.tertiary,
        fontSize: 11,
      },
    },
    yAxis: {
      type: "value",
      name: yAxisLabel,
      nameTextStyle: {
        color: FinancialColors.text.secondary,
      },
      axisLabel: {
        color: FinancialColors.text.tertiary,
        fontSize: 11,
      },
    },
    series: series.map((s, index) => ({
      name: s.name,
      type: "line",
      data: s.data,
      smooth: true,
      lineStyle: {
        width: 2,
        color:
          s.color ||
          FinancialColors.series[index % FinancialColors.series.length],
      },
      itemStyle: {
        color:
          s.color ||
          FinancialColors.series[index % FinancialColors.series.length],
      },
    })),
    dataZoom: getDataZoomConfig(true),
  };
}

/**
 * Loading animation configuration
 */
export function getLoadingConfig() {
  return {
    text: "Loading...",
    color: FinancialColors.brand.primary,
    textColor: FinancialColors.text.primary,
    maskColor: "rgba(15, 23, 42, 0.8)",
    zlevel: 0,
  };
}

/**
 * Data decimation for large datasets
 * Reduces data points while preserving visual accuracy
 *
 * @param data - Array of data points [timestamp, value]
 * @param targetPoints - Maximum number of points to return (default: 1000)
 * @param method - Decimation method: 'lttb' (Largest Triangle Three Buckets) or 'average'
 * @returns Decimated data array
 *
 * @example
 * const largeDataset = generateData(10000); // 10k points
 * const optimizedData = decimateData(largeDataset, 1000); // Reduce to 1k points
 */
export function decimateData<T extends [number, number]>(
  data: T[],
  targetPoints: number = 1000,
  method: "lttb" | "average" = "lttb",
): T[] {
  if (data.length <= targetPoints) {
    return data;
  }

  if (method === "average") {
    return decimateByAverage(data, targetPoints);
  } else {
    return decimateByLTTB(data, targetPoints);
  }
}

/**
 * Largest Triangle Three Buckets (LTTB) algorithm
 * Maintains visual appearance while reducing points
 */
function decimateByLTTB<T extends [number, number]>(
  data: T[],
  targetPoints: number,
): T[] {
  if (data.length <= targetPoints) {
    return data;
  }

  const result: T[] = [];
  const bucketSize = (data.length - 2) / (targetPoints - 2);

  // Always keep first point
  result.push(data[0]);

  let a = 0; // Previous selected point

  for (let i = 0; i < targetPoints - 2; i++) {
    // Calculate point average for next bucket
    let avgX = 0;
    let avgY = 0;
    const avgRangeStart = Math.floor((i + 1) * bucketSize) + 1;
    const avgRangeEnd = Math.min(
      Math.floor((i + 2) * bucketSize) + 1,
      data.length,
    );
    const avgRangeLength = avgRangeEnd - avgRangeStart;

    for (let j = avgRangeStart; j < avgRangeEnd; j++) {
      avgX += data[j][0];
      avgY += data[j][1];
    }
    avgX /= avgRangeLength;
    avgY /= avgRangeLength;

    // Get the range for this bucket
    const rangeStart = Math.floor(i * bucketSize) + 1;
    const rangeEnd = Math.min(
      Math.floor((i + 1) * bucketSize) + 1,
      data.length,
    );

    // Point a
    const pointAX = data[a][0];
    const pointAY = data[a][1];

    let maxArea = -1;
    let maxAreaPoint = rangeStart;

    for (let j = rangeStart; j < rangeEnd; j++) {
      // Calculate triangle area over three buckets
      const area =
        Math.abs(
          (pointAX - avgX) * (data[j][1] - pointAY) -
            (pointAX - data[j][0]) * (avgY - pointAY),
        ) * 0.5;

      if (area > maxArea) {
        maxArea = area;
        maxAreaPoint = j;
      }
    }

    result.push(data[maxAreaPoint]);
    a = maxAreaPoint;
  }

  // Always keep last point
  result.push(data[data.length - 1]);

  return result as T[];
}

/**
 * Simple average-based decimation
 * Groups data into buckets and averages each bucket
 */
function decimateByAverage<T extends [number, number]>(
  data: T[],
  targetPoints: number,
): T[] {
  const result: T[] = [];
  const bucketSize = Math.ceil(data.length / targetPoints);

  for (let i = 0; i < data.length; i += bucketSize) {
    const bucket = data.slice(i, i + bucketSize);
    const avgX =
      bucket.reduce((sum, point) => sum + point[0], 0) / bucket.length;
    const avgY =
      bucket.reduce((sum, point) => sum + point[1], 0) / bucket.length;
    result.push([avgX, avgY] as T);
  }

  return result;
}

/**
 * Calculate optimal point count based on container width
 * Ensures ~2 pixels per data point for optimal rendering
 *
 * @param containerWidth - Chart container width in pixels
 * @param pixelsPerPoint - Pixels per data point (default: 2)
 * @returns Optimal number of data points
 */
export function getOptimalPointCount(
  containerWidth: number,
  pixelsPerPoint: number = 2,
): number {
  return Math.floor(containerWidth / pixelsPerPoint);
}

/**
 * Memoize chart data to prevent unnecessary recalculations
 * Use with React.useMemo for best results
 *
 * @example
 * const chartData = useMemo(() =>
 *   memoizeChartData(rawData, 'price-chart-key'),
 *   [rawData]
 * );
 */
const chartDataCache = new Map<string, any>();

export function memoizeChartData<T>(
  data: T,
  cacheKey: string,
  ttl: number = 60000, // 1 minute default
): T {
  const cached = chartDataCache.get(cacheKey);

  if (cached && Date.now() - cached.timestamp < ttl) {
    return cached.data;
  }

  chartDataCache.set(cacheKey, {
    data,
    timestamp: Date.now(),
  });

  // Clean up old cache entries (keep last 50)
  if (chartDataCache.size > 50) {
    const entries = Array.from(chartDataCache.entries());
    entries.sort((a, b) => a[1].timestamp - b[1].timestamp);
    entries.slice(0, entries.length - 50).forEach(([key]) => {
      chartDataCache.delete(key);
    });
  }

  return data;
}

/**
 * Clear chart data cache
 * Call when data source changes or on component unmount
 */
export function clearChartCache(cacheKey?: string) {
  if (cacheKey) {
    chartDataCache.delete(cacheKey);
  } else {
    chartDataCache.clear();
  }
}

export default {
  getBaseChartConfig,
  getFinancialTooltipConfig,
  getChartGridConfig,
  getDataZoomConfig,
  getCorrelationHeatmapConfig,
  getLineChartConfig,
  getLoadingConfig,
  formatLargeNumber,
  formatPercentage,
  formatCurrency,
  formatChartDate,
  getValueColor,
  getDynamicFontSize,
  getResponsiveFontSizes,
  decimateData,
  getOptimalPointCount,
  memoizeChartData,
  clearChartCache,
};
