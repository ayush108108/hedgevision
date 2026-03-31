import React, { useEffect, useRef, useState } from "react";
import * as echarts from "echarts";
import { HedgeVisionDarkTheme } from "../../themes/echarts-dark";
import { FinancialColors } from "../../themes/financial-colors";
import {
  getResponsiveFontSizes,
  formatChartDate,
} from "../../themes/echarts-config";

export interface BetaPoint {
  date: string;
  beta: number | null;
}

interface Props {
  data: BetaPoint[];
  assetName: string;
  benchmarkName: string;
  height?: number;
  title?: string;
}

export function BetaChart({
  data,
  assetName,
  benchmarkName,
  height = 350,
  title,
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
    const betas = data.map((d) => d.beta);

    // Get responsive font sizes
    const fonts = getResponsiveFontSizes(
      containerSize.width,
      containerSize.height,
      data.length,
    );

    // Calculate average beta for reference line
    const validBetas = betas.filter((b) => b !== null) as number[];
    const avgBeta =
      validBetas.length > 0
        ? validBetas.reduce((sum, b) => sum + b, 0) / validBetas.length
        : 1.0;

    const chartTitle =
      title || `Rolling Beta: ${assetName} vs ${benchmarkName}`;

    const option: echarts.EChartsOption = {
      animation: true,
      animationDuration: 400,

      title: {
        text: chartTitle,
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
            if (
              value !== null &&
              value !== undefined &&
              param.seriesName !== "Beta = 1.0" &&
              param.seriesName !== "Average Beta"
            ) {
              const betaColor =
                value > 1
                  ? FinancialColors.financial.bullish
                  : value < 1
                    ? FinancialColors.financial.bearish
                    : FinancialColors.financial.neutral;
              content += `
                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 4px;">
                  <span style="display: flex; align-items: center;">
                    <span style="display: inline-block; width: 10px; height: 10px; border-radius: 50%; 
                                 background: ${param.color}; margin-right: 8px;"></span>
                    Beta:
                  </span>
                  <strong style="margin-left: 16px; color: ${betaColor};">${value.toFixed(3)}</strong>
                </div>
              `;
              // Add interpretation
              const interpretation =
                value > 1.2
                  ? "Higher volatility than benchmark"
                  : value < 0.8
                    ? "Lower volatility than benchmark"
                    : "Similar volatility to benchmark";
              content += `
                <div style="margin-top: 4px; font-size: 0.85em; color: ${FinancialColors.text.tertiary};">
                  ${interpretation}
                </div>
              `;
            }
          });

          return content;
        },
      },

      legend: {
        data: [`${assetName} Beta`, "Beta = 1.0", "Average Beta"],
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
        top: "20%",
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
          fillerColor: "rgba(139, 92, 246, 0.15)",
          borderColor: FinancialColors.border.medium,
          handleStyle: {
            color: FinancialColors.brand.accent,
          },
          textStyle: {
            color: FinancialColors.text.tertiary,
            fontSize: fonts.axisLabel - 1,
          },
          dataBackground: {
            lineStyle: { color: FinancialColors.border.light },
            areaStyle: { color: "rgba(139, 92, 246, 0.05)" },
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
        name: "Beta Coefficient",
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

      series: [
        // Beta line
        {
          name: `${assetName} Beta`,
          type: "line",
          data: betas,
          smooth: true,
          symbol: "circle",
          symbolSize: 6,
          showSymbol: false,
          lineStyle: {
            width: 2.5,
            color: FinancialColors.brand.accent,
          },
          itemStyle: {
            color: FinancialColors.brand.accent,
          },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: "rgba(139, 92, 246, 0.25)" },
              { offset: 1, color: "rgba(139, 92, 246, 0.05)" },
            ]),
          },
          emphasis: {
            focus: "series",
            lineStyle: {
              width: 3.5,
            },
          },
          markLine: {
            silent: true,
            symbol: "none",
            lineStyle: {
              color: FinancialColors.financial.neutral,
              type: "solid",
              width: 1.5,
              opacity: 0.6,
            },
            label: {
              show: true,
              position: "end",
              formatter: "β = 1.0",
              color: FinancialColors.text.tertiary,
              fontSize: fonts.axisLabel - 1,
            },
            data: [{ yAxis: 1.0 }],
          },
        },
        // Beta = 1.0 reference line (invisible series for legend)
        {
          name: "Beta = 1.0",
          type: "line",
          data: [],
          lineStyle: {
            color: FinancialColors.financial.neutral,
            type: "solid",
            width: 1.5,
          },
        },
        // Average beta reference line
        {
          name: "Average Beta",
          type: "line",
          data: [],
          lineStyle: {
            color: FinancialColors.brand.warning,
            type: "dashed",
            width: 1.5,
          },
          markLine: {
            silent: true,
            symbol: "none",
            lineStyle: {
              color: FinancialColors.brand.warning,
              type: "dashed",
              width: 1.5,
              opacity: 0.5,
            },
            label: {
              show: true,
              position: "end",
              formatter: `Avg: ${avgBeta.toFixed(2)}`,
              color: FinancialColors.text.tertiary,
              fontSize: fonts.axisLabel - 1,
            },
            data: [{ yAxis: avgBeta }],
          },
        },
      ],
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
  }, [data, assetName, benchmarkName, title, containerSize.width, containerSize.height]);

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
        <p>No beta data available.</p>
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
