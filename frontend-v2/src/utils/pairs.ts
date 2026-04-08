import {
  ALL_ASSET_SYMBOLS,
  getNameFromSymbol,
  getSymbolFromName,
} from "../constants/assets";

function stripKnownSuffix(symbol: string): string {
  return symbol.replace(/\.(US|CC|FOREX|NSE)$/i, "");
}

export function getApiAssetSymbol(asset?: string | null): string | undefined {
  if (!asset) return undefined;

  const directNameMatch = getSymbolFromName(asset);
  if (directNameMatch) return directNameMatch;

  if (ALL_ASSET_SYMBOLS.includes(asset as (typeof ALL_ASSET_SYMBOLS)[number])) {
    return asset;
  }

  const normalized = stripKnownSuffix(asset).toUpperCase();
  const suffixlessMatch = ALL_ASSET_SYMBOLS.find(
    (symbol) => stripKnownSuffix(symbol).toUpperCase() === normalized,
  );

  return suffixlessMatch ?? asset;
}

export function getDisplayAssetName(asset?: string | null): string | undefined {
  if (!asset) return undefined;

  const directSymbolMatch = getNameFromSymbol(asset);
  if (directSymbolMatch) return directSymbolMatch;

  const apiSymbol = getApiAssetSymbol(asset);
  if (apiSymbol) {
    const resolvedName = getNameFromSymbol(apiSymbol);
    if (resolvedName) return resolvedName;
  }

  return asset;
}

export interface PairSignalSummary {
  status:
    | "no-data"
    | "not-cointegrated"
    | "neutral"
    | "watch"
    | "entry"
    | "strong-entry";
  label: string;
  detail: string;
  tone: "gray" | "blue" | "yellow" | "red";
  longAsset?: string;
  shortAsset?: string;
}

export function getPairSignalSummary({
  currentZScore,
  isCointegrated,
  asset1Name,
  asset2Name,
  entryThreshold = 1.5,
  strongThreshold = 2,
}: {
  currentZScore?: number | null;
  isCointegrated?: boolean | null;
  asset1Name?: string;
  asset2Name?: string;
  entryThreshold?: number;
  strongThreshold?: number;
}): PairSignalSummary {
  if (currentZScore == null || Number.isNaN(currentZScore)) {
    return {
      status: "no-data",
      label: "No signal",
      detail: "Load pair data to evaluate the current spread.",
      tone: "gray",
    };
  }

  const absZ = Math.abs(currentZScore);
  const isPositiveSpread = currentZScore > 0;
  const longAsset = isPositiveSpread ? asset2Name : asset1Name;
  const shortAsset = isPositiveSpread ? asset1Name : asset2Name;

  if (!isCointegrated) {
    return {
      status: "not-cointegrated",
      label: "No trade",
      detail:
        "The spread may be stretched, but the pair is not cointegrated, so mean reversion is not statistically confirmed.",
      tone: "gray",
      longAsset,
      shortAsset,
    };
  }

  if (absZ >= strongThreshold) {
    return {
      status: "strong-entry",
      label: "Strong entry",
      detail: `Spread is extremely stretched. Favor long ${longAsset} / short ${shortAsset}.`,
      tone: "red",
      longAsset,
      shortAsset,
    };
  }

  if (absZ >= entryThreshold) {
    return {
      status: "entry",
      label: "Entry signal",
      detail: `Spread is at an actionable level. Favor long ${longAsset} / short ${shortAsset}.`,
      tone: "yellow",
      longAsset,
      shortAsset,
    };
  }

  if (absZ >= 1) {
    return {
      status: "watch",
      label: "Watchlist",
      detail: "Spread is widening, but it has not yet reached the preferred entry zone.",
      tone: "blue",
      longAsset,
      shortAsset,
    };
  }

  return {
    status: "neutral",
    label: "No signal",
    detail: "Spread is near its historical mean. Wait for a wider dislocation.",
    tone: "gray",
    longAsset,
    shortAsset,
  };
}