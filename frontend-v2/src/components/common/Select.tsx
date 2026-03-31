import React, { useEffect, useLayoutEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

export interface Option {
  label: string;
  value: string;
}

interface SelectProps {
  value: string;
  onChange: (value: string) => void;
  options: Option[];
  placeholder?: string;
  disabled?: boolean;
  className?: string;
}

export function Select({
  value,
  onChange,
  options,
  placeholder = "Select",
  disabled = false,
  className = "",
}: SelectProps) {
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const [menuPos, setMenuPos] = useState<{top:number; left:number; width:number}>({top:0,left:0,width:0});
  const menuRef = useRef<HTMLUListElement>(null);

  // Position menu in a portal to avoid clipping under charts/containers
  useLayoutEffect(() => {
    if (!open || !containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    setMenuPos({ top: rect.bottom + 6, left: rect.left, width: rect.width });

    const onResize = () => {
      const r = containerRef.current?.getBoundingClientRect();
      if (!r) return;
      setMenuPos({ top: r.bottom + 6, left: r.left, width: r.width });
    };
    window.addEventListener("resize", onResize);
    window.addEventListener("scroll", onResize, true);
    return () => {
      window.removeEventListener("resize", onResize);
      window.removeEventListener("scroll", onResize, true);
    };
  }, [open]);

  // Apply computed style via DOM API to avoid JSX inline style lint errors
  useLayoutEffect(() => {
    if (!open || !menuRef.current) return;
    const el = menuRef.current;
    el.style.position = "fixed";
    el.style.top = `${menuPos.top}px`;
    el.style.left = `${menuPos.left}px`;
    el.style.width = `${menuPos.width}px`;
  }, [open, menuPos]);

  useEffect(() => {
    const onDocClick = (e: MouseEvent) => {
      if (!containerRef.current || !menuRef.current) return;
      // Don't close if clicking inside the menu portal
      if (menuRef.current.contains(e.target as Node)) return;
      // Close if clicking outside the container
      if (!containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onDocClick);
    return () => document.removeEventListener("mousedown", onDocClick);
  }, [open]);

  // Keyboard accessibility: close on Escape
  useEffect(() => {
    if (!open) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        setOpen(false);
      }
    };
    document.addEventListener("keydown", onKeyDown);
    return () => document.removeEventListener("keydown", onKeyDown);
  }, [open]);

  const selected = options.find((o) => o.value === value);

  return (
    <div ref={containerRef} className={`relative z-[60] ${className}`}>
      <button
        type="button"
        onClick={() => !disabled && setOpen((o) => !o)}
        disabled={disabled}
        className={`w-full px-4 py-2.5 rounded-lg border text-left flex items-center justify-between
          ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
          bg-white/5 border-gray-700 text-white hover:bg-white/10`}
  aria-haspopup="listbox"
      >
        <span className="truncate">{selected?.label || placeholder}</span>
        <svg
          width="18"
          height="18"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={open ? "rotate-180" : "rotate-0"}
        >
          <path d="M7 10l5 5 5-5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
        </svg>
      </button>

      {open && createPortal(
        <ul
          ref={menuRef}
          role="listbox"
          aria-label="Select options"
          className="z-[9999] max-h-64 overflow-auto rounded-lg border border-gray-700 bg-slate-900 shadow-2xl"
        >
          {options.map((opt) => (
            <li
              key={opt.value}
              role="option"
              className={`cursor-pointer px-4 py-2 hover:bg-white/10 ${
                opt.value === value ? "text-blue-400 bg-blue-500/10" : "text-white"
              }`}
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                onChange(opt.value);
                setOpen(false);
              }}
            >
              {opt.label}
            </li>
          ))}
        </ul>,
        document.body
      )}
    </div>
  );
}
