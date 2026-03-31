import axios from "axios";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ||
  import.meta.env.VITE_API_URL ||
  "http://localhost:8000";

export const api = axios.create({
  baseURL: API_BASE,
  timeout: 30_000,
});

// Response interceptor for error logging (no auth redirects in no-auth mode)
api.interceptors.response.use(
  (response) => response,
  (error) => {
    console.error("API Error:", error.response?.data || error.message);
    return Promise.reject(error);
  },
);

export interface EnqueueBacktestPayload {
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
  max_holding_period?: number;
  granularity?: string;
}

export interface BacktestResult {
  task_id?: string;
  metrics?: Record<string, any>;
  trades?: any[];
  equity_curve?: Record<string, number>;
}

export function enqueueBacktest(payload: EnqueueBacktestPayload) {
  // Deprecated: Celery removed, use runBacktest (synchronous) instead
  throw new Error("Async backtest deprecated. Use runBacktest() for synchronous execution");
}

export function runBacktest(payload: EnqueueBacktestPayload) {
  return api
    .post<BacktestResult>("/backtest/run", payload)
    .then((r) => r.data);
}

export function getBacktestStatus(taskId: string) {
  // Deprecated: Celery removed
  throw new Error("Backtest status endpoint deprecated. Use synchronous runBacktest()");
}

// Cache endpoints
export interface CacheHealthResponse {
  status: string;
  cache_type: "redis" | "memory";
  redis_available: boolean;
  set_success: boolean;
  get_success: boolean;
  delete_success: boolean;
  config: {
    redis_host?: string;
    redis_port?: number;
    redis_db?: number;
    redis_prefix?: string;
    redis_ttl?: number;
  };
}

export interface CacheStatsResponse {
  cache_type: "redis" | "memory";
  redis_available: boolean;
  configuration: Record<string, any>;
  redis_info?: {
    connected_clients: number;
    used_memory_human: string;
    total_commands_processed: number;
    keyspace_hits: number;
    keyspace_misses: number;
    hit_rate_percent: number;
  };
}

export function getCacheHealth() {
  return api.get<CacheHealthResponse>("/cache/health").then((r) => r.data);
}

export function getCacheStats() {
  return api.get<CacheStatsResponse>("/cache/stats").then((r) => r.data);
}

export function clearCache() {
  return api
    .post<{ status: string; message: string }>("/cache/clear")
    .then((r) => r.data);
}

export function performCacheTest(iterations = 100) {
  return api
    .get<{
      iterations: number;
      cache_type: string;
      set_performance: { avg_ms: number; min_ms: number; max_ms: number };
      get_performance: { avg_ms: number; min_ms: number; max_ms: number };
    }>(`/cache/performance-test?iterations=${iterations}`)
    .then((r) => r.data);
}

// News API
export interface NewsArticle {
  id: string;
  title: string;
  summary: string;
  source: string;
  url: string;
  timestamp: string;
  sentiment: "positive" | "negative" | "neutral";
  sentiment_score: number;
  sentiment_scores: Record<string, number>;
  relatedAssets: string[];
}

export interface NewsResponse {
  articles: NewsArticle[];
  total: number;
  sources: string[];
}

export function getNews(params?: {
  sources?: string;
  sentiment?: string;
  limit?: number;
}) {
  return api.get<NewsResponse>("/news/", { params }).then((r) => r.data);
}

export function getAssetNews(symbol: string, limit = 10) {
  return api
    .get<NewsResponse>(`/news/asset/${symbol}`, { params: { limit } })
    .then((r) => r.data);
}

export function getNewsSources() {
  return api
    .get<{ sources: string[]; total: number }>("/news/sources")
    .then((r) => r.data);
}

// Crypto Market Data API
export interface PriceData {
  symbol: string;
  price: number;
  bid?: number;
  ask?: number;
  volume?: number;
  quoteVolume?: number;
  change?: number;
  percentage?: number;
  high?: number;
  low?: number;
  timestamp?: number;
  fundingRate?: number;
}

export interface FundingRateData {
  symbol: string;
  fundingRate: number;
  fundingTimestamp?: number;
  nextFundingTime?: number;
  averageRate7d?: number;
}

export interface OpenInterestData {
  symbol: string;
  openInterest: number;
  openInterestValue?: number;
  timestamp?: number;
}

export interface LiquidationData {
  symbol: string;
  timeframe: string;
  longLiquidations: number;
  shortLiquidations: number;
  totalLiquidations: number;
  longLiquidationsPercent?: number;
  shortLiquidationsPercent?: number;
}

export function getCryptoPrice(symbol: string) {
  return api.get<PriceData>(`/crypto/price/${symbol}`).then((r) => r.data);
}

export function getCryptoPrices(symbols?: string) {
  return api
    .get<PriceData[]>("/crypto/prices", { params: { symbols } })
    .then((r) => r.data);
}

export function getFundingRate(symbol: string) {
  return api
    .get<FundingRateData>(`/crypto/funding/${symbol}`)
    .then((r) => r.data);
}

export function getOpenInterest(symbol: string) {
  return api
    .get<OpenInterestData>(`/crypto/openinterest/${symbol}`)
    .then((r) => r.data);
}

export function getOrderBook(symbol: string, limit = 20) {
  return api
    .get(`/crypto/orderbook/${symbol}`, { params: { limit } })
    .then((r) => r.data);
}

export function getGainersLosers(limit = 10) {
  return api
    .get<{ gainers: PriceData[]; losers: PriceData[] }>(
      "/crypto/gainers-losers",
      { params: { limit } }
    )
    .then((r) => r.data);
}

