import React, { useState, useRef, useEffect } from "react";
import { Info } from "lucide-react";

interface InfoTooltipProps {
  text: string;
  /** Optional explicit title shown in bold at the top of the tooltip */
  title?: string;
}

/**
 * Plain-English info tooltip. Works on both hover (desktop) and tap (mobile).
 * Renders a small ℹ icon that shows a tooltip panel on interaction.
 */
export function InfoTooltip({ text, title }: InfoTooltipProps) {
  const [visible, setVisible] = useState(false);
  const ref = useRef<HTMLSpanElement>(null);

  // Close on click outside (for touch devices)
  useEffect(() => {
    if (!visible) return;
    const handler = (e: MouseEvent | TouchEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setVisible(false);
      }
    };
    document.addEventListener("mousedown", handler);
    document.addEventListener("touchstart", handler);
    return () => {
      document.removeEventListener("mousedown", handler);
      document.removeEventListener("touchstart", handler);
    };
  }, [visible]);

  return (
    <span
      ref={ref}
      className="relative inline-flex items-center"
      onMouseEnter={() => setVisible(true)}
      onMouseLeave={() => setVisible(false)}
      onTouchStart={(e) => {
        e.stopPropagation();
        setVisible((v) => !v);
      }}
    >
      <Info
        size={13}
        className="ml-1 text-gray-500 hover:text-blue-400 cursor-help shrink-0"
        aria-label="More information"
      />
      {visible && (
        <span
          className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-60 text-left"
          style={{ filter: "drop-shadow(0 4px 16px rgba(0,0,0,0.5))" }}
        >
          <span className="block rounded-xl border border-white/10 bg-[#141830] p-3 text-xs leading-relaxed text-gray-300">
            {title && <span className="block font-semibold text-white mb-1">{title}</span>}
            {text}
          </span>
          {/* Arrow pointing down */}
          <span className="block mx-auto w-0 h-0" style={{
            borderLeft: "6px solid transparent",
            borderRight: "6px solid transparent",
            borderTop: "6px solid rgba(255,255,255,0.10)",
            width: 0,
            marginLeft: "50%",
            transform: "translateX(-50%)",
          }} />
        </span>
      )}
    </span>
  );
}
