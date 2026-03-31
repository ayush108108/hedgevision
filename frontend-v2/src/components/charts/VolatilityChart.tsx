import React, { useEffect, useRef, useState } from "react";
import * as echarts from "echarts";
import { HedgeVisionDarkTheme } from "../../themes/echarts-dark";
import { FinancialColors } from "../../themes/financial-colors";
import {
  getResponsiveFontSizes,
  formatPercentage,
  formatChartDate,
} from "../../themes/echarts-config";

export interface VolatilityPoint {
  date: string;
  volatility: number | null;
}

interface Props {
  data: VolatilityPoint[];
  assetName: string;
  benchmarkData?: VolatilityPoint[]; // Optional benchmark comparison
  benchmarkName?: string;
  height?: number;
  title?: string;
}

export function VolatilityChart({
  data,
  assetName,
  benchmarkData,
  benchmarkName,
  height = 350,
  title = "Rolling Volatility",
}: Props) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  const [containerSize, setContainerSize] = useState({
    width: 800,
    height: 350,
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

    // Prepare data
    const dates = data.map((d) => d.date);
    const volatilities = data.map((d) => d.volatility);

    // Get responsive font sizes
    const fonts = getResponsiveFontSizes(
      containerSize.width,
      containerSize.height,
      data.length,
    );

    // Build series array
    const series: any[] = [
      {
        name: assetName,
        type: "line",
        data: volatilities,
        smooth: true,
        symbol: "circle",
        symbolSize: 6,
        showSymbol: false,
        lineStyle: {
          width: 2.5,
          color: FinancialColors.brand.primary,
        },
        itemStyle: {
          color: FinancialColors.brand.primary,
        },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: "rgba(59, 130, 246, 0.3)" },
            { offset: 1, color: "rgba(59, 130, 246, 0.05)" },
          ]),
        },
        emphasis: {
          focus: "series",
          lineStyle: {
            width: 3.5,
          },
        },
      },
    ];

    // Add benchmark series if provided
    if (benchmarkData && benchmarkData.length > 0 && benchmarkName) {
      const benchmarkVolatilities = benchmarkData.map((d) => d.volatility);
      series.push({
        name: benchmarkName,
        type: "line",
        data: benchmarkVolatilities,
        smooth: true,
        symbol: "circle",
        symbolSize: 5,
        showSymbol: false,
        lineStyle: {
          width: 2,
          color: FinancialColors.brand.warning,
          type: "dashed",
        },
        itemStyle: {
          color: FinancialColors.brand.warning,
        },
        emphasis: {
          focus: "series",
          lineStyle: {
            width: 3,
          },
        },
      });
    }

    const option: echarts.EChartsOption = {
      animation: true,
      animationDuration: 400,

      title: {
        text: title,
        left: "center",
        top: 5,
        textStyle: {
          color: FinancialColors.text.primary,
          fontSize: fonts.title,
          fontWeight: 600,
        },
      },

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
              content += `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
                  <span style="display: flex; align-items: center;">
                    <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; 
                                 background: ${param.color}; margin-right: 8px;"></span>
                    ${param.seriesName}:
                  </span>
                  <strong style="margin-left: 16px;">${formatPercentage(value * 100)}</strong>
                </div>
              `;
            }
          });

          return content;
        },
      },

      legend: {
        data: series.map((s) => s.name),
        top: 35,
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
        top: benchmarkData ? "20%" : "18%",
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
        data: dates,
        axisLabel: {
          color: FinancialColors.text.tertiary,
          fontSize: fonts.axisLabel,
          formatter: (value: string) => formatChartDate(value, "short"),
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
        name: "Volatility (%)",
        nameTextStyle: {
          color: FinancialColors.text.secondary,
          fontSize: fonts.axisName,
          padding: [0, 0, 0, 10],
        },
        axisLabel: {
          color: FinancialColors.text.tertiary,
          fontSize: fonts.axisLabel,
          formatter: (value: number) => formatPercentage(value * 100),
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
  }, [
    data,
    assetName,
    benchmarkData,
    benchmarkName,
    title,
    containerSize.width,
    containerSize.height,
  ]);

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
        <p>No volatility data available.</p>
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
