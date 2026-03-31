import axios from "axios";
import { config } from "../config/env";

/**
 * Unified API client for HedgeVision.
 * Auth interceptors are stripped for the no-auth production showcase.
 * To re-enable auth, set VITE_FEATURE_AUTH=true and restore the
 * token interceptors from git history.
 */
const apiClient = axios.create({
  baseURL: config.apiUrl,
  timeout: 30000,
  headers: {
    "Content-Type": "application/json",
  },
});

export default apiClient;
