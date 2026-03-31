import axios from "axios";
import { config } from "../config/env";

const API_URL = config.apiUrl;

export interface AuthUser {
  id: string;
  email: string;
  name?: string;
  created_at?: string;
}

export interface AuthResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface RegisterData {
  email: string;
  password: string;
  name?: string;
}

/**
 * Login user and get auth tokens
 */
export async function login(
  credentials: LoginCredentials,
): Promise<AuthResponse> {
  const response = await axios.post<AuthResponse>(
    `${API_URL}/auth/login`,
    credentials,
  );
  return response.data;
}

/**
 * Register new user
 */
export async function register(data: RegisterData): Promise<AuthResponse> {
  const response = await axios.post<AuthResponse>(
    `${API_URL}/auth/register`,
    data,
  );
  return response.data;
}

/**
 * Refresh access token using refresh token
 */
export async function refreshToken(
  refreshToken: string,
): Promise<AuthResponse> {
  const response = await axios.post<AuthResponse>(
    `${API_URL}/auth/refresh`,
    { refresh_token: refreshToken },
  );
  return response.data;
}

/**
 * Get current user profile
 */
export async function getCurrentUser(token: string): Promise<AuthUser> {
  const response = await axios.get<AuthUser>(`${API_URL}/auth/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });
  return response.data;
}

/**
 * Logout user (invalidate token on backend)
 */
export async function logout(token: string): Promise<void> {
  await axios.post(
    `${API_URL}/auth/logout`,
    {},
    {
      headers: {
        Authorization: `Bearer ${token}`,
      },
    },
  );
}

/**
 * Storage keys
 */
const LEGACY_TOKEN_KEY = "statarb_access_token";
const LEGACY_REFRESH_TOKEN_KEY = "statarb_refresh_token";
const LEGACY_USER_KEY = "statarb_user";

const TOKEN_BASE_KEY = import.meta.env.VITE_JWT_STORAGE_KEY || "hedgevision_token";
export const TOKEN_KEY = `${TOKEN_BASE_KEY}_access`;
export const REFRESH_TOKEN_KEY =
  import.meta.env.VITE_REFRESH_TOKEN_KEY || `${TOKEN_BASE_KEY}_refresh`;
export const USER_KEY = `${TOKEN_BASE_KEY}_user`;

/**
 * Get stored token
 */
export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY) || localStorage.getItem(LEGACY_TOKEN_KEY);
}

/**
 * Get stored refresh token
 */
export function getStoredRefreshToken(): string | null {
  return (
    localStorage.getItem(REFRESH_TOKEN_KEY) ||
    localStorage.getItem(LEGACY_REFRESH_TOKEN_KEY)
  );
}

/**
 * Get stored user
 */
export function getStoredUser(): AuthUser | null {
  const userStr = localStorage.getItem(USER_KEY) || localStorage.getItem(LEGACY_USER_KEY);
  if (!userStr) return null;
  try {
    return JSON.parse(userStr);
  } catch {
    return null;
  }
}

/**
 * Store auth data
 */
export function storeAuthData(authResponse: AuthResponse): void {
  localStorage.setItem(TOKEN_KEY, authResponse.access_token);
  localStorage.setItem(REFRESH_TOKEN_KEY, authResponse.refresh_token);
  localStorage.setItem(USER_KEY, JSON.stringify(authResponse.user));
  // Clean up old storage keys once migrated.
  localStorage.removeItem(LEGACY_TOKEN_KEY);
  localStorage.removeItem(LEGACY_REFRESH_TOKEN_KEY);
  localStorage.removeItem(LEGACY_USER_KEY);
}

/**
 * Clear auth data
 */
export function clearAuthData(): void {
  localStorage.removeItem(TOKEN_KEY);
  localStorage.removeItem(REFRESH_TOKEN_KEY);
  localStorage.removeItem(USER_KEY);
  localStorage.removeItem(LEGACY_TOKEN_KEY);
  localStorage.removeItem(LEGACY_REFRESH_TOKEN_KEY);
  localStorage.removeItem(LEGACY_USER_KEY);
}
