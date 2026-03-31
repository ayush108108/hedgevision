import React, { useEffect } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  Loader2,
  CheckCircle2,
  XCircle,
  Activity,
  Clock,
  TrendingUp,
} from "lucide-react";
import { getScreeningStatus } from "../../services/cointegrationApi";

interface ScreeningStatusProps {
  jobId: string;
  onComplete: () => void;
}

export function ScreeningStatus({ jobId, onComplete }: ScreeningStatusProps) {
  const { data: status, isLoading } = useQuery({
    queryKey: ["screening-status", jobId],
    queryFn: () => getScreeningStatus(jobId),
    enabled: !!jobId,
    refetchInterval: (query) => {
      // Stop polling if job is complete or failed
      const data = query.state.data;
      if (data?.status === "completed" || data?.status === "failed") {
        return false;
      }
      return 2000; // Poll every 2 seconds
    },
  });

  useEffect(() => {
    if (status?.status === "completed") {
      onComplete();
    }
  }, [status?.status, onComplete]);

  if (isLoading || !status) {
    return (
      <div className="p-6 rounded-2xl bg-white/5 border border-white/10">
        <div className="flex items-center gap-3">
          <Loader2 className="w-6 h-6 text-blue-500 animate-spin" />
          <div>
            <div className="text-lg font-semibold text-white">
              Initializing screening...
            </div>
            <div className="text-sm text-gray-400">
              Preparing to analyze pairs
            </div>
          </div>
        </div>
      </div>
    );
  }

  const getStatusIcon = () => {
    switch (status.status) {
      case "completed":
        return <CheckCircle2 className="w-6 h-6 text-green-400" />;
      case "failed":
        return <XCircle className="w-6 h-6 text-red-400" />;
      case "running":
        return <Activity className="w-6 h-6 text-blue-400 animate-pulse" />;
      default:
        return <Clock className="w-6 h-6 text-gray-400" />;
    }
  };

  const getStatusColor = () => {
    switch (status.status) {
      case "completed":
        return "from-green-500/20 to-emerald-500/20 border-green-500/30";
      case "failed":
        return "from-red-500/20 to-pink-500/20 border-red-500/30";
      case "running":
        return "from-blue-500/20 to-cyan-500/20 border-blue-500/30";
      default:
        return "from-gray-500/20 to-gray-600/20 border-gray-500/30";
    }
  };

  const progress =
    status.progress?.pairs_tested && status.progress?.total_pairs
      ? (status.progress.pairs_tested / status.progress.total_pairs) * 100
      : 0;

  const eta = status.progress?.estimated_time_remaining
    ? `${Math.ceil(status.progress.estimated_time_remaining / 60)} min remaining`
    : null;

  return (
    <div
      className={`p-6 rounded-2xl bg-gradient-to-br ${getStatusColor()} border space-y-4`}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {getStatusIcon()}
          <div>
            <div className="text-lg font-semibold text-white capitalize">
              {status.status}
            </div>
            <div className="text-sm text-gray-400">
              {status.status === "completed"
                ? "Screening completed successfully"
                : status.status === "failed"
                  ? "Screening failed"
                  : "Analyzing cointegration pairs"}
            </div>
          </div>
        </div>
        {status.status === "running" && eta && (
          <div className="text-right">
            <div className="text-sm text-gray-400">ETA</div>
            <div className="text-lg font-semibold text-white">{eta}</div>
          </div>
        )}
      </div>

      {/* Progress Bar */}
      {status.status === "running" && (
        <>
          <div className="space-y-2">
            <div className="flex items-center justify-between text-sm">
              <span className="text-gray-400">Progress</span>
              <span className="font-medium text-white">
                {status.progress?.pairs_tested || 0} /{" "}
                {status.progress?.total_pairs || 0} pairs
              </span>
            </div>
            <div className="h-3 bg-white/10 rounded-full overflow-hidden relative">
              <div
                className="absolute inset-y-0 left-0 bg-gradient-to-r from-blue-500 to-purple-500 rounded-full transition-all duration-500"
                style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
              />
            </div>
            <div className="text-right text-sm font-medium text-white">
              {progress.toFixed(1)}%
            </div>
          </div>

          {/* Current Activity */}
          {status.progress?.current_pair && (
            <div className="p-3 rounded-lg bg-white/5 border border-white/10">
              <div className="flex items-center gap-2 text-sm text-gray-400 mb-1">
                <TrendingUp className="w-4 h-4" />
                <span>Currently Testing</span>
              </div>
              <div className="text-white font-medium">
                {status.progress.current_pair}
              </div>
            </div>
          )}
        </>
      )}

      {/* Results Summary */}
      {status.status === "completed" && (
        <div className="grid grid-cols-3 gap-4">
          <div className="p-3 rounded-lg bg-white/5 border border-white/10">
            <div className="text-sm text-gray-400 mb-1">Tested</div>
            <div className="text-2xl font-bold text-white">
              {status.progress?.pairs_tested || 0}
            </div>
          </div>
          <div className="p-3 rounded-lg bg-white/5 border border-white/10">
            <div className="text-sm text-gray-400 mb-1">Found</div>
            <div className="text-2xl font-bold text-green-400">
              {status.results_count || 0}
            </div>
          </div>
          <div className="p-3 rounded-lg bg-white/5 border border-white/10">
            <div className="text-sm text-gray-400 mb-1">Duration</div>
            <div className="text-2xl font-bold text-white">
              {status.completed_at && status.started_at
                ? `${Math.ceil((new Date(status.completed_at).getTime() - new Date(status.started_at).getTime()) / 60000)}m`
                : "N/A"}
            </div>
          </div>
        </div>
      )}

      {/* Error Message */}
      {status.status === "failed" && status.progress?.error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/30 text-red-300 text-sm">
          <div className="font-medium mb-1">Error Details:</div>
          <div>{status.progress.error}</div>
        </div>
      )}

      {/* Job ID */}
      <div className="pt-3 border-t border-white/10 text-xs text-gray-500">
        Job ID: {jobId}
      </div>
    </div>
  );
}
