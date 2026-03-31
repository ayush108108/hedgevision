import React, { useEffect, useRef, useState } from "react";
import * as echarts from "echarts";
import { HedgeVisionDarkTheme } from "../../themes/echarts-dark";
import { FinancialColors } from "../../themes/financial-colors";
import {
  getResponsiveFontSizes,
  formatChartDate,
} from "../../themes/echarts-config";
import type { MetricType, RollingMetricPoint } from "../../services/rollingMetrics";
import { getMetricOption } from "../controls/MetricSelector";

interface Props {
  data: RollingMetricPoint[];
  assetName: string;
  benchmarkName?: string;
  height?: number;
  rollingWindow?: number;
  dataSource?: "cached" | "computed";
  cachedAt?: string;
}

export function RollingMetricsChart({
  data,
  assetName,
  benchmarkName,
  height = 400,
  rollingWindow = 60,
  dataSource = "computed",
  cachedAt,
}: Props) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  const [containerSize, setContainerSize] = useState({
    width: 800,
    height: 400,
  });

  useEffect(() => {
    if (!chartRef.current || !data.length) return;

    // Update container size
    const updateSize = () => {
      if (chartRef.current) {
        setContainerSize({
          width: chartRef.current.clientWidth,
          height: chartRef.current.clientHeight,
        });
      }
    };
    updateSize();

    // Initialize chart
    if (chartInstance.current) {
      chartInstance.current.dispose();
    }
    chartInstance.current = echarts.init(
      chartRef.current,
      HedgeVisionDarkTheme as any,
    );

    // Group data by metric type
    const metricGroups = new Map<MetricType, RollingMetricPoint[]>();
    data.forEach((point) => {
      if (!metricGroups.has(point.metric)) {
        metricGroups.set(point.metric, []);
      }
      metricGroups.get(point.metric)!.push(point);
    });

    // Get all unique dates
    const allDates = Array.from(new Set(data.map((d) => d.date))).sort();

    // Get responsive font sizes
    const fonts = getResponsiveFontSizes(
      containerSize.width,
      containerSize.height,
      allDates.length,
    );

    // Build series for each metric
    const series: any[] = [];
    const legendData: string[] = [];

    metricGroups.forEach((points, metricType) => {
      const metricOption = getMetricOption(metricType);
      if (!metricOption) return;

      // Create data array aligned with allDates
      const metricData = allDates.map((date) => {
        const point = points.find((p) => p.date === date);
        return point ? point.value : null;
      });

      legendData.push(metricOption.name);

      series.push({
        name: metricOption.name,
        type: "line",
        data: metricData,
        smooth: true,
        symbol: "circle",
        symbolSize: 6,
        showSymbol: false,
        lineStyle: {
          width: 2.5,
          color: metricOption.color,
        },
        itemStyle: {
          color: metricOption.color,
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: `${metricOption.color}40` },
            { offset: 1, color: `${metricOption.color}08` },
          ]),
        },
        emphasis: {
          focus: "series",
          lineStyle: {
            width: 3.5,
          },
        },
      });
    });

    const option: echarts.EChartsOption = {
      animation: true,
      animationDuration: 400,
      // Title/subtext intentionally omitted; the page renders a header above the chart

      tooltip: {
        trigger: "axis",
        axisPointer: {
          type: "cross",
          crossStyle: {
            color: FinancialColors.text.tertiary,
            opacity: 0.5,
          },
        },
        backgroundColor: FinancialColors.background.overlay,
        borderColor: FinancialColors.border.medium,
        borderWidth: 1,
        textStyle: {
          color: FinancialColors.text.primary,
          fontSize: fonts.tooltip,
        },
        padding: [12, 16],
        extraCssText: `
          backdrop-filter: blur(12px);
          border-radius: 8px;
          box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
        `,
        formatter: (params: any) => {
          if (!Array.isArray(params) || params.length === 0) return "";

          const date = params[0].axisValue;
          let content = `<div style="font-weight: 600; margin-bottom: 8px;">${formatChartDate(date, "medium")}</div>`;

          params.forEach((param: any) => {
            const value = param.value;
            if (value !== null && value !== undefined) {
              // Find metric option for formatting
              const metricName = param.seriesName;
              const metricOption = Array.from(metricGroups.keys())
                .map(getMetricOption)
                .find((opt) => opt?.name === metricName);

              const formattedValue = metricOption?.format?.(value) ?? value.toFixed(3);

              content += `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
                  <span style="display: flex; align-items: center;">
                    <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; 
                                 background: ${param.color}; margin-right: 8px;"></span>
                    ${param.seriesName}:
                  </span>
                  <strong style="margin-left: 16px;">${formattedValue}</strong>
                </div>
              `;
            }
          });

          return content;
        },
      },

      legend: {
        data: legendData,
        top: 40,
        left: "center",
        textStyle: {
          color: FinancialColors.text.secondary,
          fontSize: fonts.legend,
        },
        itemWidth: 20,
        itemHeight: 10,
      },

      grid: {
        left: "3%",
        right: "4%",
        bottom: "12%",
        top: "22%",
        containLabel: true,
      },

      dataZoom: [
        {
          type: "inside",
          start: 0,
          end: 100,
          zoomOnMouseWheel: true,
          moveOnMouseMove: true,
        },
        {
          type: "slider",
          start: 0,
          end: 100,
          height: 25,
          bottom: 10,
          backgroundColor: FinancialColors.background.card,
          fillerColor: "rgba(59, 130, 246, 0.15)",
          borderColor: FinancialColors.border.medium,
          handleStyle: {
            color: FinancialColors.brand.primary,
          },
          textStyle: {
            color: FinancialColors.text.tertiary,
            fontSize: fonts.axisLabel - 1,
          },
          dataBackground: {
            lineStyle: { color: FinancialColors.border.light },
            areaStyle: { color: "rgba(59, 130, 246, 0.05)" },
          },
        } as any,
      ],

      xAxis: {
        type: "category",
        data: allDates,
        axisLabel: {
          color: FinancialColors.text.tertiary,
          fontSize: fonts.axisLabel,
          // Ensure we handle the value correctly if it's already a string or index
          formatter: (value: any) => {
            // In 'category' axis, 'value' is the string from the 'data' array at that index
            return formatChartDate(value, "short");
          },
        },
        axisLine: {
          lineStyle: {
            color: FinancialColors.border.medium,
          },
        },
        splitLine: {
          show: false,
        },
      },

      yAxis: {
        type: "value",
        name: "Metric Value",
        nameTextStyle: {
          color: FinancialColors.text.secondary,
          fontSize: fonts.axisName,
          padding: [0, 0, 0, 10],
        },
        axisLabel: {
          color: FinancialColors.text.tertiary,
          fontSize: fonts.axisLabel,
          formatter: (value: number) => value.toFixed(2),
        },
        axisLine: {
          show: true,
          lineStyle: {
            color: FinancialColors.border.medium,
          },
        },
        splitLine: {
          lineStyle: {
            type: "dashed",
            color: FinancialColors.border.light,
            opacity: 0.3,
          },
        },
      },

      series: series,
    };

    chartInstance.current.setOption(option);

    // Handle resize
    const handleResize = () => {
      chartInstance.current?.resize();
      updateSize();
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      chartInstance.current?.dispose();
    };
  }, [data, assetName, benchmarkName, rollingWindow, dataSource, cachedAt, containerSize.width, containerSize.height]);

  if (!data.length) {
    return (
      <div
        style={{
          width: "100%",
          height,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: FinancialColors.text.tertiary,
        }}
      >
        <p>No metrics data available. Select metrics to display.</p>
      </div>
    );
  }

  return (
    <div
      ref={chartRef}
      style={{
        width: "100%",
        height,
      }}
    />
  );
}
