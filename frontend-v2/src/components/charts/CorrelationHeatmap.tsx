import React, {
  useEffect,
  useRef,
  useCallback,
  useState,
  useMemo,
} from "react";
import * as echarts from "echarts";
import { useNavigate } from "react-router-dom";
import {
  FinancialColors,
  getCorrelationColor,
} from "../../themes/financial-colors";
import { HedgeVisionDarkTheme } from "../../themes/echarts-dark";
import { useThrottle } from "../../hooks/useThrottle";
import { decimateData, memoizeChartData } from "../../themes/echarts-config";
import { Maximize2, Minimize2, ZoomIn, ZoomOut, RotateCcw } from "lucide-react";

export interface CorrelationHeatmapProps {
  assets: string[];
  matrix: Record<string, Record<string, number>>;
  height?: number;
  onCellClick?: (asset1: string, asset2: string, correlation: number) => void;
}

export const CorrelationHeatmap: React.FC<CorrelationHeatmapProps> = ({
  assets,
  matrix,
  height = 600,
  onCellClick,
}) => {
  const ref = useRef<HTMLDivElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const chart = useRef<echarts.ECharts | null>(null);
  const navigate = useNavigate();
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [zoomLevel, setZoomLevel] = useState(100);

  // Throttled resize handler for performance (limit to once per 200ms)
  const handleResize = useThrottle(() => {
    chart.current?.resize();
  }, 200);

  const handleCellClick = useCallback(
    (params: any) => {
      const asset1 = assets[params.data[0]];
      const asset2 = assets[params.data[1]];
      const correlation = params.data[2];

      // Skip self-correlation cells
      if (asset1 === asset2) return;

      // Custom callback if provided
      if (onCellClick) {
        onCellClick(asset1, asset2, correlation);
      } else {
        // Default: navigate to pair analysis with rolling correlation pre-selected
        navigate(`/pair-analysis?asset1=${asset1}&asset2=${asset2}&metric=correlation`);
      }
    },
    [assets, navigate, onCellClick],
  );

  const toggleFullscreen = useCallback(() => {
    if (!containerRef.current) return;

    if (!isFullscreen) {
      if (containerRef.current.requestFullscreen) {
        containerRef.current.requestFullscreen();
      }
    } else {
      if (document.exitFullscreen) {
        document.exitFullscreen();
      }
    }
    setIsFullscreen(!isFullscreen);

    // Resize chart after fullscreen toggle
    setTimeout(() => {
      chart.current?.resize();
    }, 100);
  }, [isFullscreen]);

  const handleZoomIn = useCallback(() => {
    const newZoom = Math.min(zoomLevel + 20, 200);
    setZoomLevel(newZoom);

    if (chart.current) {
      const option = chart.current.getOption() as any;
      const currentDataZoom = option.dataZoom || [];

      // Adjust dataZoom to zoom in (reduce the end value)
      const range = 100 * (100 / newZoom);
      chart.current.setOption({
        dataZoom: [
          { ...currentDataZoom[0], end: Math.min(range, 100) },
          { ...currentDataZoom[1], end: Math.min(range, 100) },
        ],
      });
    }
  }, [zoomLevel]);

  const handleZoomOut = useCallback(() => {
    const newZoom = Math.max(zoomLevel - 20, 50);
    setZoomLevel(newZoom);

    if (chart.current) {
      const option = chart.current.getOption() as any;
      const currentDataZoom = option.dataZoom || [];

      // Adjust dataZoom to zoom out (increase the end value)
      const range = 100 * (100 / newZoom);
      chart.current.setOption({
        dataZoom: [
          { ...currentDataZoom[0], end: Math.min(range, 100) },
          { ...currentDataZoom[1], end: Math.min(range, 100) },
        ],
      });
    }
  }, [zoomLevel]);

  const handleResetZoom = useCallback(() => {
    setZoomLevel(100);

    if (chart.current) {
      chart.current.setOption({
        dataZoom: [
          { start: 0, end: 100 },
          { start: 0, end: 100 },
        ],
      });
    }
  }, []);

  // Calculate dynamic font size based on number of assets and container size
  const getDynamicFontSize = useCallback(
    (baseSize: number) => {
      const assetCount = assets.length;
      const containerWidth = ref.current?.clientWidth || 800;

      // Scale down font size for more assets or smaller containers
      let scaleFactor = 1;

      if (assetCount > 20) {
        scaleFactor = 0.6;
      } else if (assetCount > 15) {
        scaleFactor = 0.7;
      } else if (assetCount > 10) {
        scaleFactor = 0.8;
      } else if (assetCount > 5) {
        scaleFactor = 0.9;
      }

      // Further adjust for small containers
      if (containerWidth < 600) {
        scaleFactor *= 0.8;
      } else if (containerWidth < 800) {
        scaleFactor *= 0.9;
      }

      return Math.max(Math.round(baseSize * scaleFactor), 8); // Minimum 8px
    },
    [assets.length],
  );

  useEffect(() => {
    if (!ref.current || assets.length < 2) return;

    if (chart.current) chart.current.dispose();
    chart.current = echarts.init(ref.current, HedgeVisionDarkTheme as any);

    // Transform matrix data to ECharts format
    const data: [number, number, number][] = [];
    assets.forEach((assetA, i) => {
      assets.forEach((assetB, j) => {
        const value = matrix[assetA]?.[assetB] ?? 0;
        data.push([i, j, parseFloat(value.toFixed(3))]);
      });
    });

    // Calculate dynamic font sizes
    const labelFontSize = getDynamicFontSize(10);
    const axisLabelFontSize = getDynamicFontSize(11);
    const tooltipFontSize = getDynamicFontSize(13);
    const emphasisLabelFontSize = getDynamicFontSize(12);

    // Responsive layout based on actual container width
    const containerWidth = ref.current?.clientWidth || 800;
    const isMobile = containerWidth < 500;
    const gridLeft = isMobile ? 55 : (assets.length > 10 ? 100 : 120);
    // On mobile hide visualMap legend to reclaim space; on desktop keep 220-240
    const gridRight = isMobile ? 10 : (assets.length > 10 ? 220 : 240);
    const gridTop = isMobile ? 55 : 80;
    const gridBottom = isMobile ? 40 : (assets.length > 10 ? 60 : 50);
    // Y-slider sits between grid and right edge — on mobile drop it
    const ySliderRight = isMobile ? null : 180;

    const option: echarts.EChartsOption = {
      animation: true,
      animationDuration: 400,
      animationEasing: "cubicOut",

      tooltip: {
        position: "top",
        backgroundColor: FinancialColors.background.overlay,
        borderColor: FinancialColors.border.medium,
        borderWidth: 1,
        textStyle: {
          color: FinancialColors.text.primary,
          fontSize: tooltipFontSize,
          fontWeight: 500,
        },
        padding: [12, 16],
        extraCssText: `
          backdrop-filter: blur(12px);
          border-radius: 8px;
          box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
          z-index: 99999 !important;
        `,
        formatter: (params: any) => {
          const [xIdx, yIdx, value] = params.data;
          const asset1 = assets[xIdx];
          const asset2 = assets[yIdx];

          if (asset1 === asset2) {
            return `<div style="text-align: center;">
              <strong style="font-size: ${tooltipFontSize + 1}px;">${asset1}</strong>
              <div style="margin-top: 4px; color: ${FinancialColors.text.secondary};">Self-correlation: 1.00</div>
            </div>`;
          }

          const color = getCorrelationColor(value);
          const strength =
            Math.abs(value) > 0.7
              ? "Strong"
              : Math.abs(value) > 0.4
                ? "Moderate"
                : "Weak";
          const direction = value > 0 ? "Positive" : "Negative";

          return `<div>
            <div style="display: flex; justify-content: space-between; margin-bottom: 8px;">
              <strong style="font-size: ${tooltipFontSize + 1}px;">${asset1}</strong>
              <span style="margin: 0 8px; color: ${FinancialColors.text.tertiary};">×</span>
              <strong style="font-size: ${tooltipFontSize + 1}px;">${asset2}</strong>
            </div>
            <div style="display: flex; align-items: center; justify-content: space-between;">
              <span style="color: ${FinancialColors.text.secondary};">Correlation:</span>
              <strong style="font-size: ${tooltipFontSize + 3}px; color: ${color}; margin-left: 12px;">${value.toFixed(3)}</strong>
            </div>
            <div style="margin-top: 4px; color: ${FinancialColors.text.tertiary}; font-size: ${tooltipFontSize - 2}px;">
              ${strength} ${direction}
            </div>
            <div style="margin-top: 8px; padding-top: 8px; border-top: 1px solid ${FinancialColors.border.light}; 
                        color: ${FinancialColors.brand.primary}; font-size: ${tooltipFontSize - 2}px;">
              Click to analyze pair →
            </div>
          </div>`;
        },
      },

      // Enable brush for area selection
      brush: {
        toolbox: ["rect", "polygon", "clear"],
        xAxisIndex: 0,
        yAxisIndex: 0,
        brushStyle: {
          borderWidth: 2,
          color: "rgba(59, 130, 246, 0.1)",
          borderColor: FinancialColors.brand.primary,
        },
      },

      // Add dataZoom for scrolling and zooming
      dataZoom: [
        {
          type: "slider",
          xAxisIndex: 0,
          start: 0,
          end: 100,
          bottom: 5,
          height: 18,
          brushSelect: false,
          backgroundColor: FinancialColors.background.card,
          fillerColor: "rgba(59, 130, 246, 0.15)",
          borderColor: FinancialColors.border.medium,
          handleStyle: {
            color: FinancialColors.brand.primary,
            borderColor: FinancialColors.brand.primary,
          },
          moveHandleStyle: {
            color: FinancialColors.brand.primary,
          },
          textStyle: {
            color: FinancialColors.text.tertiary,
            fontSize: axisLabelFontSize - 1,
          },
          dataBackground: {
            lineStyle: { color: FinancialColors.border.light },
            areaStyle: { color: "rgba(59, 130, 246, 0.05)" },
          },
        },
        ...(!isMobile ? [{
          type: "slider" as const,
          yAxisIndex: 0,
          start: 0,
          end: 100,
          right: ySliderRight as number,
          width: 18,
          brushSelect: false,
          backgroundColor: FinancialColors.background.card,
          fillerColor: "rgba(59, 130, 246, 0.15)",
          borderColor: FinancialColors.border.medium,
          handleStyle: {
            color: FinancialColors.brand.primary,
            borderColor: FinancialColors.brand.primary,
          },
          moveHandleStyle: {
            color: FinancialColors.brand.primary,
          },
          textStyle: {
            color: FinancialColors.text.tertiary,
            fontSize: axisLabelFontSize - 1,
          },
          dataBackground: {
            lineStyle: { color: FinancialColors.border.light },
            areaStyle: { color: "rgba(59, 130, 246, 0.05)" },
          },
        }] : []),
        {
          type: "inside",
          xAxisIndex: 0,
          start: 0,
          end: 100,
          zoomOnMouseWheel: true,
          moveOnMouseMove: true,
          preventDefaultMouseMove: false,
        },
        {
          type: "inside",
          yAxisIndex: 0,
          start: 0,
          end: 100,
          zoomOnMouseWheel: true,
          moveOnMouseMove: true,
          preventDefaultMouseMove: false,
        },
      ],

      grid: {
        left: gridLeft,
        right: gridRight,
        top: gridTop,
        bottom: gridBottom,
        containLabel: true,
      },

      xAxis: {
        type: "category",
        data: assets,
        splitArea: {
          show: true,
          areaStyle: {
            color: ["rgba(15, 23, 42, 0.2)", "rgba(15, 23, 42, 0.4)"],
          },
        },
        axisLabel: {
          rotate: assets.length > 10 ? 45 : 45,
          color: FinancialColors.text.secondary,
          fontSize: axisLabelFontSize,
          fontWeight: 500,
          margin: 12,
          interval: 0, // Show all labels
        },
        axisLine: {
          lineStyle: {
            color: FinancialColors.border.medium,
          },
        },
        axisTick: {
          show: false,
        },
      },

      yAxis: {
        type: "category",
        data: assets,
        splitArea: {
          show: true,
          areaStyle: {
            color: ["rgba(15, 23, 42, 0.2)", "rgba(15, 23, 42, 0.4)"],
          },
        },
        axisLabel: {
          color: FinancialColors.text.secondary,
          fontSize: axisLabelFontSize,
          fontWeight: 500,
          margin: 12,
          interval: 0, // Show all labels
        },
        axisLine: {
          lineStyle: {
            color: FinancialColors.border.medium,
          },
        },
        axisTick: {
          show: false,
        },
      },

      visualMap: {
        min: -1,
        max: 1,
        calculable: !isMobile,
        show: !isMobile,
        orient: "vertical",
        left: "right",
        top: "middle",
        inRange: {
          color: [
            FinancialColors.correlation.strongNegative, // -1.0
            FinancialColors.correlation.negative, // -0.5
            FinancialColors.correlation.neutral, //  0.0
            FinancialColors.correlation.positive, // +0.5
            FinancialColors.correlation.strongPositive, // +1.0
          ],
        },
        text: ["High", "Low"],
        textStyle: {
          color: FinancialColors.text.secondary,
          fontSize: axisLabelFontSize,
        },
        itemWidth: 20,
        itemHeight: 140,
        borderColor: FinancialColors.border.medium,
        borderWidth: 1,
        backgroundColor: "rgba(15, 23, 42, 0.4)",
        padding: 8,
      },

      series: [
        {
          type: "heatmap",
          data: data,
          label: {
            show: true,
            fontSize: labelFontSize,
            fontWeight: 600,
            color: FinancialColors.text.primary,
            formatter: (params: any) => {
              const value = params.data[2];
              // Show 1.00 for diagonal (self-correlation)
              if (params.data[0] === params.data[1]) {
                return "1.00";
              }
              // Hide labels if too many assets and font is too small
              if (assets.length > 15 && labelFontSize < 9) {
                return "";
              }
              return value.toFixed(2);
            },
          },
          emphasis: {
            itemStyle: {
              shadowBlur: 15,
              shadowColor: "rgba(59, 130, 246, 0.5)",
              borderColor: FinancialColors.brand.primary,
              borderWidth: 2,
            },
            label: {
              show: true,
              fontSize: emphasisLabelFontSize,
              fontWeight: 700,
            },
          },
          itemStyle: {
            borderColor: FinancialColors.border.light,
            borderWidth: 1,
          },
        },
      ],
    };

    chart.current.setOption(option);

    // Add click event handler
    chart.current.on("click", handleCellClick);

    // Handle window resize (throttled)
    window.addEventListener("resize", handleResize);

    // Handle fullscreen change
    const handleFullscreenChange = () => {
      setIsFullscreen(!!document.fullscreenElement);
      setTimeout(() => chart.current?.resize(), 100);
    };
    document.addEventListener("fullscreenchange", handleFullscreenChange);

    return () => {
      chart.current?.off("click", handleCellClick);
      window.removeEventListener("resize", handleResize);
      document.removeEventListener("fullscreenchange", handleFullscreenChange);
      chart.current?.dispose();
    };
  }, [assets, matrix, handleCellClick, getDynamicFontSize, handleResize]);

  if (assets.length < 2) {
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
        <p>Need at least 2 assets to display correlation heatmap</p>
      </div>
    );
  }

  const buttonClass = `
    p-2 rounded-lg transition-all duration-200
    bg-slate-700/50 hover:bg-slate-600/50
    border border-slate-600/50 hover:border-blue-500/50
    text-slate-300 hover:text-white
    disabled:opacity-50 disabled:cursor-not-allowed
    flex items-center justify-center
  `;

  return (
    <div
      ref={containerRef}
      style={{
        width: "100%",
        height: isFullscreen ? "100vh" : height,
        position: "relative",
        backgroundColor: isFullscreen ? "rgb(15, 23, 42)" : "transparent",
      }}
    >
      {/* Control Panel */}
      <div
        style={{
          position: "absolute",
          top: "10px",
          left: "10px",
          zIndex: 999,
          display: "flex",
          gap: "8px",
          padding: "8px",
          backgroundColor: "rgba(15, 23, 42, 0.95)",
          borderRadius: "8px",
          backdropFilter: "blur(12px)",
          border: `1px solid ${FinancialColors.border.medium}`,
          boxShadow: "0 4px 20px rgba(0, 0, 0, 0.3)",
        }}
      >
        <button
          onClick={handleZoomIn}
          disabled={zoomLevel >= 200}
          className={buttonClass}
          title="Zoom In"
        >
          <ZoomIn size={18} />
        </button>

        <button
          onClick={handleZoomOut}
          disabled={zoomLevel <= 50}
          className={buttonClass}
          title="Zoom Out"
        >
          <ZoomOut size={18} />
        </button>

        <button
          onClick={handleResetZoom}
          className={buttonClass}
          title="Reset Zoom"
        >
          <RotateCcw size={18} />
        </button>

        <div
          style={{
            width: "1px",
            height: "100%",
            backgroundColor: FinancialColors.border.medium,
            margin: "0 4px",
          }}
        />

        <button
          onClick={toggleFullscreen}
          className={buttonClass}
          title={isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
        >
          {isFullscreen ? <Minimize2 size={18} /> : <Maximize2 size={18} />}
        </button>

        <div
          style={{
            padding: "0 8px",
            display: "flex",
            alignItems: "center",
            fontSize: "12px",
            color: FinancialColors.text.tertiary,
            fontWeight: 500,
          }}
        >
          {zoomLevel}%
        </div>
      </div>

      {/* Chart Container */}
      <div
        ref={ref}
        style={{
          width: "100%",
          height: "100%",
          cursor: "pointer",
        }}
      />
    </div>
  );
};
