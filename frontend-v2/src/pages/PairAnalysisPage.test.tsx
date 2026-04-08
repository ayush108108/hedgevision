import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, MemoryRouter } from "react-router-dom";
import { PairAnalysisPage } from "./PairAnalysisPage";
import * as pairService from "../services/pair";

// Mock the pair service
vi.mock("../services/pair");

// Mock rolling metrics service
vi.mock("../services/rollingMetrics", () => ({
  getRollingMetrics: vi.fn().mockResolvedValue({ data: [] }),
  MetricType: {},
}));

// Test utilities
const createTestQueryClient = () =>
  new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  });

const renderWithProviders = (
  ui: React.ReactElement,
  route?: string,
) => {
  const queryClient = createTestQueryClient();
  return render(
    <QueryClientProvider client={queryClient}>
      {route ? (
        <MemoryRouter initialEntries={[route]}>{ui}</MemoryRouter>
      ) : (
        <BrowserRouter>{ui}</BrowserRouter>
      )}
    </QueryClientProvider>,
  );
};

describe("PairAnalysisPage", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Loading State", () => {
    it("should display loading indicator when isLoading is true", async () => {
      // Mock the API call to never resolve (keeps loading state)
      vi.mocked(pairService.getPairAnalysis).mockImplementation(
        () => new Promise(() => {}),
      );

      renderWithProviders(<PairAnalysisPage />);

      // LoadingChart shows rotating messages like "Calculating metrics for you..."
      await waitFor(() => {
        expect(
          screen.getByText(/Calculating metrics for you/i),
        ).toBeInTheDocument();
      });
    });

    it("should show Refreshing text on button when loading", async () => {
      vi.mocked(pairService.getPairAnalysis).mockImplementation(
        () => new Promise(() => {}),
      );

      renderWithProviders(<PairAnalysisPage />);

      await waitFor(() => {
        expect(screen.getByText("Refreshing...")).toBeInTheDocument();
      });
    });
  });

  describe("Error State", () => {
    it("should display error message when error is present", async () => {
      const errorMessage = "Failed to fetch pair analysis";

      // Mock the API call to reject with an error
      vi.mocked(pairService.getPairAnalysis).mockRejectedValue(
        new Error(errorMessage),
      );

      renderWithProviders(<PairAnalysisPage />);

      // Wait for error to appear
      await waitFor(() => {
        expect(screen.getByText(`Error: ${errorMessage}`)).toBeInTheDocument();
      });
    });

    it("should display error in red-themed card", async () => {
      vi.mocked(pairService.getPairAnalysis).mockRejectedValue(
        new Error("Network error"),
      );

      renderWithProviders(<PairAnalysisPage />);

      await waitFor(() => {
        const errorDiv = screen.getByText(/Error:/i).closest(".premium-card");
        expect(errorDiv).toHaveClass("bg-red-500/10");
        expect(errorDiv).toHaveClass("border-red-500/30");
      });
    });

    it("should handle invalid asset selection error", async () => {
      vi.mocked(pairService.getPairAnalysis).mockRejectedValue(
        new Error("Invalid asset selection"),
      );

      renderWithProviders(<PairAnalysisPage />);

      await waitFor(() => {
        expect(
          screen.getByText(/Error: Invalid asset selection/i),
        ).toBeInTheDocument();
      });
    });

    it("should display error text in red color", async () => {
      vi.mocked(pairService.getPairAnalysis).mockRejectedValue(
        new Error("Test error"),
      );

      renderWithProviders(<PairAnalysisPage />);

      await waitFor(() => {
        const errorText = screen.getByText(/Error:/i);
        expect(errorText).toHaveClass("text-red-400");
      });
    });
  });

  describe("Initial Render", () => {
    it("should render page header with title", () => {
      renderWithProviders(<PairAnalysisPage />);

      expect(screen.getByText("Pair Analysis")).toBeInTheDocument();
      expect(
        screen.getByText(/Deep statistical analysis of two assets/i),
      ).toBeInTheDocument();
    });

    it("should render configuration controls section", () => {
      renderWithProviders(<PairAnalysisPage />);

      expect(screen.getByText("Configure Analysis")).toBeInTheDocument();
      // Labels are rendered as text within label elements
      expect(screen.getByText("Asset 1")).toBeInTheDocument();
      expect(screen.getByText("Asset 2")).toBeInTheDocument();
      expect(screen.getByText("Timeframe")).toBeInTheDocument();
    });

    it("should render refresh button", () => {
      renderWithProviders(<PairAnalysisPage />);

      // Button shows either "Refresh Analysis" or "Refreshing..." depending on query state
      const refreshBtn = screen.getByText(/Refresh Analysis|Refreshing/i);
      expect(refreshBtn).toBeInTheDocument();
    });
  });

  describe("Success State", () => {
    const mockPairAnalysisData = {
      asset1: "AAPL.US",
      asset2: "MSFT.US",
      correlation: 0.85,
      volatility_ratio: 1.23,
      pair_metrics: {
        correlation: 0.85,
        volatility_ratio: 1.23,
      },
      price_data: {
        dates: ["2023-01-01", "2023-01-02", "2023-01-03"],
        asset1_prices: [100, 102, 101],
        asset2_prices: [200, 204, 202],
      },
      spread_data: [
        { date: "2023-01-01", spread: 0.5, zscore: 0.1 },
        { date: "2023-01-02", spread: 0.6, zscore: 0.2 },
        { date: "2023-01-03", spread: 0.55, zscore: 0.15 },
      ],
      regression_metrics: {
        alpha: 0.05,
        beta: 0.95,
        r_squared: 0.72,
      },
      cointegration_results: {
        adf_statistic: -3.5,
        adf_pvalue: 0.01,
        is_cointegrated: true,
      },
    };

    it("should display data when successfully loaded", async () => {
      vi.mocked(pairService.getPairAnalysis).mockResolvedValue(
        mockPairAnalysisData,
      );

      renderWithProviders(<PairAnalysisPage />);

      await waitFor(() => {
        // Check for correlation value
        expect(screen.getByText("0.850")).toBeInTheDocument();
        expect(screen.getByText("Correlation")).toBeInTheDocument();
      });
    });

    it("should not show error when data is present", async () => {
      vi.mocked(pairService.getPairAnalysis).mockResolvedValue(
        mockPairAnalysisData,
      );

      renderWithProviders(<PairAnalysisPage />);

      await waitFor(() => {
        expect(screen.queryByText(/Error:/i)).not.toBeInTheDocument();
      });
    });

    it("should resolve screener raw symbols from the URL into the API request", async () => {
      vi.mocked(pairService.getPairAnalysis).mockResolvedValue(
        mockPairAnalysisData,
      );

      renderWithProviders(
        <PairAnalysisPage />,
        "/pair-analysis?asset1=BTC-USD&asset2=ETH-USD",
      );

      await waitFor(() => {
        expect(pairService.getPairAnalysis).toHaveBeenCalledWith(
          expect.objectContaining({
            asset1: "BTC-USD.CC",
            asset2: "ETH-USD.CC",
          }),
        );
      });

      expect(screen.getByText("Bitcoin")).toBeInTheDocument();
      expect(screen.getByText("Ethereum")).toBeInTheDocument();
    });
  });

  describe("Integration", () => {
    it("should transition from loading to error state", async () => {
      vi.mocked(pairService.getPairAnalysis).mockRejectedValue(
        new Error("API Error"),
      );

      renderWithProviders(<PairAnalysisPage />);

      // Then show error
      await waitFor(() => {
        expect(screen.getByText(/Error: API Error/i)).toBeInTheDocument();
      });
    });
  });
});
