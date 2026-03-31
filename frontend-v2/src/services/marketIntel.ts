import apiClient from "./apiClient";

export interface StructuredVerdict {
  stance: "bullish" | "bearish" | "neutral";
  confidence: number;
  headline: string;
  rationale: string[];
  model_version: string;
  model_provider: string;
}

export interface MarketIntelResponse {
  ticker: string;
  market_data: Record<string, number | string | null>;
  quant_metrics: Record<string, number | string | null>;
  sentiment: Record<string, unknown> | null;
  verdict: StructuredVerdict;
}

export function getStructuredVerdict(params: {
  ticker: string;
  period?: string;
  news_url?: string;
  use_llm?: boolean;
  provider?: "rules" | "openai" | "anthropic" | "ollama" | "cpu";
  model?: string;
}) {
  return apiClient
    .get<MarketIntelResponse>(`/market-intel/verdict/${params.ticker}`, {
      params,
    })
    .then((r) => r.data);
}
