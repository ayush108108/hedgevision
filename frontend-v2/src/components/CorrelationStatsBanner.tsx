import React, { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowRight, RefreshCcw } from "lucide-react";
import { getCorrelationMatrix } from "../services/correlation";
import type { CorrelationMatrix } from "../types";

type StatCardProps = {
  title: string;
  value: string;
  subtitle?: string;
  accent?: "blue" | "green" | "amber" | "red";
};

type CorrelationInsights = {
  assetCount: number;
  strongestPair: { assets: string; value: number } | null;
  weakestPair: { assets: string; value: number } | null;
  averageCorrelation: number | null;
  generatedAt: string | null;
};

const accentStyles: Record<
  NonNullable<StatCardProps["accent"]>,
  { border: string; text: string; chip: string }
> = {
  blue: {
    border: "border-blue-400/40",
    text: "text-blue-200",
    chip: "bg-blue-500/10 text-blue-200",
  },
  green: {
    border: "border-emerald-400/40",
    text: "text-emerald-200",
    chip: "bg-emerald-500/10 text-emerald-200",
  },
  amber: {
    border: "border-amber-400/40",
    text: "text-amber-200",
    chip: "bg-amber-500/10 text-amber-200",
  },
  red: {
    border: "border-rose-400/40",
    text: "text-rose-200",
    chip: "bg-rose-500/10 text-rose-200",
  },
};

const StatCard = React.memo(
  ({ title, value, subtitle, accent = "blue" }: StatCardProps) => {
    const styles = accentStyles[accent];
    return (
      <div
        className={`flex-1 min-w-[220px] rounded-xl border ${styles.border} bg-white/5 px-4 py-3`}
      >
        <p className="text-xs uppercase tracking-wide text-slate-400">
          {title}
        </p>
        <p className={`mt-2 text-2xl font-semibold ${styles.text}`}>{value}</p>
        {subtitle ? (
          <p
            className={`mt-1 text-xs font-medium ${styles.chip} inline-flex items-center gap-1 rounded-full px-2 py-0.5`}
          >
            <ArrowRight size={12} /> {subtitle}
          </p>
        ) : null}
      </div>
    );
  },
);
StatCard.displayName = "StatCard";

const BannerSkeleton = React.memo(() => (
  <div className="flex flex-col gap-3">
    <div className="flex items-center justify-between gap-2">
      <div className="h-4 w-52 animate-pulse rounded bg-slate-700/70" />
      <div className="h-8 w-24 animate-pulse rounded bg-slate-700/70" />
    </div>
    <div className="flex flex-col gap-3 md:flex-row">
      {[0, 1, 2].map((key) => (
        <div
          key={key}
          className="flex-1 min-w-[220px] rounded-xl border border-slate-700/60 bg-white/5 p-4"
        >
          <div className="h-3 w-28 animate-pulse rounded bg-slate-700/70" />
          <div className="mt-3 h-6 w-32 animate-pulse rounded bg-slate-700/70" />
          <div className="mt-4 h-5 w-24 animate-pulse rounded bg-slate-700/70" />
        </div>
      ))}
    </div>
  </div>
));
BannerSkeleton.displayName = "BannerSkeleton";

interface ToastProps {
  message: string;
}

const Toast = React.memo(({ message }: ToastProps) => (
  <div className="pointer-events-none fixed right-6 top-20 z-[60] flex w-full max-w-xs items-start gap-3 rounded-xl border border-rose-500/40 bg-[#1a0f0f]/95 px-4 py-3 text-rose-100 shadow-2xl shadow-rose-500/20 backdrop-blur">
    <AlertTriangle className="mt-0.5 h-4 w-4 text-rose-300" aria-hidden />
    <div>
      <p className="text-sm font-semibold">Correlation data unavailable</p>
      <p className="mt-1 text-xs text-rose-200/80">{message}</p>
    </div>
  </div>
));
Toast.displayName = "Toast";

function computeCorrelationInsights(
  data: CorrelationMatrix,
): CorrelationInsights {
  const assets = Array.isArray(data?.assets) ? data.assets : [];

  if (!assets.length) {
    return {
      assetCount: 0,
      strongestPair: null,
      weakestPair: null,
      averageCorrelation: null,
      generatedAt: data.metadata?.generated_at ?? null,
    };
  }

  let sum = 0;
  let count = 0;
  let strong: CorrelationInsights["strongestPair"] = null;
  let weak: CorrelationInsights["weakestPair"] = null;

  for (const assetA of assets) {
    for (const assetB of assets) {
      if (assetA === assetB) continue;
      const value = (data as any)?.matrix?.[assetA]?.[assetB];
      if (typeof value !== "number" || Number.isNaN(value)) continue;
      sum += value;
      count += 1;
      if (!strong || Math.abs(value) > Math.abs(strong.value)) {
        strong = { assets: `${assetA} / ${assetB}`, value };
      }
      if (!weak || Math.abs(value) < Math.abs(weak.value)) {
        weak = { assets: `${assetA} / ${assetB}`, value };
      }
    }
  }

  return {
    assetCount: assets.length,
    strongestPair: strong,
    weakestPair: weak,
    averageCorrelation: count ? sum / count : null,
    generatedAt: data.metadata?.generated_at ?? null,
  };
}

