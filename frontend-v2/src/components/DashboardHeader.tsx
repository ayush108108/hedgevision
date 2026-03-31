"use client";

import { useState } from "react";
import { Menu, X, Github, ExternalLink } from "lucide-react";
import { useNavigate } from "react-router-dom";
import { Navigation } from "./Navigation";

export function DashboardHeader() {
  const navigate = useNavigate();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 h-16">
      {/* Glassmorphism background */}
      <div className="absolute inset-0 bg-[#0a0e27]/90 backdrop-blur-xl border-b border-white/10" />

      <div className="relative h-full px-3 sm:px-6 md:px-8 flex items-center justify-between gap-2">
        {/* Logo */}
        <div
          className="flex items-center gap-2 cursor-pointer shrink-0"
          onClick={() => { navigate("/"); setIsMobileMenuOpen(false); }}
        >
          <div className="w-8 h-8 sm:w-9 sm:h-9 rounded-xl bg-gradient-to-br from-blue-500 to-cyan-500 flex items-center justify-center shadow-lg shadow-blue-500/30">
            <span className="text-white font-bold text-sm sm:text-base">H</span>
          </div>
          <div className="hidden xs:block">
            <h1 className="text-white font-semibold text-sm sm:text-base leading-tight">HedgeVision</h1>
            <p className="text-gray-400 text-[10px] sm:text-xs">Statistical Arbitrage</p>
          </div>
        </div>

        {/* Desktop Navigation — center */}
        <div className="hidden md:flex flex-1 justify-center">
          <Navigation onNavigate={() => setIsMobileMenuOpen(false)} />
        </div>

        {/* Right side */}
        <div className="flex items-center gap-2 shrink-0">
          <a
            href="https://github.com/ayush-jadaun"
            target="_blank"
            rel="noopener noreferrer"
            className="hidden sm:flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 border border-white/10 text-gray-300 hover:text-white transition-all text-xs"
          >
            <Github size={14} />
            <span>Source</span>
            <ExternalLink size={10} className="opacity-60" />
          </a>

          {/* Mobile Menu Toggle */}
          <button
            onClick={() => setIsMobileMenuOpen((v) => !v)}
            className="md:hidden p-1.5 rounded-lg bg-white/5 active:bg-white/15 border border-white/10 text-white transition-colors"
            aria-label="Toggle menu"
          >
            {isMobileMenuOpen ? <X size={20} /> : <Menu size={20} />}
          </button>
        </div>
      </div>

      {/* Mobile Menu drawer */}
      {isMobileMenuOpen && (
        <div className="md:hidden absolute top-16 left-0 right-0 bg-[#0a0e27]/98 backdrop-blur-xl border-b border-white/10 shadow-xl">
          <div className="px-3 py-3">
            <Navigation mobile onNavigate={() => setIsMobileMenuOpen(false)} />
          </div>
        </div>
      )}
    </header>
  );
}
