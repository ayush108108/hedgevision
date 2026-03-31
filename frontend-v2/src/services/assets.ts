import apiClient from "./apiClient";

export interface Asset {
  id: number;
  symbol: string;
  name?: string;
}

export interface AssetsResponse {
  assets: Asset[];
  total: number;
}

/**
 * Fetch all available assets from the database
 */
export async function getAssets(params?: {
  search?: string;
  limit?: number;
}): Promise<AssetsResponse> {
  const response = await apiClient.get<AssetsResponse>("/assets", {
    params,
  });
  return response.data;
}

/**
 * Fetch popular/curated assets commonly used for pairs trading
 */
export async function getPopularAssets(): Promise<AssetsResponse> {
  const response = await apiClient.get<AssetsResponse>("/assets/popular");
  return response.data;
}

/**
 * Fetch just asset symbols (lightweight)
 */
export async function getAssetSymbols(limit?: number): Promise<string[]> {
  const response = await apiClient.get<string[]>("/assets/symbols", {
    params: { limit },
  });
  return response.data;
}