function formatCorrelation(value: number | null, fallback = "—") {
  if (value === null || Number.isNaN(value)) return fallback;
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}`;
}

function formatTimestamp(timestamp: string | null) {
  if (!timestamp) return "Unknown";
  const parsed = new Date(timestamp);
  if (Number.isNaN(parsed.getTime())) return "Unknown";
  return parsed.toLocaleString(undefined, {
    hour: "2-digit",
    minute: "2-digit",
    month: "short",
    day: "numeric",
  });
}

const REFRESH_INTERVAL_MS = 1000 * 60 * 5; // 5 minutes

const CorrelationStatsBannerComponent: React.FC = () => {
  const [toastMessage, setToastMessage] = useState<string | null>(null);

  const correlationQuery = useQuery({
    queryKey: ["correlation", "header"],
    queryFn: () => getCorrelationMatrix({ granularity: "daily" }),
    staleTime: REFRESH_INTERVAL_MS,
    refetchInterval: REFRESH_INTERVAL_MS,
  });

  useEffect(() => {
    if (correlationQuery.error) {
      const message =
        correlationQuery.error instanceof Error
          ? correlationQuery.error.message
          : "Unable to load correlation metrics.";
      setToastMessage(message);
    }
  }, [correlationQuery.error]);

  useEffect(() => {
    if (!toastMessage) return;
    const timeout = window.setTimeout(() => setToastMessage(null), 4000);
    return () => window.clearTimeout(timeout);
  }, [toastMessage]);

  const insights = useMemo(
    () =>
      correlationQuery.data
        ? computeCorrelationInsights(correlationQuery.data)
        : null,
    [correlationQuery.data],
  );

  return (
    <>
      <section className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-slate-900/80 via-slate-900/60 to-slate-900/80 px-4 py-4 shadow-lg shadow-black/40 backdrop-blur">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(56,189,248,0.12),transparent_55%)]" />
        <div className="relative flex flex-col gap-4">
          <header className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs uppercase tracking-wide text-slate-400">
                Correlation snapshot
              </p>
              <h2 className="text-lg font-semibold text-sky-100">
                Daily correlation insights across monitored assets
              </h2>
            </div>
            <button
              type="button"
              onClick={() => correlationQuery.refetch()}
              className="inline-flex items-center gap-2 rounded-lg border border-sky-400/40 bg-sky-500/10 px-3 py-2 text-sm font-medium text-sky-100 transition hover:bg-sky-500/20 hover:text-white"
              disabled={correlationQuery.isFetching}
            >
              <RefreshCcw
                className={`h-4 w-4 ${correlationQuery.isFetching ? "animate-spin" : ""}`}
              />
              {correlationQuery.isFetching ? "Refreshing" : "Refresh"}
            </button>
          </header>

          {correlationQuery.isLoading || !insights ? (
            <BannerSkeleton />
          ) : (
            <div className="flex flex-col gap-3 md:flex-row">
              <StatCard
                title="Tracked assets"
                value={insights.assetCount.toString()}
                subtitle={`Updated ${formatTimestamp(insights.generatedAt)}`}
                accent="blue"
              />
              <StatCard
                title="Strongest relationship"
                value={
                  insights.strongestPair ? insights.strongestPair.assets : "—"
                }
                subtitle={formatCorrelation(
                  insights.strongestPair?.value ?? null,
                )}
                accent="green"
              />
              <StatCard
                title="Average correlation"
                value={formatCorrelation(insights.averageCorrelation)}
                subtitle={
                  insights.weakestPair
                    ? `${insights.weakestPair.assets}: ${formatCorrelation(insights.weakestPair.value)}`
                    : undefined
                }
                accent="amber"
              />
            </div>
          )}
        </div>
      </section>

      {toastMessage ? <Toast message={toastMessage} /> : null}
    </>
  );
};

export const CorrelationStatsBanner = React.memo(
  CorrelationStatsBannerComponent,
);
CorrelationStatsBanner.displayName = "CorrelationStatsBanner";
