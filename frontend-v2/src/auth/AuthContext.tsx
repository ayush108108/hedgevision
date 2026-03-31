import React, {
  createContext,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import * as authService from "../services/auth";
import type {
  AuthUser as ServiceAuthUser,
  LoginCredentials,
  RegisterData,
} from "../services/auth";

// Re-export AuthUser for convenience
export type AuthUser = ServiceAuthUser;

interface AuthContextValue {
  isAuthenticated: boolean;
  user: AuthUser | null;
  isLoading: boolean;
  login: (credentials: LoginCredentials) => Promise<void>;
  register: (data: RegisterData) => Promise<void>;
  logout: () => Promise<void>;
  // Legacy methods for backward compatibility
  signIn: () => Promise<void>;
  signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Check for existing auth session on mount
  useEffect(() => {
    const initAuth = async () => {
      const token = authService.getStoredToken();
      const storedUser = authService.getStoredUser();

      if (token && storedUser) {
        // Verify token is still valid by fetching current user
        try {
          const currentUser = await authService.getCurrentUser(token);
          setUser(currentUser);
          setIsAuthenticated(true);
        } catch (error) {
          // Token is invalid, clear storage
          console.error("Token validation failed:", error);
          authService.clearAuthData();
          setUser(null);
          setIsAuthenticated(false);
        }
      }

      setIsLoading(false);
    };

    initAuth();
  }, []);

  const login = async (credentials: LoginCredentials) => {
    try {
      const authResponse = await authService.login(credentials);
      authService.storeAuthData(authResponse);
      setUser(authResponse.user);
      setIsAuthenticated(true);
    } catch (error) {
      console.error("Login failed:", error);
      throw error;
    }
  };

  const register = async (data: RegisterData) => {
    try {
      const authResponse = await authService.register(data);
      authService.storeAuthData(authResponse);
      setUser(authResponse.user);
      setIsAuthenticated(true);
    } catch (error) {
      console.error("Registration failed:", error);
      throw error;
    }
  };

  const logout = async () => {
    const token = authService.getStoredToken();

    try {
      if (token) {
        await authService.logout(token);
      }
    } catch (error) {
      console.error("Logout request failed:", error);
      // Continue with local logout even if API call fails
    } finally {
      authService.clearAuthData();
      setUser(null);
      setIsAuthenticated(false);
    }
  };

  // Legacy methods for backward compatibility
  const signIn = async () => {
    // This is a placeholder - direct use of login() is preferred
    console.warn("signIn() is deprecated, use login() instead");
  };

  const signOut = async () => {
    await logout();
  };

  const value = useMemo<AuthContextValue>(
    () => ({
      isAuthenticated,
      user,
      isLoading,
      login,
      register,
      logout,
      signIn,
      signOut,
    }),
    [isAuthenticated, user, isLoading],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within an AuthProvider");
  return ctx;
}
