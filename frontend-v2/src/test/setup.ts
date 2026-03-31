import { expect, afterEach, vi } from "vitest";
import { cleanup } from "@testing-library/react";
import "@testing-library/jest-dom/vitest";

// Cleanup after each test
afterEach(() => {
  cleanup();
});

// Mock window.matchMedia
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {}, // deprecated
    removeListener: () => {}, // deprecated
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
});

// Mock ResizeObserver
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Global mock for echarts to avoid zrender/canvas usage in JSDOM
if (!(global as any).__ECHARTS_MOCKED__) {
  vi.mock("echarts", () => {
    const connect = vi.fn();
    const init = vi.fn(() => ({
      setOption: vi.fn(),
      dispose: vi.fn(),
      resize: vi.fn(),
      getZr: vi.fn(() => ({ on: vi.fn(), off: vi.fn() })),
    }));
    const graphic = { LinearGradient: vi.fn() };
    return { __esModule: true, connect, init, graphic };
  });
  (global as any).__ECHARTS_MOCKED__ = true;
}
