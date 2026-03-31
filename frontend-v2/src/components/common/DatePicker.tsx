import React, { useRef, useState, useEffect } from "react";
import { Calendar } from "lucide-react";

interface DatePickerProps {
  value: string;
  onChange: (value: string) => void;
  label?: string;
  className?: string;
}

export function DatePicker({ value, onChange, label, className = "" }: DatePickerProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [focused, setFocused] = useState(false);

  return (
    <div className={`relative ${className}`}>
      {label && (
        <label className="block text-sm font-medium text-gray-300 mb-2">
          {label}
        </label>
      )}
      <div className="relative">
        <input
          ref={inputRef}
          type="date"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
          className={`
            w-full px-4 py-2.5 pr-10
            bg-gray-800/50 border border-gray-700
            rounded-lg text-white
            placeholder-gray-500
            transition-all duration-200
            focus:ring-2 focus:ring-blue-500 focus:border-blue-500
            hover:border-gray-600
            ${focused ? 'ring-2 ring-blue-500 border-blue-500' : ''}
          `}
          style={{
            colorScheme: 'dark',
          }}
        />
        <div className="absolute inset-y-0 right-0 flex items-center pr-3 pointer-events-none">
          <Calendar className="w-4 h-4 text-gray-400" />
        </div>
      </div>
    </div>
  );
}
