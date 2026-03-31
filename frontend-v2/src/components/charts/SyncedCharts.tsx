import React, { useEffect, useRef, useState } from "react";
import * as echarts from "echarts";
import { HedgeVisionDarkTheme } from "../../themes/echarts-dark";
import { FinancialColors } from "../../themes/financial-colors";
import {
  getResponsiveFontSizes,
  formatCurrency,
  formatChartDate,
} from "../../themes/echarts-config";

export interface PricePoint {
  date: string;
  asset1_price: number | null;
  asset2_price: number | null;
}

export interface SpreadPoint {
  date: string;
  spread: number | null;
  zscore: number | null;
}

interface Props {
  priceData: PricePoint[];
  spreadData: SpreadPoint[];
  asset1Name: string;
  asset2Name: string;
  totalHeight?: number;
}

export function SyncedCharts({
  priceData,
  spreadData,
  asset1Name,
  asset2Name,
  totalHeight = 720,
}: Props) {
  const priceChartRef = useRef<HTMLDivElement>(null);
  const spreadChartRef = useRef<HTMLDivElement>(null);
  const priceChartInstance = useRef<echarts.ECharts | null>(null);
  const spreadChartInstance = useRef<echarts.ECharts | null>(null);
  const syncGroupId = "pair-chart-sync";

  // Initialize both charts
  useEffect(() => {
    if (!priceChartRef.current || !spreadChartRef.current) return;

    // Initialize price chart
    if (!priceChartInstance.current) {
      priceChartInstance.current = echarts.init(
        priceChartRef.current,
        HedgeVisionDarkTheme as any
      );
      (priceChartInstance.current as any).group = syncGroupId;
    }

    // Initialize spread chart
    if (!spreadChartInstance.current) {
      spreadChartInstance.current = echarts.init(
        spreadChartRef.current,
        HedgeVisionDarkTheme as any
      );
      (spreadChartInstance.current as any).group = syncGroupId;
    }

    // Connect charts for synchronized interactions
    echarts.connect(syncGroupId);
    console.log("[SyncedCharts] ✅ Charts initialized and connected");

    // Handle window resize
    const handleResize = () => {
      priceChartInstance.current?.resize();
      spreadChartInstance.current?.resize();
    };
    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
    };
  }, []);

  // Update charts when data changes
  useEffect(() => {
    if (
      !priceChartInstance.current ||
      !spreadChartInstance.current ||
      !priceData.length ||
      !spreadData.length
    )
      return;

    const topHeight = Math.round(totalHeight * 0.55);
    const bottomHeight = totalHeight - topHeight;

    // Price chart config
    const dates = priceData.map((d) => d.date);
    const asset1Prices = priceData.map((d) => d.asset1_price);
    const asset2Prices = priceData.map((d) => d.asset2_price);

    const priceWidth = priceChartRef.current?.clientWidth || 800;
    const priceFonts = getResponsiveFontSizes(priceWidth, topHeight, dates.length);

    const priceOption: echarts.EChartsOption = {
      animation: false, // Disable animations for faster initial render
      animationDuration: 0,
      animationEasing: "linear",
      progressive: 200, // Render in chunks for large datasets
      tooltip: {
        trigger: "axis",
        axisPointer: {
          type: "cross",
          link: [{ xAxisIndex: 'all' }, { yAxisIndex: 'all' }],
          crossStyle: {
            color: FinancialColors.text.tertiary,
            opacity: 0.6,
          },
        },
        backgroundColor: FinancialColors.background.overlay,
        borderColor: FinancialColors.border.medium,
        textStyle: {
          color: FinancialColors.text.primary,
          fontSize: priceFonts.tooltip,
        },
        padding: [12, 16],
        formatter: (params: any) => {
          if (!Array.isArray(params) || !params.length) return "";
          const date = params[0].axisValue;
          let html = `<div style="font-weight: 600; margin-bottom: 8px;">${formatChartDate(
            date,
            "medium"
          )}</div>`;
          params.forEach((p: any) => {
            if (p.value !== null) {
              html += `<div style="margin: 4px 0;">
                <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: ${p.color}; margin-right: 8px;"></span>
                ${p.seriesName}: <strong>${formatCurrency(p.value)}</strong>
              </div>`;
            }
          });
          return html;
        },
      },
      legend: {
        data: [asset1Name, asset2Name],
        top: 10,
        left: "center",
        textStyle: {
          color: FinancialColors.text.secondary,
          fontSize: priceFonts.legend,
        },
      },
      grid: {
        left: "3%",
        right: "5%",
        top: "12%",
        bottom: "8%",
        containLabel: true,
      },
      dataZoom: [
        {
          type: "inside",
          xAxisIndex: 0,
          start: 0,
          end: 100,
          zoomOnMouseWheel: true,
          moveOnMouseMove: true,
        },
      ],
      xAxis: {
        type: "category",
        data: dates,
        boundaryGap: false,
        axisLabel: {
          color: FinancialColors.text.tertiary,
          fontSize: priceFonts.axisLabel,
          formatter: (v: string) => formatChartDate(v, "short"),
        },
        axisLine: { lineStyle: { color: FinancialColors.border.medium } },
        splitLine: { show: false },
      },
      yAxis: [
        {
          type: "value",
          name: asset1Name,
          position: "left",
          axisLabel: {
            color: FinancialColors.text.tertiary,
            fontSize: priceFonts.axisLabel,
            formatter: (v: number) => formatCurrency(v),
          },
          axisLine: { show: true, lineStyle: { color: FinancialColors.brand.primary } },
          splitLine: {
            lineStyle: { type: "dashed", color: FinancialColors.border.light, opacity: 0.3 },
          },
        },
        {
          type: "value",
          name: asset2Name,
          position: "right",
          axisLabel: {
            color: FinancialColors.text.tertiary,
            fontSize: priceFonts.axisLabel,
            formatter: (v: number) => formatCurrency(v),
          },
          axisLine: { show: true, lineStyle: { color: FinancialColors.brand.accent } },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: asset1Name,
          type: "line",
          yAxisIndex: 0,
          data: asset1Prices,
          smooth: true,
          symbol: "none",
          lineStyle: { width: 2, color: FinancialColors.brand.primary },
          itemStyle: { color: FinancialColors.brand.primary },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: "rgba(59, 130, 246, 0.2)" },
              { offset: 1, color: "rgba(59, 130, 246, 0.02)" },
            ]),
          },
        },
        {
          name: asset2Name,
          type: "line",
          yAxisIndex: 1,
          data: asset2Prices,
          smooth: true,
          symbol: "none",
          lineStyle: { width: 2, color: FinancialColors.brand.accent },
          itemStyle: { color: FinancialColors.brand.accent },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: "rgba(147, 51, 234, 0.2)" },
              { offset: 1, color: "rgba(147, 51, 234, 0.02)" },
            ]),
          },
        },
      ],
    };

    // Spread chart config
    const spreads = spreadData.map((d) => d.spread);
    const zscores = spreadData.map((d) => d.zscore);

    const spreadWidth = spreadChartRef.current?.clientWidth || 800;
    const spreadFonts = getResponsiveFontSizes(spreadWidth, bottomHeight, dates.length);

    const spreadOption: echarts.EChartsOption = {
      animation: false,
      tooltip: {
        trigger: "axis",
        axisPointer: {
          type: "cross",
          link: [{ xAxisIndex: 'all' }, { yAxisIndex: 'all' }],
          crossStyle: {
            color: FinancialColors.text.tertiary,
            opacity: 0.6,
          },
        },
        backgroundColor: FinancialColors.background.overlay,
        borderColor: FinancialColors.border.medium,
        textStyle: {
          color: FinancialColors.text.primary,
          fontSize: spreadFonts.tooltip,
        },
        padding: [12, 16],
        formatter: (params: any) => {
          if (!Array.isArray(params) || !params.length) return "";
          const date = params[0].axisValue;
          let html = `<div style="font-weight: 600; margin-bottom: 8px;">${formatChartDate(
            date,
            "medium"
          )}</div>`;
          params.forEach((p: any) => {
            if (p.value !== null) {
              html += `<div style="margin: 4px 0;">
                <span style="display: inline-block; width: 8px; height: 8px; border-radius: 50%; background: ${p.color}; margin-right: 8px;"></span>
                ${p.seriesName}: <strong>${(p.value as number).toFixed(3)}</strong>
              </div>`;
            }
          });
          return html;
        },
      },
      legend: {
        data: ["Spread", "Z-Score"],
        top: 10,
        left: "center",
        textStyle: {
          color: FinancialColors.text.secondary,
          fontSize: spreadFonts.legend,
        },
      },
      grid: {
        left: "3%",
        right: "5%",
        top: "12%",
        bottom: "8%",
        containLabel: true,
      },
      dataZoom: [
        {
          type: "inside",
          xAxisIndex: 0,
          start: 0,
          end: 100,
          zoomOnMouseWheel: true,
          moveOnMouseMove: true,
        },
      ],
      xAxis: {
        type: "category",
        data: dates,
        boundaryGap: false,
        axisLabel: {
          color: FinancialColors.text.tertiary,
          fontSize: spreadFonts.axisLabel,
          formatter: (v: string) => formatChartDate(v, "short"),
        },
        axisLine: { lineStyle: { color: FinancialColors.border.medium } },
        splitLine: { show: false },
      },
      yAxis: [
        {
          type: "value",
          name: "Spread",
          position: "left",
          axisLabel: {
            color: FinancialColors.text.tertiary,
            fontSize: spreadFonts.axisLabel,
            formatter: (v: number) => v.toFixed(2),
          },
          axisLine: { show: true, lineStyle: { color: FinancialColors.brand.secondary } },
          splitLine: {
            lineStyle: { type: "dashed", color: FinancialColors.border.light, opacity: 0.3 },
          },
        },
        {
          type: "value",
          name: "Z-Score",
          position: "right",
          axisLabel: {
            color: FinancialColors.text.tertiary,
            fontSize: spreadFonts.axisLabel,
            formatter: (v: number) => v.toFixed(1),
          },
          axisLine: { show: true, lineStyle: { color: FinancialColors.brand.warning } },
          splitLine: { show: false },
        },
      ],
      series: [
        {
          name: "Spread",
          type: "line",
          yAxisIndex: 0,
          data: spreads,
          smooth: true,
          symbol: "none",
          lineStyle: { width: 2, color: FinancialColors.brand.secondary },
          itemStyle: { color: FinancialColors.brand.secondary },
          areaStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
              { offset: 0, color: "rgba(6, 182, 212, 0.2)" },
              { offset: 1, color: "rgba(6, 182, 212, 0.02)" },
            ]),
          },
        },
        {
          name: "Z-Score",
          type: "line",
          yAxisIndex: 1,
          data: zscores,
          smooth: true,
          symbol: "none",
          lineStyle: { width: 2, color: FinancialColors.brand.warning },
          itemStyle: { color: FinancialColors.brand.warning },
          markLine: {
            silent: true,
            symbol: "none",
            lineStyle: { type: "dashed", color: FinancialColors.brand.warning, opacity: 0.5 },
            label: { show: true, fontSize: spreadFonts.seriesLabel },
            data: [
              { yAxis: 2, name: "+2σ" },
              { yAxis: -2, name: "-2σ" },
              {
                yAxis: 1.5,
                name: "⚡ +1.5σ",
                lineStyle: { type: "dashed", color: "rgba(245,158,11,0.7)", width: 1 },
                label: { color: "#f59e0b", fontSize: 10 },
              },
              {
                yAxis: -1.5,
                name: "⚡ -1.5σ",
                lineStyle: { type: "dashed", color: "rgba(245,158,11,0.7)", width: 1 },
                label: { color: "#f59e0b", fontSize: 10 },
              },
              { yAxis: 0, name: "Mean", lineStyle: { type: "solid", opacity: 0.3 } },
            ],
          },
          markArea: {
            silent: true,
            itemStyle: { opacity: 0.12 },
            data: (() => {
              // Build contiguous segments where |zscore| > 1.5
              const segments: [{ xAxis: string; itemStyle: { color: string } }, { xAxis: string }][] = [];
              let segStart: string | null = null;
              let segPositive = false;
              spreadData.forEach((d) => {
                const extreme = Math.abs(d.zscore ?? 0) > 1.5;
                const positive = (d.zscore ?? 0) > 0;
                if (extreme && segStart === null) {
                  segStart = d.date;
                  segPositive = positive;
                } else if (!extreme && segStart !== null) {
                  segments.push([
                    { xAxis: segStart, itemStyle: { color: segPositive ? "rgba(239,68,68,0.20)" : "rgba(34,197,94,0.20)" } },
                    { xAxis: d.date },
                  ]);
                  segStart = null;
                }
              });
              if (segStart !== null && spreadData.length > 0) {
                segments.push([
                  { xAxis: segStart, itemStyle: { color: segPositive ? "rgba(239,68,68,0.20)" : "rgba(34,197,94,0.20)" } },
                  { xAxis: spreadData[spreadData.length - 1].date },
                ]);
              }
              return segments;
            })(),
          },
        },
      ],
    };

    priceChartInstance.current.setOption(priceOption, true);
    spreadChartInstance.current.setOption(spreadOption, true);
    console.log("[SyncedCharts] ✅ Charts updated with data");
  }, [priceData, spreadData, asset1Name, asset2Name, totalHeight]);

  const topHeight = Math.round(totalHeight * 0.55);
  const bottomHeight = totalHeight - topHeight;

  return (
    <div style={{ width: "100%", height: totalHeight, display: "flex", flexDirection: "column" }}>
      <div
        ref={priceChartRef}
        style={{
          width: "100%",
          height: topHeight,
          border: `1px solid ${FinancialColors.border.light}`,
        }}
      />
      <div
        ref={spreadChartRef}
        style={{
          width: "100%",
          height: bottomHeight,
          border: `1px solid ${FinancialColors.border.light}`,
          borderTop: "none",
        }}
      />
    </div>
  );
}
