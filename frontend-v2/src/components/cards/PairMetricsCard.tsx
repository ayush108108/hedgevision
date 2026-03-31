interface Props {
  correlation?: number;
  volatilityRatio?: number;
}

export function PairMetricsCard({ correlation, volatilityRatio }: Props) {
  return (
    <div className="bg-white border rounded-lg p-6">
      <h3 className="text-lg font-semibold mb-4">Pair Metrics</h3>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="text-center">
          <div className="text-3xl font-bold text-blue-600">
            {correlation ? correlation.toFixed(3) : "N/A"}
          </div>
          <div className="text-sm text-slate-600 mt-1">Correlation</div>
          <div className="w-full bg-slate-200 rounded-full h-2 mt-2">
            <div
              className="bg-blue-600 h-2 rounded-full"
              style={{ width: `${Math.abs(correlation || 0) * 100}%` }}
            />
          </div>
        </div>

        <div className="text-center">
          <div className="text-3xl font-bold text-green-600">
            {volatilityRatio ? volatilityRatio.toFixed(3) : "N/A"}
          </div>
          <div className="text-sm text-slate-600 mt-1">Volatility Ratio</div>
          <div className="w-full bg-slate-200 rounded-full h-2 mt-2">
            <div
              className="bg-green-600 h-2 rounded-full"
              style={{
                width: `${Math.min((volatilityRatio || 0) * 50, 100)}%`,
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
