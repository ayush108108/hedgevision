import React, { useState, Suspense, lazy } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Layout } from "./components/Layout";
import { ErrorBoundary } from "./components/common/ErrorBoundary";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { DisclaimerModal } from "./components/ui/DisclaimerModal";
import { DisclaimerFooter } from "./components/ui/DisclaimerFooter";
import { features } from "./config/features";

// ---------- Core pages (always loaded) ----------
const HomePage = lazy(() => import("./pages/HomePage").then(m => ({ default: m.HomePage })));
const CorrelationPage = lazy(() => import("./pages/CorrelationPage").then(m => ({ default: m.CorrelationPage })));
const CointegrationPage = lazy(() => import("./pages/CointegrationPage").then(m => ({ default: m.CointegrationPage })));
const PairAnalysisPage = lazy(() => import("./pages/PairAnalysisPage").then(m => ({ default: m.PairAnalysisPage })));
const TradingSignalsPage = lazy(() => import("./pages/TradingSignalsPage").then(m => ({ default: m.TradingSignalsPage })));
const EducationPage = lazy(() => import("./pages/EducationPage").then(m => ({ default: m.EducationPage })));

// ---------- Optional pages (feature-flagged, tree-shaken when disabled) ----------
const PortfolioPage = features.portfolio ? lazy(() => import("./pages/PortfolioPage").then(m => ({ default: m.PortfolioPage }))) : null;
const NewsPage = features.news ? lazy(() => import("./pages/NewsPage").then(m => ({ default: m.NewsPage }))) : null;
const TradingCalculatorPage = features.calculator ? lazy(() => import("./pages/TradingCalculatorPage").then(m => ({ default: m.TradingCalculatorPage }))) : null;
const WatchlistPage = features.watchlist ? lazy(() => import("./pages/WatchlistPage").then(m => ({ default: m.WatchlistPage }))) : null;
const BacktestPage = features.backtest ? lazy(() => import("./pages/BacktestPage").then(m => ({ default: m.BacktestPage }))) : null;
const OnboardingPage = features.onboarding ? lazy(() => import("./pages/OnboardingPage").then(m => ({ default: m.OnboardingPage }))) : null;
const LoginPage = features.auth ? lazy(() => import("./pages/LoginPage").then(m => ({ default: m.LoginPage }))) : null;
const SignUpPage = features.auth ? lazy(() => import("./pages/SignUpPage").then(m => ({ default: m.SignUpPage }))) : null;

const LoadingFallback = () => (
  <div className="flex items-center justify-center min-h-screen">
    <div className="text-center">
      <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto mb-4"></div>
      <p className="text-gray-400">Loading...</p>
    </div>
  </div>
);

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 5 * 60 * 1000,
      refetchOnWindowFocus: false,
      retry: 2,
    },
  },
});

function App() {
  const [disclaimerAccepted, setDisclaimerAccepted] = useState(false);

  return (
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <DisclaimerModal onAccept={() => setDisclaimerAccepted(true)} />
        {disclaimerAccepted && (
          <BrowserRouter>
            <div className="flex min-h-screen flex-col">
              <Layout>
                <Suspense fallback={<LoadingFallback />}>
                  <Routes>
                    {/* Core routes */}
                    <Route path="/" element={<HomePage />} />
                    <Route path="/correlation" element={<CorrelationPage />} />
                    <Route path="/cointegration" element={<CointegrationPage />} />
                    <Route path="/pair-analysis" element={<PairAnalysisPage />} />
                    <Route path="/signals" element={<TradingSignalsPage />} />
                    <Route path="/learn" element={<EducationPage />} />

                    {/* Feature-flagged routes */}
                    {PortfolioPage && <Route path="/portfolio" element={<PortfolioPage />} />}
                    {NewsPage && <Route path="/news" element={<NewsPage />} />}
                    {TradingCalculatorPage && <Route path="/calculator" element={<TradingCalculatorPage />} />}
                    {WatchlistPage && <Route path="/watchlist" element={<WatchlistPage />} />}
                    {BacktestPage && <Route path="/backtest" element={<BacktestPage />} />}
                    {OnboardingPage && <Route path="/onboarding" element={<OnboardingPage />} />}
                    {LoginPage && <Route path="/login" element={<LoginPage />} />}
                    {SignUpPage && <Route path="/signup" element={<SignUpPage />} />}
                    {SignUpPage && <Route path="/register" element={<SignUpPage />} />}

                    {/* Catch-all */}
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </Suspense>
              </Layout>
              <DisclaimerFooter />
            </div>
          </BrowserRouter>
        )}
      </QueryClientProvider>
    </ErrorBoundary>
  );
}

export default App;
