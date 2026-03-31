import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  // For GitHub Pages: set VITE_BASE_PATH=/repo-name/ at build time.
  // For custom domain or local dev: leave unset (defaults to "/").
  base: process.env.VITE_BASE_PATH || "/",
  server: {
    port: 3000,
  },
  preview: {
    port: 5000,
  },
  build: {
    // Optimize for production
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: {
          echarts: ["echarts", "echarts-for-react"],
          vendor: ["react", "react-dom", "react-router-dom"],
          query: ["@tanstack/react-query", "axios"],
        },
      },
    },
  },
});
