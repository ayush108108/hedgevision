import React, { useState } from "react";
import { Zap, Send, MessageCircle, Mail } from "lucide-react";
import { getStructuredVerdict, type MarketIntelResponse } from "../services/marketIntel";
import { useBYOKStore, type BYOKProvider } from "../state/byokStore";
import { StructuredVerdictCard } from "../components/cards/StructuredVerdictCard";
import { BacktestPage } from "./BacktestPage";

export function TradingSignalsPage() {
  const { useLlm, provider, model, setUseLlm, setProvider, setModel } = useBYOKStore();
  const [ticker, setTicker] = useState("BTC-USD");
  const [verdictData, setVerdictData] = useState<MarketIntelResponse | null>(null);
  const [verdictError, setVerdictError] = useState<string | null>(null);
  const [verdictLoading, setVerdictLoading] = useState(false);
  const [activeTab, setActiveTab] = useState<"signals" | "backtest">("signals");
  const [chatMessages, setChatMessages] = useState<Array<{ id: string; text: string; sender: "user" | "bot"; timestamp: Date }>>([
    {
      id: "1",
      text: "👋 Welcome to AI Trading Signals Assistant! This feature is under active development and will be available soon.",
      sender: "bot",
      timestamp: new Date(),
    },
    {
      id: "2",
      text: "📊 I'll help you analyze cointegrated pairs, identify trading opportunities, and manage your portfolio.",
      sender: "bot",
      timestamp: new Date(Date.now() + 1000),
    },
  ]);
  const [inputMessage, setInputMessage] = useState("");

  const handleLoadVerdict = async () => {
    setVerdictLoading(true);
    setVerdictError(null);
    try {
      const data = await getStructuredVerdict({
        ticker,
        period: "1y",
        use_llm: useLlm && provider !== "rules",
        provider,
        model,
      });
      setVerdictData(data);
    } catch (error: any) {
      setVerdictError(error?.response?.data?.detail || error?.message || "Failed to load verdict");
    } finally {
      setVerdictLoading(false);
    }
  };

  const handleSendMessage = () => {
    if (!inputMessage.trim()) return;

    // Add user message
    const newMessage = {
      id: Date.now().toString(),
      text: inputMessage,
      sender: "user" as const,
      timestamp: new Date(),
    };

    setChatMessages((prev) => [...prev, newMessage]);

    // Simulate bot response after delay
    setTimeout(() => {
      const responses = [
        "🔨 This feature is still being built. We're working hard to bring you an intelligent trading signal analyzer!",
        "⚙️ Our team is integrating real-time market data and ML models. Coming very soon!",
        "📈 In the meantime, you can explore our Cointegration Screener to find trading opportunities.",
        "🚀 Thank you for your patience! We're building something amazing.",
      ];
      const randomResponse = responses[Math.floor(Math.random() * responses.length)];

      setChatMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          text: randomResponse,
          sender: "bot",
          timestamp: new Date(),
        },
      ]);
    }, 800);

    setInputMessage("");
  };

  // Disabled: This page is static coming soon, signals table doesn't exist yet
  // const {
  //   data: signalsResp,
  //   isLoading,
  //   error,
  //   refetch,
  //   isFetching,
  // } = useQuery({
  //   queryKey: ["signals", "active"],
  //   queryFn: () => getActiveSignals({ granularity: "daily" }),
  //   refetchInterval: 15000,
  //   retry: 2,
  // });

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-blue-900/20 to-gray-900">
      {/* Header */}
      <div className="border-b border-white/10 bg-gradient-to-r from-blue-500/10 to-purple-500/10 backdrop-blur-xl">
        <div className="max-w-[1920px] mx-auto px-6 py-8 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-2xl bg-gradient-to-br from-blue-500 to-purple-500 shadow-xl shadow-blue-500/25">
              <Zap className="w-7 h-7 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-3 mb-2">
                <h1 className="text-4xl font-bold text-white tracking-tight">Trading Signals</h1>
                <span className="px-3 py-1 rounded-full bg-gradient-to-r from-cyan-500/30 to-blue-500/30 border border-cyan-500/50 text-cyan-300 text-xs font-bold uppercase tracking-wider flex items-center gap-1.5">
                  <span className="w-2 h-2 rounded-full bg-cyan-400 animate-pulse" />
                  AI
                </span>
              </div>
              <p className="text-blue-200/70 text-lg mt-1">Live opportunities from cointegrated pairs</p>
            </div>
          </div>
        </div>

        {/* Tab navigation */}
        <div className="max-w-[1920px] mx-auto px-6 flex gap-1 pb-0">
          <button
            onClick={() => setActiveTab("signals")}
            className={`px-5 py-3 text-sm font-medium rounded-t-lg transition-colors ${
              activeTab === "signals"
                ? "bg-slate-900 text-white border-t border-l border-r border-white/10"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            AI Verdict
          </button>
          <button
            onClick={() => setActiveTab("backtest")}
            className={`px-5 py-3 text-sm font-medium rounded-t-lg transition-colors ${
              activeTab === "backtest"
                ? "bg-slate-900 text-white border-t border-l border-r border-white/10"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            Backtest Engine
          </button>
        </div>
      </div>

      {/* Tab: AI Verdict */}
      {activeTab === "signals" && (
        <div className="max-w-[1920px] mx-auto px-6 py-6">
          {/* Verdict controls */}
          <div className="rounded-2xl border border-white/10 bg-slate-900/60 p-5 mb-6">
            <div className="flex flex-wrap items-end gap-3">
              <div>
                <label className="text-xs text-slate-400 block mb-1">Ticker</label>
                <input
                  value={ticker}
                  onChange={(e) => setTicker(e.target.value.toUpperCase())}
                  className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white"
                  placeholder="BTC-USD"
                />
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Provider</label>
                <select
                  value={provider}
                  onChange={(e) => setProvider(e.target.value as BYOKProvider)}
                  className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white"
                  title="BYOK Provider"
                >
                  <option value="rules">Rules</option>
                  <option value="cpu">CPU Local</option>
                  <option value="openai">OpenAI</option>
                  <option value="anthropic">Anthropic</option>
                  <option value="ollama">Ollama</option>
                </select>
              </div>
              <div>
                <label className="text-xs text-slate-400 block mb-1">Model</label>
                <input
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-white min-w-[180px]"
                />
              </div>
              <label className="text-slate-300 text-sm inline-flex items-center gap-2 ml-2">
                <input
                  type="checkbox"
                  checked={useLlm}
                  onChange={(e) => setUseLlm(e.target.checked)}
                />
                Use LLM
              </label>
              <button
                onClick={handleLoadVerdict}
                className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white"
              >
                {verdictLoading ? "Loading..." : "Load Verdict"}
              </button>
            </div>

            {verdictError && <p className="text-rose-300 text-sm mt-3">{verdictError}</p>}
            {verdictData && (
              <div className="mt-4">
                <StructuredVerdictCard ticker={verdictData.ticker} verdict={verdictData.verdict} />
              </div>
            )}
          </div>

          {/* Signal assistant chat + waitlist */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
            {/* Chat Interface */}
            <div className="lg:col-span-1 bg-gradient-to-br from-gray-800 to-gray-900 border border-white/10 rounded-2xl overflow-hidden flex flex-col h-[500px]">
              <div className="border-b border-white/10 bg-gradient-to-r from-blue-500/10 to-purple-500/10 p-4 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="p-2 rounded-lg bg-gradient-to-br from-blue-500 to-purple-500">
                    <MessageCircle size={20} className="text-white" />
                  </div>
                  <div>
                    <h3 className="text-white font-semibold">Signal Assistant</h3>
                    <p className="text-xs text-gray-400">Under Development</p>
                  </div>
                </div>
                <span className="px-2 py-1 rounded-full bg-gradient-to-r from-cyan-500/30 to-blue-500/30 border border-cyan-500/50 text-cyan-300 text-xs font-bold uppercase tracking-wider">
                  AI
                </span>
              </div>
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {chatMessages.map((msg) => (
                  <div key={msg.id} className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}>
                    <div
                      className={`max-w-xs px-4 py-2 rounded-lg ${
                        msg.sender === "user"
                          ? "bg-gradient-to-r from-blue-600 to-blue-500 text-white rounded-br-none"
                          : "bg-gray-700 text-gray-100 rounded-bl-none"
                      }`}
                    >
                      <p className="text-sm">{msg.text}</p>
                      <p className={`text-xs mt-1 ${msg.sender === "user" ? "text-blue-100" : "text-gray-400"}`}>
                        {msg.timestamp.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
              <div className="border-t border-white/10 p-4 bg-gray-900/50 space-y-2">
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={inputMessage}
                    onChange={(e) => setInputMessage(e.target.value)}
                    onKeyPress={(e) => e.key === "Enter" && handleSendMessage()}
                    placeholder="Ask about signals..."
                    className="flex-1 px-3 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 text-sm"
                  />
                  <button
                    onClick={handleSendMessage}
                    disabled={!inputMessage.trim()}
                    title="Send message"
                    className="px-4 py-2 rounded-lg bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 disabled:opacity-50 disabled:cursor-not-allowed text-white transition-all duration-200 flex items-center gap-2"
                  >
                    <Send size={16} />
                  </button>
                </div>
                <p className="text-xs text-gray-500 text-center">Demo mode — full AI chat coming soon</p>
              </div>
            </div>

            {/* Waitlist CTA */}
            <div className="lg:col-span-2 px-6 py-8 rounded-2xl bg-gradient-to-r from-blue-500/10 to-purple-500/10 border border-blue-500/20 flex flex-col items-center justify-center text-center">
              <h3 className="text-2xl font-bold text-white mb-3">
                Want Early Access to AI-Powered Features?
              </h3>
              <p className="text-gray-300 mb-6 max-w-xl">
                Join our waitlist to get notified when AI-powered trading signals and advanced analytics go live.
              </p>
              <div className="flex justify-center gap-4 flex-wrap">
                <input
                  type="email"
                  placeholder="Enter your email"
                  className="px-4 py-3 bg-white/5 border border-gray-700 rounded-lg text-white placeholder-gray-500 focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                />
                <button className="px-6 py-3 rounded-lg bg-gradient-to-r from-blue-600 to-blue-500 hover:from-blue-500 hover:to-blue-400 text-white font-medium transition-all flex items-center gap-2 shadow-lg shadow-blue-500/25 hover:shadow-blue-500/40">
                  <Mail className="h-4 w-4" />
                  Join Waitlist
                </button>
              </div>
              <p className="text-xs text-gray-500 mt-4">
                No spam. Unsubscribe anytime. We respect your privacy.
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Tab: Backtest Engine */}
      {activeTab === "backtest" && (
        <div className="max-w-[1920px] mx-auto px-6 py-6">
          <BacktestPage />
        </div>
      )}
    </div>
  );
}
