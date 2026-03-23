import { createContext, useState, useCallback, useEffect, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";

interface AuthState {
  token: string | null;
  role: "admin" | "student" | null;
  userId: string | null;
  isAuthenticated: boolean;
}

export interface AuthContextValue extends AuthState {
  login: (token: string, role: string, userId: string) => void;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

function parseToken(token: string): { sub: string; role: string; exp: number } | null {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload;
  } catch {
    return null;
  }
}

function getInitialState(): AuthState {
  const token = localStorage.getItem("token");
  if (!token) {
    return { token: null, role: null, userId: null, isAuthenticated: false };
  }

  const payload = parseToken(token);
  if (!payload || payload.exp * 1000 < Date.now()) {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    localStorage.removeItem("userId");
    return { token: null, role: null, userId: null, isAuthenticated: false };
  }

  const role = localStorage.getItem("role") as "admin" | "student" | null;
  const userId = localStorage.getItem("userId");
  return { token, role, userId, isAuthenticated: true };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(getInitialState);
  const navigate = useNavigate();

  const login = useCallback(
    (token: string, role: string, userId: string) => {
      localStorage.setItem("token", token);
      localStorage.setItem("role", role);
      localStorage.setItem("userId", userId);
      setState({
        token,
        role: role as "admin" | "student",
        userId,
        isAuthenticated: true,
      });
    },
    [],
  );

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    localStorage.removeItem("userId");
    setState({ token: null, role: null, userId: null, isAuthenticated: false });
    navigate("/login");
  }, [navigate]);

  // Check token expiry periodically
  useEffect(() => {
    if (!state.token) return;

    const payload = parseToken(state.token);
    if (!payload) return;

    const msUntilExpiry = payload.exp * 1000 - Date.now();
    if (msUntilExpiry <= 0) {
      logout();
      return;
    }

    const timer = setTimeout(logout, msUntilExpiry);
    return () => clearTimeout(timer);
  }, [state.token, logout]);

  return (
    <AuthContext value={{ ...state, login, logout }}>
      {children}
    </AuthContext>
  );
}
