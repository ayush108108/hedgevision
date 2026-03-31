export const config = {
  apiUrl:
    import.meta.env.VITE_API_BASE_URL ||
    import.meta.env.VITE_API_URL ||
    "", // Relative path for same-origin serving
  wsUrl: import.meta.env.VITE_WS_BASE_URL || `ws://${window.location.host}`,

  validate() {
    if (!this.apiUrl) {
      console.warn("⚠️ API URL not configured, using default localhost:8000");
    }
  },
};

config.validate();
