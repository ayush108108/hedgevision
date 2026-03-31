export interface CointegrationResults {
  adf_statistic?: number;
  adf_pvalue?: number;
  critical_values?: Record<string, number>;
  is_cointegrated?: boolean;
  johansen_trace_stat?: number;
  johansen_critical_value?: number;
}

interface Props {
  results: CointegrationResults;
  asset1Name: string;
  asset2Name: string;
  granularity?: string;
}

export function CointegrationCard({
  results,
  asset1Name,
  asset2Name,
  granularity = "daily",
}: Props) {
  const isCointegrated = results.is_cointegrated ?? false;

  // Format granularity for display
  const granularityLabels: Record<string, string> = {
    daily: "Daily",
    "4h": "4-Hour",
    hourly: "Hourly",
    weekly: "Weekly",
    monthly: "Monthly",
  };

  const displayGranularity = granularityLabels[granularity] || granularity;

  return (
    <div className="premium-card p-6 space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-white">
            Cointegration Test
          </h3>
          <span className="px-2 py-1 text-xs font-medium bg-blue-500/10 text-blue-400 border border-blue-500/30 rounded">
            {displayGranularity}
          </span>
        </div>
        <span
          className={`px-3 py-1 rounded-full text-sm font-medium border ${
            isCointegrated
              ? "bg-green-400/10 text-green-400 border-green-400/30"
              : "bg-red-400/10 text-red-400 border-red-400/30"
          }`}
        >
          {isCointegrated ? "Cointegrated" : "Not Cointegrated"}
        </span>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
        <div>
          <div className="font-medium text-gray-400">ADF Statistic</div>
          <div className="text-lg text-white">
            {(results.adf_statistic || 0).toFixed(4)}
          </div>
        </div>
        <div>
          <div className="font-medium text-gray-400">P-Value</div>
          <div className="text-lg text-white">
            {(results.adf_pvalue || 0).toFixed(4)}
          </div>
        </div>
        {results.johansen_trace_stat && (
          <div>
            <div className="font-medium text-gray-400">Johansen Trace</div>
            <div className="text-lg text-white">
              {results.johansen_trace_stat.toFixed(4)}
            </div>
          </div>
        )}
        {results.johansen_critical_value && (
          <div>
            <div className="font-medium text-gray-400">Critical Value</div>
            <div className="text-lg text-white">
              {results.johansen_critical_value.toFixed(4)}
            </div>
          </div>
        )}
      </div>

      {results.critical_values && (
        <div className="mt-4">
          <div className="font-medium text-gray-400 mb-2">Critical Values</div>
          <div className="grid grid-cols-3 gap-2 text-xs">
            {Object.entries(results.critical_values).map(([level, value]) => (
              <div
                key={level}
                className="bg-white/5 border border-gray-700 p-2 rounded"
              >
                <div className="font-medium text-gray-300">{level}</div>
                <div className="text-white">{value.toFixed(4)}</div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
