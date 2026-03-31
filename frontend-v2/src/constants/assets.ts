/**
 * Centralized Asset Constants
 * Synchronized with backend/api/utils/assets.py
 */

export interface Asset {
  symbol: string; // API format (e.g., "AAPL.US")
  name: string; // Display name (e.g., "Apple")
  type: "stock" | "etf" | "forex" | "crypto" | "adr";
  category: string;
  exchange?: string;
}

// Asset categories from backend
export const ASSET_CATEGORIES = {
  "US Stocks": [
    "Apple",
    "Microsoft",
    "Tesla",
    "NVIDIA",
    "Meta Platforms",
    "Alphabet",
    "Amazon",
    "Netflix",
    "MicroStrategy",
    "C3.ai",
  ],
  "US ETFs": [
    "S&P 500 ETF",
    "Nasdaq 100 ETF",
    "Dow Jones ETF",
    "7-10Y Treasury ETF",
    "20Y+ Treasury ETF",
    "1-3Y Treasury ETF",
    "Tech Sector ETF",
    "Financials Sector ETF",
    "Energy Sector ETF",
    "Cons. Disc. Sector ETF",
    "Cons. Staples Sector ETF",
    "Industrials Sector ETF",
    "Healthcare Sector ETF",
    "Materials Sector ETF",
    "Utilities Sector ETF",
    "US REIT Sector ETF",
    "VIX Volatility Proxy ETF",
    "US TIPS Inflation ETF",
    "US Dollar Index ETF",
  ],
  "Global ETFs": [
    "Emerging Markets ETF",
    "China ETF",
    "Japan ETF",
    "Europe ETF",
    "Gold ETF",
    "Silver ETF",
    "Crude Oil ETF",
    "Steel/Mining ETF",
  ],
  "Forex Pairs": ["EUR/USD", "USD/JPY", "GBP/USD", "AUD/USD", "USD/CHF"],
  Crypto: ["Bitcoin", "Ethereum", "Solana", "XRP"],
  "India Market Proxies": ["NIFTY 50 ETF", "Sensex 30 ETF"],
  ADRs: ["Infosys ADR", "HDFC Bank ADR"],
} as const;

// Name to Symbol mapping
export const NAME_TO_SYMBOL: Record<string, string> = {
  // US Stocks
  Apple: "AAPL.US",
  Microsoft: "MSFT.US",
  Tesla: "TSLA.US",
  NVIDIA: "NVDA.US",
  "Meta Platforms": "META.US",
  Alphabet: "GOOGL.US",
  Amazon: "AMZN.US",
  Netflix: "NFLX.US",
  MicroStrategy: "MSTR.US",
  "C3.ai": "AI.US",

  // US ETFs
  "S&P 500 ETF": "SPY.US",
  "Nasdaq 100 ETF": "QQQ.US",
  "Dow Jones ETF": "DIA.US",
  "7-10Y Treasury ETF": "IEF.US",
  "20Y+ Treasury ETF": "TLT.US",
  "1-3Y Treasury ETF": "SHY.US",
  "Tech Sector ETF": "XLK.US",
  "Financials Sector ETF": "XLF.US",
  "Energy Sector ETF": "XLE.US",
  "Cons. Disc. Sector ETF": "XLY.US",
  "Cons. Staples Sector ETF": "XLP.US",
  "Industrials Sector ETF": "XLI.US",
  "Healthcare Sector ETF": "XLV.US",
  "Materials Sector ETF": "XLB.US",
  "Utilities Sector ETF": "XLU.US",
  "US REIT Sector ETF": "VNQ.US",
  "VIX Volatility Proxy ETF": "VXX.US",
  "US TIPS Inflation ETF": "TIP.US",
  "US Dollar Index ETF": "UUP.US",

  // Global ETFs
  "Emerging Markets ETF": "EEM.US",
  "China ETF": "FXI.US",
  "Japan ETF": "EWJ.US",
  "Europe ETF": "FEZ.US",
  "Gold ETF": "GLD.US",
  "Silver ETF": "SLV.US",
  "Crude Oil ETF": "USO.US",
  "Steel/Mining ETF": "SLX.US",

  // Forex
  "EUR/USD": "EURUSD.FOREX",
  "USD/JPY": "USDJPY.FOREX",
  "GBP/USD": "GBPUSD.FOREX",
  "AUD/USD": "AUDUSD.FOREX",
  "USD/CHF": "USDCHF.FOREX",

  // Crypto
  Bitcoin: "BTC-USD.CC",
  Ethereum: "ETH-USD.CC",
  Solana: "SOL-USD.CC",
  XRP: "XRP-USD.CC",

  // India Market Proxies
  "NIFTY 50 ETF": "SETFNIF50.NSE",
  "Sensex 30 ETF": "SENSEXIETF.NSE",

  // ADRs
  "Infosys ADR": "INFY.US",
  "HDFC Bank ADR": "HDB.US",
};

