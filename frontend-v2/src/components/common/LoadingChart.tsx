import React, { useEffect, useState } from "react";
import { TrendingUp, Activity, BarChart3 } from "lucide-react";

const loadingMessages = [
  "Calculating metrics for you...",
  "Computing correlations carefully...",
  "Analyzing market relationships...",
  "Crunching the numbers...",
  "Processing statistical models...",
  "Evaluating market data...",
];

export function LoadingChart() {
  const [messageIndex, setMessageIndex] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setMessageIndex((prev) => (prev + 1) % loadingMessages.length);
    }, 2500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] py-16">
      {/* Animated Chart Icon */}
      <div className="relative mb-8">
        {/* Pulsing background circles */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-32 h-32 rounded-full bg-blue-500/20 animate-ping" style={{ animationDuration: '2s' }} />
        </div>
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-24 h-24 rounded-full bg-purple-500/20 animate-ping" style={{ animationDuration: '1.5s', animationDelay: '0.3s' }} />
        </div>
        
        {/* Center icon with rotation */}
        <div className="relative z-10 w-20 h-20 rounded-full bg-gradient-to-br from-blue-500 to-purple-500 flex items-center justify-center shadow-lg shadow-blue-500/50 animate-pulse">
          <Activity className="text-white" size={32} />
        </div>

        {/* Orbiting icons */}
        <div className="absolute inset-0 animate-spin" style={{ animationDuration: '3s' }}>
          <div className="absolute -top-2 left-1/2 -translate-x-1/2 w-10 h-10 rounded-full bg-gradient-to-br from-green-500 to-emerald-500 flex items-center justify-center shadow-lg">
            <TrendingUp className="text-white" size={20} />
          </div>
        </div>
        <div className="absolute inset-0 animate-spin" style={{ animationDuration: '3s', animationDelay: '1s' }}>
          <div className="absolute -bottom-2 left-1/2 -translate-x-1/2 w-10 h-10 rounded-full bg-gradient-to-br from-pink-500 to-rose-500 flex items-center justify-center shadow-lg">
            <BarChart3 className="text-white" size={20} />
          </div>
        </div>
      </div>

      {/* Loading bar */}
      <div className="w-64 h-2 bg-slate-800 rounded-full overflow-hidden mb-6">
        <div className="h-full bg-gradient-to-r from-blue-500 via-purple-500 to-pink-500 animate-pulse" style={{ width: '70%' }} />
      </div>

      {/* Message */}
      <div className="text-center">
        <h3 className="text-xl font-semibold text-white mb-2 animate-pulse">
          {loadingMessages[messageIndex]}
        </h3>
        <p className="text-sm text-gray-500">
          This may take a few moments
        </p>
      </div>

      {/* Animated dots */}
      <div className="flex gap-2 mt-4">
        <div className="w-2 h-2 rounded-full bg-blue-500 animate-bounce" style={{ animationDelay: '0ms' }} />
        <div className="w-2 h-2 rounded-full bg-purple-500 animate-bounce" style={{ animationDelay: '150ms' }} />
        <div className="w-2 h-2 rounded-full bg-pink-500 animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
    </div>
  );
}
