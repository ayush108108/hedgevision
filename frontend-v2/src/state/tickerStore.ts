import { create } from "zustand";

export interface PriceData {
  symbol: string;
  price: number;
  change: number;
  changePercent: number;
}

interface TickerState {
  selectedTicker: string;
  availableTickers: string[];
  prices: Record<string, PriceData>;
  setSelectedTicker: (ticker: string) => void;
  upsertPrice: (symbol: string, partial: Partial<PriceData>) => void;
  setPrices: (prices: Record<string, PriceData>) => void;
}

const INITIAL_TICKERS = ["BTC/USD", "ETH/USD", "SPY", "AAPL"];

export const useTickerStore = create<TickerState>((set) => ({
  selectedTicker: INITIAL_TICKERS[0],
  availableTickers: INITIAL_TICKERS,
  prices: {
    "BTC/USD": {
      symbol: "BTC/USD",
      price: 42850.5,
      change: 1250.75,
      changePercent: 3.01,
    },
    "ETH/USD": {
      symbol: "ETH/USD",
      price: 2285.3,
      change: 85.2,
      changePercent: 3.88,
    },
    SPY: { symbol: "SPY", price: 589.45, change: 12.3, changePercent: 2.13 },
    AAPL: { symbol: "AAPL", price: 234.67, change: -5.2, changePercent: -2.17 },
  },
  setSelectedTicker: (ticker) => set({ selectedTicker: ticker }),
  upsertPrice: (symbol, partial) =>
    set((state) => {
      const prev = state.prices[symbol] || {
        symbol,
        price: 0,
        change: 0,
        changePercent: 0,
      };
      const nextPrice = partial.price ?? prev.price;
      const change = partial.change ?? nextPrice - prev.price;
      const changePercent =
        partial.changePercent ?? (prev.price ? (change / prev.price) * 100 : 0);
      return {
        prices: {
          ...state.prices,
          [symbol]: {
            symbol,
            price: nextPrice,
            change,
            changePercent,
          },
        },
      };
    }),
  setPrices: (prices) => set({ prices }),
}));
