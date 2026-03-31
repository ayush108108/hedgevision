import React from "react";
import { AlertTriangle } from "lucide-react";

export function DisclaimerFooter() {
  return (
    <footer className="border-t border-gray-800 bg-gray-900/50 backdrop-blur-sm">
      <div className="container mx-auto px-4 py-4">
        <div className="flex flex-col items-center gap-3 text-center md:flex-row md:justify-between md:text-left">
          <div className="flex items-center gap-2 text-xs text-gray-400">
            <AlertTriangle className="h-4 w-4 text-yellow-500" />
            <span>
              <strong className="text-gray-300">Educational Project Only</strong> – Not for live trading
            </span>
          </div>

          <div className="text-xs text-gray-500">
            Data from yfinance | No guarantee of accuracy | Not financial advice
          </div>

          <div className="text-xs text-gray-500">
            © {new Date().getFullYear()} statarb | Non-commercial use only
          </div>
        </div>
      </div>
    </footer>
  );
}
