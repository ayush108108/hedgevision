import React, { useEffect, useRef, useState } from "react";
import * as echarts from "echarts";
import { HedgeVisionDarkTheme } from "../../themes/echarts-dark";
import { FinancialColors } from "../../themes/financial-colors";
import { getResponsiveFontSizes } from "../../themes/echarts-config";

export interface ScatterPoint {
  x: number;
  y: number;
}

export interface RegressionMetrics {
  beta?: number;
  alpha?: number;
  r_squared?: number;
  std_error?: number;
  hedge_ratio?: number;
  intercept?: number;
  scatter_data?: ScatterPoint[];
}

interface Props {
  metrics: RegressionMetrics;
  asset1Name: string;
  asset2Name: string;
  height?: number;
}

export function RegressionChart({
  metrics,
  asset1Name,
  asset2Name,
  height = 400,
}: Props) {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);
  const [containerSize, setContainerSize] = useState({
    width: 800,
    height: 400,
  });

  const scatterData = metrics.scatter_data || [];
  const beta = metrics.hedge_ratio || metrics.beta || 0;
  const alpha = metrics.intercept || metrics.alpha || 0;

  useEffect(() => {
    if (!chartRef.current || !scatterData.length) return;

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

    // Prepare scatter data
    const scatter = scatterData.map((d) => [d.x, d.y]);

    // Calculate regression line points
    const xValues = scatterData.map((d) => d.x);
    const minX = Math.min(...xValues);
    const maxX = Math.max(...xValues);
    const regressionLine = [
      [minX, alpha + beta * minX],
      [maxX, alpha + beta * maxX],
    ];

    // Get responsive font sizes
    const fonts = getResponsiveFontSizes(
      containerSize.width,
      containerSize.height,
      scatterData.length,
    );

    const option: echarts.EChartsOption = {
      animation: true,
      animationDuration: 300,

      title: {
        text: `${asset2Name} vs ${asset1Name}`,
        left: "center",
        top: 10,
        textStyle: {
          color: FinancialColors.text.primary,
          fontSize: fonts.title,
          fontWeight: 600,
        },
      },

      tooltip: {
        trigger: "item",
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
          if (params.seriesName === "Regression Line") {
            return `<div>
              <strong>Regression Line</strong><br/>
              y = ${beta.toFixed(3)}x + ${alpha.toFixed(3)}<br/>
              R² = ${(metrics.r_squared || 0).toFixed(3)}
            </div>`;
          }
          const [x, y] = params.data;
          return `<div>
            <strong>${asset1Name}:</strong> ${x.toFixed(2)}<br/>
            <strong>${asset2Name}:</strong> ${y.toFixed(2)}
          </div>`;
        },
      },

      grid: {
        left: "10%",
        right: "5%",
        bottom: "15%",
        top: "20%",
        containLabel: true,
      },

      xAxis: {
        type: "value",
        name: asset1Name,
        nameLocation: "middle",
        nameGap: 30,
        nameTextStyle: {
          color: FinancialColors.text.secondary,
          fontSize: fonts.axisName,
          fontWeight: 600,
        },
        axisLabel: {
          color: FinancialColors.text.tertiary,
          fontSize: fonts.axisLabel,
          formatter: (value: number) => value.toFixed(1),
        },
        axisLine: {
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

      yAxis: {
        type: "value",
        name: asset2Name,
        nameLocation: "middle",
        nameGap: 50,
        nameTextStyle: {
          color: FinancialColors.text.secondary,
          fontSize: fonts.axisName,
          fontWeight: 600,
        },
        axisLabel: {
          color: FinancialColors.text.tertiary,
          fontSize: fonts.axisLabel,
          formatter: (value: number) => value.toFixed(1),
        },
        axisLine: {
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
        {
          name: "Data Points",
          type: "scatter",
          data: scatter,
          symbolSize: 6,
          itemStyle: {
            color: FinancialColors.brand.primary,
            opacity: 0.7,
          },
          emphasis: {
            scale: true,
            itemStyle: {
              color: FinancialColors.brand.accent,
              opacity: 1,
              shadowBlur: 10,
              shadowColor: "rgba(139, 92, 246, 0.5)",
            },
          },
        },
        {
          name: "Regression Line",
          type: "line",
          data: regressionLine,
          lineStyle: {
            color: FinancialColors.financial.bearish,
            width: 2,
            type: "solid",
          },
          symbol: "none",
          emphasis: {
            disabled: true,
          },
          z: 10,
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
  }, [
    metrics,
    asset1Name,
    asset2Name,
    scatterData,
    beta,
    alpha,
    containerSize.width,
    containerSize.height,
  ]);

  if (!scatterData.length) {
    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
          <div className="bg-slate-700/50 p-3 rounded-lg border border-slate-600/50">
            <div className="font-medium text-slate-400">Beta</div>
            <div className="text-lg text-white">{beta.toFixed(3)}</div>
          </div>
          <div className="bg-slate-700/50 p-3 rounded-lg border border-slate-600/50">
            <div className="font-medium text-slate-400">Alpha</div>
            <div className="text-lg text-white">{alpha.toFixed(3)}</div>
          </div>
          <div className="bg-slate-700/50 p-3 rounded-lg border border-slate-600/50">
            <div className="font-medium text-slate-400">R²</div>
            <div className="text-lg text-white">
              {(metrics.r_squared || 0).toFixed(3)}
            </div>
          </div>
          <div className="bg-slate-700/50 p-3 rounded-lg border border-slate-600/50">
            <div className="font-medium text-slate-400">Std Error</div>
            <div className="text-lg text-white">
              {(metrics.std_error || 0).toFixed(3)}
            </div>
          </div>
        </div>
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
          <p>No regression data available.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Metrics Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
        <div className="bg-slate-700/50 p-3 rounded-lg border border-slate-600/50 hover:border-blue-500/50 transition-colors">
          <div className="font-medium text-slate-400">Beta (Hedge Ratio)</div>
          <div className="text-lg text-white font-semibold">
            {beta.toFixed(3)}
          </div>
        </div>
        <div className="bg-slate-700/50 p-3 rounded-lg border border-slate-600/50 hover:border-blue-500/50 transition-colors">
          <div className="font-medium text-slate-400">Alpha (Intercept)</div>
          <div className="text-lg text-white font-semibold">
            {alpha.toFixed(3)}
          </div>
        </div>
        <div className="bg-slate-700/50 p-3 rounded-lg border border-slate-600/50 hover:border-blue-500/50 transition-colors">
          <div className="font-medium text-slate-400">R² (Fit Quality)</div>
          <div
            className={`text-lg font-semibold ${(metrics.r_squared || 0) > 0.7 ? "text-green-400" : (metrics.r_squared || 0) > 0.4 ? "text-yellow-400" : "text-red-400"}`}
          >
            {(metrics.r_squared || 0).toFixed(3)}
          </div>
        </div>
        <div className="bg-slate-700/50 p-3 rounded-lg border border-slate-600/50 hover:border-blue-500/50 transition-colors">
          <div className="font-medium text-slate-400">Std Error</div>
          <div className="text-lg text-white font-semibold">
            {(metrics.std_error || 0).toFixed(3)}
          </div>
        </div>
      </div>

      {/* Chart */}
      <div
        ref={chartRef}
        style={{
          width: "100%",
          height,
        }}
      />
    </div>
  );
}