export function getLiquidations(symbol = "BTC", timeframe = "24h") {
  return api
    .get<LiquidationData>(`/crypto/liquidations/${symbol}`, {
      params: { timeframe },
    })
    .then((r) => r.data);
}

export function getCoinglassOI(symbol = "BTC") {
  return api
    .get(`/crypto/coinglass/openinterest/${symbol}`)
    .then((r) => r.data);
}

export function getCoinglassFunding(symbol = "BTC") {
  return api.get(`/crypto/coinglass/funding/${symbol}`).then((r) => r.data);
}

export function getLongShortRatio(symbol = "BTC", exchange = "Binance") {
  return api
    .get(`/crypto/coinglass/longshort/${symbol}`, { params: { exchange } })
    .then((r) => r.data);
}

export function getFearGreedIndex() {
  return api.get("/crypto/fear-greed").then((r) => r.data);
}

export function getMarketMetrics(symbol = "BTC") {
  return api.get(`/crypto/market-metrics/${symbol}`).then((r) => r.data);
}

// Portfolio API
export interface Position {
  id: string;
  user_id: string;
  pair: string;
  asset1: string;
  asset2: string;
  type: "long-short" | "short-long";
  entry_date: string;
  entry_spread: number;
  current_spread: number;
  position_size: number;
  unrealized_pnl: number;
  unrealized_pnl_percent: number;
  status: "open" | "pending" | "closed";
  exit_date?: string;
  exit_spread?: number;
  realized_pnl?: number;
  hedge_ratio: number;
  entry_zscore?: number;
  stop_loss?: number;
  take_profit?: number;
  notes?: string;
}

export interface PortfolioMetrics {
  total_value: number;
  cash_balance: number;
  invested_capital: number;
  total_pnl: number;
  total_pnl_percent: number;
  number_of_positions: number;
  win_rate: number;
  sharpe_ratio: number;
  max_drawdown: number;
  total_return: number;
  average_win: number;
  average_loss: number;
  profit_factor: number;
  sortino_ratio: number;
  calmar_ratio: number;
}

// Standardization Service types
export interface StandardizedPairResponse {
  pair: string;
}

export interface SplitPairResponse {
  asset1: string;
  asset2: string;
}

export interface ProviderSymbolMap {
  asset1: string | null;
  asset2: string | null;
}

export interface StandardizedPositionResponse {
  position: Position;
  standardized: {
    pair: string;
    assets: { asset1: string; asset2: string };
    providers: {
      binance: ProviderSymbolMap;
      coinglass: ProviderSymbolMap;
      yfinance: ProviderSymbolMap;
    };
  };
}

export interface CreatePositionRequest {
  pair: string;
  asset1: string;
  asset2: string;
  type: "long-short" | "short-long";
  entry_spread: number;
  position_size: number;
  hedge_ratio?: number;
  entry_zscore?: number;
  stop_loss?: number;
  take_profit?: number;
  notes?: string;
}

export function createPosition(data: CreatePositionRequest) {
  return api.post<Position>("/portfolio/positions", data).then((r) => r.data);
}

export function getPositions(status?: string) {
  return api
    .get<Position[]>("/portfolio/positions", { params: { status } })
    .then((r) => r.data);
}

export function getPosition(positionId: string) {
  return api
    .get<Position>(`/portfolio/positions/${positionId}`)
    .then((r) => r.data);
}

export function updatePositionSpread(
  positionId: string,
  current_spread: number
) {
  return api
    .patch<Position>(`/portfolio/positions/${positionId}/spread`, {
      current_spread,
    })
    .then((r) => r.data);
}

export function closePosition(positionId: string, exit_spread: number, notes?: string) {
  return api
    .post<Position>(`/portfolio/positions/${positionId}/close`, {
      exit_spread,
      notes,
    })
    .then((r) => r.data);
}

export function deletePosition(positionId: string) {
  return api
    .delete(`/portfolio/positions/${positionId}`)
    .then((r) => r.data);
}

export function getPortfolioMetrics() {
  return api
    .get<PortfolioMetrics>("/portfolio/metrics")
    .then((r) => r.data);
}

// Standardization Service client
export function getCanonicalPair(asset1: string, asset2: string, delimiter: string = "-") {
  const params = new URLSearchParams({ asset1, asset2, delimiter });
  return api.get<StandardizedPairResponse>(`/standardize/pair?${params.toString()}`).then((r) => r.data);
}

export function splitPair(pair: string) {
  const params = new URLSearchParams({ pair });
  return api.get<SplitPairResponse>(`/standardize/split?${params.toString()}`).then((r) => r.data);
}

export function toBinance(asset: string) {
  const params = new URLSearchParams({ asset });
  return api.get<{ asset: string; binance_symbol: string | null }>(`/standardize/binance?${params.toString()}`).then((r) => r.data);
}

export function toCoinglass(asset: string) {
  const params = new URLSearchParams({ asset });
  return api.get<{ asset: string; coinglass_symbol: string | null }>(`/standardize/coinglass?${params.toString()}`).then((r) => r.data);
}

export function toYFinance(asset: string) {
  const params = new URLSearchParams({ asset });
  return api.get<{ asset: string; yfinance_symbol: string | null }>(`/standardize/yfi?${params.toString()}`).then((r) => r.data);
}

export function getStandardizedPosition(positionId: string) {
  return api.get<StandardizedPositionResponse>(`/portfolio/positions/${positionId}/standardized`).then((r) => r.data);
}

export function getTradeHistory(limit = 50) {
  return api
    .get<Position[]>("/portfolio/history", { params: { limit } })
    .then((r) => r.data);
}
