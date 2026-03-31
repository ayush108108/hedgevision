import React from "react";
import { NavLink } from "react-router-dom";
import { TrendingUp, Grid3x3, GitCompare, Zap, BookOpen, ChevronDown, type LucideIcon } from "lucide-react";
import { features } from "../config/features";

type NavItem = { path: string; label: string; icon: LucideIcon };

const primaryNav: NavItem[] = [
  { path: "/cointegration", label: "Screener", icon: TrendingUp },
  { path: "/correlation", label: "Correlation", icon: Grid3x3 },
  { path: "/pair-analysis", label: "Analysis", icon: GitCompare },
  { path: "/signals", label: "Signals", icon: Zap },
  { path: "/learn", label: "Learn", icon: BookOpen },
];

// Only show "More" items when features are enabled
const moreNav: NavItem[] = [
  ...(features.portfolio ? [{ path: "/portfolio", label: "Portfolio", icon: Grid3x3 }] : []),
  ...(features.news ? [{ path: "/news", label: "News", icon: Grid3x3 }] : []),
  ...(features.calculator ? [{ path: "/calculator", label: "Calculator", icon: Grid3x3 }] : []),
  ...(features.watchlist ? [{ path: "/watchlist", label: "Watchlist", icon: Grid3x3 }] : []),
  ...(features.backtest ? [{ path: "/backtest", label: "Backtest", icon: Grid3x3 }] : []),
  ...(features.onboarding ? [{ path: "/onboarding", label: "Onboarding", icon: Grid3x3 }] : []),
];

interface NavigationProps {
  /** Pass true when rendered inside the mobile drawer */
  mobile?: boolean;
  /** Called after user taps a link so the drawer can close */
  onNavigate?: () => void;
}

export function Navigation({ mobile = false, onNavigate }: NavigationProps) {
  const [open, setOpen] = React.useState(false);

  const linkClass = (isActive: boolean) =>
    mobile
      ? `flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
          isActive
            ? "bg-blue-500/20 text-blue-300 border border-blue-500/30"
            : "text-gray-400 active:text-white active:bg-white/10 border border-transparent"
        }`
      : `group relative px-3 py-2 rounded-lg transition-all duration-200 flex items-center gap-2 text-sm ${
          isActive
            ? "bg-blue-500/20 text-blue-300 border border-blue-500/30"
            : "text-gray-400 hover:text-white hover:bg-white/5 border border-transparent"
        }`;

  return (
    <nav className={mobile ? "flex flex-col gap-1" : "flex items-center gap-1"}>
      {primaryNav.map((item) => (
        <NavLink
          key={item.path}
          to={item.path}
          className={({ isActive }) => linkClass(isActive)}
          onClick={onNavigate}
        >
          {({ isActive }) => (
            <>
              <item.icon
                size={mobile ? 17 : 16}
                className={isActive ? "text-blue-400" : "text-gray-500 group-hover:text-gray-300"}
              />
              <span>{item.label}</span>
            </>
          )}
        </NavLink>
      ))}

      {/* More dropdown — only shown when optional features are enabled */}
      {moreNav.length > 0 && (
        mobile ? (
          <>
            <div className="pt-2 pb-1 px-4 text-xs text-gray-500 uppercase tracking-wider">More</div>
            {moreNav.map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) => linkClass(isActive)}
                onClick={onNavigate}
              >
                {({ isActive }) => (
                  <>
                    <item.icon size={17} className={isActive ? "text-blue-400" : "text-gray-500"} />
                    <span>{item.label}</span>
                  </>
                )}
              </NavLink>
            ))}
          </>
        ) : (
          <div className="relative">
            <button
              onClick={() => setOpen((v) => !v)}
              className={`px-3 py-2 rounded-lg flex items-center gap-1.5 text-sm ${
                open
                  ? "bg-white/10 text-white border border-white/20"
                  : "text-gray-400 hover:text-white hover:bg-white/5 border border-transparent"
              }`}
            >
              More
              <ChevronDown size={14} className="opacity-80" />
            </button>
            {open && (
              <div className="absolute z-50 mt-2 min-w-[200px] rounded-xl border border-white/10 bg-neutral-900/98 backdrop-blur shadow-xl p-1.5">
                {moreNav.map((item) => (
                  <NavLink
                    key={item.path}
                    to={item.path}
                    className={({ isActive }) =>
                      `flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm ${
                        isActive
                          ? "bg-blue-500/20 text-blue-300"
                          : "text-gray-300 hover:bg-white/5 hover:text-white"
                      }`
                    }
                    onClick={() => { setOpen(false); onNavigate?.(); }}
                  >
                    {({ isActive }) => (
                      <>
                        <item.icon size={15} className={isActive ? "text-blue-400" : "opacity-70"} />
                        <span>{item.label}</span>
                      </>
                    )}
                  </NavLink>
                ))}
              </div>
            )}
          </div>
        )
      )}
    </nav>
  );
}