// Symbol to Name mapping (reverse)
export const SYMBOL_TO_NAME: Record<string, string> = Object.fromEntries(
  Object.entries(NAME_TO_SYMBOL).map(([name, symbol]) => [symbol, name]),
);

// Full asset list with metadata
export const ASSETS: Asset[] = Object.entries(NAME_TO_SYMBOL).map(
  ([name, symbol]) => {
    // Determine type from symbol suffix
    let type: Asset["type"];
    let exchange: string | undefined;

    if (symbol.endsWith(".US")) {
      // Check if it's an ETF based on category
      const isETF = Object.values(ASSET_CATEGORIES).some(
        (category) =>
          (category as readonly string[]).includes(name) &&
          (category === ASSET_CATEGORIES["US ETFs"] ||
            category === ASSET_CATEGORIES["Global ETFs"]),
      );
      type = isETF ? "etf" : "stock";
      exchange = "US";
    } else if (symbol.endsWith(".FOREX")) {
      type = "forex";
      exchange = "FOREX";
    } else if (symbol.endsWith(".CC")) {
      type = "crypto";
      exchange = "Crypto";
    } else if (symbol.endsWith(".NSE")) {
      type = "etf";
      exchange = "NSE";
    } else {
      type = "stock";
    }

    // Find category
    let category = "Other";
    for (const [cat, names] of Object.entries(ASSET_CATEGORIES)) {
      if ((names as readonly string[]).includes(name)) {
        category = cat;
        break;
      }
    }

    return {
      symbol,
      name,
      type,
      category,
      exchange,
    };
  },
);

// Helper functions
export const getSymbolFromName = (name: string): string | undefined => {
  return NAME_TO_SYMBOL[name];
};

export const getNameFromSymbol = (symbol: string): string | undefined => {
  return SYMBOL_TO_NAME[symbol];
};

export const getAssetsByType = (type: Asset["type"]): Asset[] => {
  return ASSETS.filter((asset) => asset.type === type);
};

export const getAssetsByCategory = (category: string): Asset[] => {
  return ASSETS.filter((asset) => asset.category === category);
};

export const searchAssets = (query: string): Asset[] => {
  const q = query.toLowerCase();
  return ASSETS.filter(
    (asset) =>
      asset.name.toLowerCase().includes(q) ||
      asset.symbol.toLowerCase().includes(q),
  );
};

// Export convenient lists
export const ALL_ASSET_NAMES = Object.keys(NAME_TO_SYMBOL);
export const ALL_ASSET_SYMBOLS = Object.values(NAME_TO_SYMBOL);

// Get popular/most active assets for dropdowns
export const POPULAR_ASSETS = [
  "Apple",
  "Microsoft",
  "Tesla",
  "NVIDIA",
  "Amazon",
  "Alphabet",
  "Meta Platforms",
  "S&P 500 ETF",
  "Nasdaq 100 ETF",
  "Bitcoin",
  "Ethereum",
];
