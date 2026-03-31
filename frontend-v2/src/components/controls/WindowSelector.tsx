import React from "react";
import { Calendar } from "lucide-react";

export const WINDOW_OPTIONS = [
  { value: 30, label: "30 days", description: "1 month" },
  { value: 60, label: "60 days", description: "2 months" },
  { value: 90, label: "90 days", description: "3 months" },
  { value: 180, label: "180 days", description: "6 months" },
  { value: 252, label: "252 days", description: "1 year" },
] as const;

interface WindowSelectorProps {
  selected: number;
  onSelect: (window: number) => void;
}

export function WindowSelector({ selected, onSelect }: WindowSelectorProps) {
  return (
    <div className="bg-gray-800/50 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <Calendar className="w-4 h-4 text-gray-400" />
        <h3 className="text-sm font-medium text-gray-300">Rolling Window</h3>
      </div>
      
      <div className="flex flex-wrap gap-2">
        {WINDOW_OPTIONS.map((option) => (
          <button
            key={option.value}
            onClick={() => onSelect(option.value)}
            className={`
              px-4 py-2 rounded-lg text-sm font-medium
              transition-all duration-200
              ${
                selected === option.value
                  ? "bg-blue-600 text-white shadow-lg shadow-blue-600/30"
                  : "bg-gray-700/50 text-gray-300 hover:bg-gray-700 hover:text-white"
              }
            `}
          >
            <div className="flex flex-col items-center gap-1">
              <span>{option.label}</span>
              <span className="text-xs opacity-70">{option.description}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  );
}

export function getWindowLabel(window: number): string {
  const option = WINDOW_OPTIONS.find((opt) => opt.value === window);
  return option ? option.label : `${window} days`;
}
