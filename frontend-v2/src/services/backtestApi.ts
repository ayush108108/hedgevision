import apiClient from "./apiClient";

export interface BacktestRequest {
  symbol1: string;
  symbol2: string;
  lookback_days?: number;
  initial_capital?: number;
  position_size?: number;
  transaction_cost?: number;
  slippage?: number;
  entry_threshold?: number;
  exit_threshold?: number;
  stop_loss_threshold?: number;
  max_holding_period?: number | null;
  granularity?: string;
}

export interface BacktestMetrics {
  initial_capital: number;
  final_capital: number;
  total_return: number;
  annualized_return: number | null;
  max_drawdown: number | null;
  trade_count: number;
  win_rate: number | null;
  average_trade: number | null;
}

export interface BacktestTrade {
  entry_date: string;
  exit_date: string;
  entry_spread: number;
  exit_spread: number;
  entry_zscore: number;
  exit_zscore: number;
  position_type: "long" | "short";
  pnl: number;
  exit_reason: "take_profit" | "stop_loss" | "time_exit" | "forced_exit";
  duration: number;
}

export interface BacktestResult {
  metrics: BacktestMetrics;
  trades: BacktestTrade[];
  equity_curve: Record<string, number>;
}

export interface BacktestValidation {
  is_valid: boolean;
  errors: string[];
  warnings: string[];
  config: BacktestRequest;
}

export class BacktestAPIError extends Error {
  constructor(
    message: string,
    public statusCode?: number,
    public details?: unknown,
  ) {
    super(message);
    this.name = "BacktestAPIError";
  }
}

function handleAPIError(error: unknown, context: string): never {
  const e = error as Record<string, unknown>;
  if (e?.response) {
    const resp = e.response as Record<string, unknown>;
    const data = resp.data as Record<string, unknown> | undefined;
    const msg = (data?.detail as string) ?? (data?.message as string) ?? (e.message as string) ?? "Unknown error";
    throw new BacktestAPIError(`${context}: ${msg}`, resp.status as number, data);
  }
  if (e?.request) {
    throw new BacktestAPIError(`${context}: No response from server`, 0);
  }
  throw new BacktestAPIError(`${context}: ${(e?.message as string) ?? "Unknown error"}`);
}

export async function runBacktest(request: BacktestRequest): Promise<BacktestResult> {
  try {
    const { data } = await apiClient.post<BacktestResult>("/backtest/run", request);
    return data;
  } catch (error) {
    handleAPIError(error, `Backtest ${request.symbol1}/${request.symbol2}`);
  }
}

export async function getDefaultBacktestConfig(): Promise<BacktestRequest> {
  try {
    const { data } = await apiClient.get<BacktestRequest>("/backtest/config/default");
    return data;
  } catch (error) {
    handleAPIError(error, "Get default backtest config");
  }
}

export async function validateBacktestConfig(
  request: BacktestRequest,
): Promise<BacktestValidation> {
  try {
    const { data } = await apiClient.post<BacktestValidation>(
      "/backtest/config/validate",
      request,
    );
    return data;
  } catch (error) {
    handleAPIError(error, "Validate backtest config");
  }
}
