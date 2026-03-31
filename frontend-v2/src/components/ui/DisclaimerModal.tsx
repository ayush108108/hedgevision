import React, { useEffect, useState } from "react";
import { AlertTriangle } from "lucide-react";

interface DisclaimerModalProps {
  onAccept: () => void;
}

export function DisclaimerModal({ onAccept }: DisclaimerModalProps) {
  const [show, setShow] = useState(false);

  useEffect(() => {
    // Check if user has already accepted disclaimer.
    // In some browser/privacy contexts localStorage can throw; avoid blank UI by falling back.
    try {
      const hasAccepted = localStorage.getItem("disclaimer-accepted");
      if (!hasAccepted) {
        setShow(true);
      } else {
        onAccept();
      }
    } catch {
      setShow(true);
    }
  }, [onAccept]);

  const handleAccept = () => {
    try {
      localStorage.setItem("disclaimer-accepted", "true");
    } catch {
      // Ignore storage persistence errors; continue to app.
    }
    setShow(false);
    onAccept();
  };

  if (!show) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
      <div className="mx-4 max-w-2xl rounded-xl border border-yellow-500/20 bg-gray-900 p-8 shadow-2xl">
        <div className="mb-6 flex items-center gap-3">
          <AlertTriangle className="h-8 w-8 text-yellow-500" />
          <h2 className="text-2xl font-bold text-white">Important Disclaimer</h2>
        </div>

        <div className="mb-6 space-y-4 text-gray-300">
          <p className="text-base leading-relaxed">
            This is a <strong className="text-white">non-commercial project</strong> for{" "}
            <strong className="text-white">educational and portfolio purposes only</strong>.
          </p>

          <div className="rounded-lg border border-yellow-500/20 bg-yellow-500/5 p-4">
            <p className="mb-2 font-semibold text-yellow-400">Data Accuracy Notice:</p>
            <p className="text-sm leading-relaxed">
              All financial data is sourced from <strong>yfinance</strong> and is{" "}
              <strong>not guaranteed to be accurate, complete, or real-time</strong>. Historical
              data may contain errors, gaps, or be subject to revision.
            </p>
          </div>

          <div className="rounded-lg border border-red-500/20 bg-red-500/5 p-4">
            <p className="mb-2 font-semibold text-red-400">Not Financial Advice:</p>
            <p className="text-sm leading-relaxed">
              The analytics and tools on this site <strong>do not constitute financial advice</strong>{" "}
              and should <strong>not be used for live trading or investment decisions</strong>.
              Always consult with qualified financial professionals before making investment decisions.
            </p>
          </div>

          <p className="text-sm text-gray-400">
            No redistribution of data or analytics from this site is permitted without explicit permission.
          </p>
        </div>

        <div className="flex justify-end">
          <button
            onClick={handleAccept}
            className="rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 focus:ring-offset-gray-900"
          >
            I Understand and Accept
          </button>
        </div>
      </div>
    </div>
  );
}
