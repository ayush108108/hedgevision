import React, { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Newspaper, RefreshCw, TrendingUp, TrendingDown, AlertCircle, ExternalLink, Filter } from "lucide-react";
import { getNews, type NewsArticle } from "../services/api";

export function NewsPage() {
  const [selectedFilter, setSelectedFilter] = useState<"all" | "positive" | "negative" | "neutral">("all");

  // Fetch news from API
  const {
    data: newsData,
    isLoading,
    error,
    refetch,
    isFetching,
  } = useQuery({
    queryKey: ["news", selectedFilter],
    queryFn: () =>
      getNews({
        sentiment: selectedFilter === "all" ? undefined : selectedFilter,
        limit: 50,
      }),
    refetchInterval: 300000, // Refresh every 5 minutes
  });

  const handleRefresh = () => {
    refetch();
  };

  // Mock data for demo fallback
  const mockNews: NewsArticle[] = [
    {
      id: "1",
      title: "Federal Reserve Signals Potential Rate Cuts in Q2 2025",
      source: "Bloomberg",
      sentiment: "positive",
      sentiment_score: 0.75,
      sentiment_scores: { positive: 0.75, negative: 0.05, neutral: 0.20 },
      timestamp: new Date(Date.now() - 3600000).toISOString(),
      summary: "The Federal Reserve indicated potential interest rate adjustments in the coming quarter, citing improved inflation metrics and stable employment data.",
      url: "#",
      relatedAssets: ["SPY", "TLT", "GLD"],
    },
    {
      id: "2",
      title: "Tech Sector Faces Regulatory Headwinds in Europe",
      source: "Reuters",
      sentiment: "negative",
      sentiment_score: -0.65,
      sentiment_scores: { positive: 0.10, negative: 0.65, neutral: 0.25 },
      timestamp: new Date(Date.now() - 7200000).toISOString(),
      summary: "New EU regulations targeting big tech companies could impact profit margins and operational flexibility for major technology firms.",
      url: "#",
      relatedAssets: ["QQQ", "AAPL", "MSFT"],
    },
    {
      id: "3",
      title: "Oil Prices Stabilize Amid OPEC+ Production Agreement",
      source: "Financial Times",
      sentiment: "neutral",
      sentiment_score: 0.05,
      sentiment_scores: { positive: 0.35, negative: 0.30, neutral: 0.35 },
      timestamp: new Date(Date.now() - 10800000).toISOString(),
      summary: "OPEC+ members reached a consensus on production targets, leading to market stabilization in energy commodities.",
      url: "#",
      relatedAssets: ["USO", "XLE"],
    },
    {
      id: "4",
      title: "Emerging Markets Show Strong Q1 Performance",
      source: "Wall Street Journal",
      sentiment: "positive",
      sentiment_score: 0.80,
      sentiment_scores: { positive: 0.80, negative: 0.05, neutral: 0.15 },
      timestamp: new Date(Date.now() - 14400000).toISOString(),
      summary: "Developing economies outperformed expectations in the first quarter, driven by infrastructure investments and improved trade relationships.",
      url: "#",
      relatedAssets: ["EEM", "VWO"],
    },
  ];

  const filteredNews = newsData?.articles || [];

  // Use real data if available, otherwise fallback to mock
  const displayNews = filteredNews.length > 0 ? filteredNews : mockNews.filter(
    item => selectedFilter === "all" || item.sentiment === selectedFilter
  );

  const getSentimentColor = (sentiment: string) => {
    switch (sentiment) {
      case "positive":
        return "text-green-400 bg-green-500/10 border-green-500/30";
      case "negative":
        return "text-red-400 bg-red-500/10 border-red-500/30";
      default:
        return "text-gray-400 bg-gray-500/10 border-gray-500/30";
    }
  };

  const getSentimentIcon = (sentiment: string) => {
    switch (sentiment) {
      case "positive":
        return <TrendingUp className="w-4 h-4" />;
      case "negative":
        return <TrendingDown className="w-4 h-4" />;
      default:
        return <AlertCircle className="w-4 h-4" />;
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900/20 to-gray-900">
      {/* Header */}
      <div className="border-b border-white/10 bg-gradient-to-r from-blue-500/10 to-purple-500/10 backdrop-blur-xl">
        <div className="max-w-[1920px] mx-auto px-6 py-8">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="p-3 rounded-lg bg-blue-500/20 border border-blue-500/30">
                <Newspaper className="h-6 w-6 text-blue-400" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-white">Market Intelligence</h1>
                <p className="text-gray-400 text-sm mt-1">
                  Real-time news and sentiment analysis for trading pairs
                </p>
              </div>
            </div>
            <button
              onClick={handleRefresh}
              disabled={isFetching}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-500/20 hover:bg-blue-500/30 border border-blue-500/30 text-blue-400 transition-all disabled:opacity-50"
            >
              <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
              Refresh
            </button>
          </div>

          {/* Filters */}
          <div className="flex items-center gap-2">
            <Filter className="w-4 h-4 text-gray-400" />
            <span className="text-sm text-gray-400 mr-2">Filter by sentiment:</span>
            <div className="flex gap-2">
              {["all", "positive", "negative", "neutral"].map((filter) => (
                <button
                  key={filter}
                  onClick={() => setSelectedFilter(filter as any)}
                  className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                    selectedFilter === filter
                      ? "bg-blue-500/20 text-blue-400 border border-blue-500/30"
                      : "bg-white/5 text-gray-400 border border-transparent hover:bg-white/10"
                  }`}
                >
                  {filter.charAt(0).toUpperCase() + filter.slice(1)}
                </button>
              ))}
            </div>
          </div>
        </div>
      </div>

      {/* News Feed */}
      <div className="max-w-[1920px] mx-auto px-6 py-8">
        {isLoading ? (
          <div className="text-center py-12">
            <RefreshCw className="w-12 h-12 text-blue-400 mx-auto mb-4 animate-spin" />
            <p className="text-gray-400">Loading news...</p>
          </div>
        ) : error ? (
          <div className="text-center py-12">
            <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
            <p className="text-gray-400">Error loading news. Showing demo data.</p>
          </div>
        ) : displayNews.length === 0 ? (
          <div className="text-center py-12">
            <AlertCircle className="w-12 h-12 text-gray-400 mx-auto mb-4" />
            <p className="text-gray-400">No news articles found</p>
          </div>
        ) : (
          <div className="space-y-4">
            {displayNews.map((item) => (
              <div
                key={item.id}
                className="bg-white/5 backdrop-blur-xl border border-white/10 rounded-lg p-6 hover:bg-white/10 transition-all"
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold text-white">{item.title}</h3>
                      <span
                        className={`flex items-center gap-1 px-2 py-1 rounded text-xs font-medium border ${getSentimentColor(
                          item.sentiment
                        )}`}
                      >
                        {getSentimentIcon(item.sentiment)}
                        {item.sentiment}
                      </span>
                    </div>

                    <div className="flex items-center gap-4 text-sm text-gray-400 mb-3">
                      <span className="font-medium">{item.source}</span>
                      <span>•</span>
                      <span>{new Date(item.timestamp).toLocaleString()}</span>
                    </div>

                    <p className="text-gray-300 mb-4">{item.summary}</p>

                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-xs text-gray-500">Related assets:</span>
                        {item.relatedAssets.map((asset) => (
                          <span
                            key={asset}
                            className="px-2 py-1 rounded bg-blue-500/10 text-blue-400 text-xs font-mono border border-blue-500/20"
                          >
                            {asset}
                          </span>
                        ))}
                      </div>
                      <a
                        href={item.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="flex items-center gap-1 text-blue-400 hover:text-blue-300 text-sm transition-colors"
                      >
                        Read more
                        <ExternalLink className="w-3 h-3" />
                      </a>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Footer Disclaimer */}
        <div className="mt-8 bg-blue-500/10 border border-blue-500/30 rounded-lg p-6">
          <div className="flex items-start gap-3">
            <AlertCircle className="w-5 h-5 text-blue-400 mt-0.5" />
            <div>
              <h4 className="text-white font-semibold mb-2">
                {newsData?.articles ? 'Live News Feed Active' : 'Demo Mode'}
              </h4>
              <p className="text-gray-300 text-sm">
                {newsData?.articles 
                  ? 'You are viewing live market news with AI-powered sentiment analysis. Data refreshes automatically every 5 minutes.'
                  : 'API connection unavailable - showing demo data. Real-time news integration features:'
                }
              </p>
              {!newsData?.articles && (
                <ul className="mt-3 space-y-1 text-gray-300 text-sm">
                  <li className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                    Live news feeds from multiple sources (Bloomberg, Reuters, Financial Times)
                  </li>
                  <li className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                    AI-powered sentiment analysis using FinBERT and LLM models
                  </li>
                  <li className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                    Automatic asset correlation and impact assessment
                  </li>
                  <li className="flex items-center gap-2">
                    <div className="w-1.5 h-1.5 rounded-full bg-blue-400" />
                    Custom alerts for news affecting your watchlist pairs
                  </li>
                </ul>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
