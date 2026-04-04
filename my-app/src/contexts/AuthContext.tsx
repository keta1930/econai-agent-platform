import { createContext, useState, useCallback, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";

type Role = "super_admin" | "admin" | "student";

interface AuthState {
  token: string | null;
  role: Role | null;
  userId: string | null;
  classId: string | null;
  className: string | null;
  isAuthenticated: boolean;
}

export interface AuthContextValue extends AuthState {
  login: (token: string, refreshToken: string, role: string, userId: string, classId?: string, className?: string) => void;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

function getInitialState(): AuthState {
  const token = localStorage.getItem("token");
  const refreshToken = localStorage.getItem("refreshToken");

  if (!token && !refreshToken) {
    return { token: null, role: null, userId: null, classId: null, className: null, isAuthenticated: false };
  }

  // If we have a refresh token, we consider the user authenticated
  // even if the access token is expired — the client interceptor will refresh it
  if (refreshToken) {
    const role = localStorage.getItem("role") as Role | null;
    const userId = localStorage.getItem("userId");
    const classId = localStorage.getItem("classId");
    const className = localStorage.getItem("className");
    return { token, role, userId, classId, className, isAuthenticated: true };
  }

  // No refresh token — clear everything
  localStorage.removeItem("token");
  localStorage.removeItem("role");
  localStorage.removeItem("userId");
  localStorage.removeItem("classId");
  localStorage.removeItem("className");
  return { token: null, role: null, userId: null, classId: null, className: null, isAuthenticated: false };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(getInitialState);
  const navigate = useNavigate();

  const login = useCallback(
    (token: string, refreshToken: string, role: string, userId: string, classId?: string, className?: string) => {
      localStorage.setItem("token", token);
      localStorage.setItem("refreshToken", refreshToken);
      localStorage.setItem("role", role);
      localStorage.setItem("userId", String(userId));
      if (classId !== undefined) {
        localStorage.setItem("classId", String(classId));
      } else {
        localStorage.removeItem("classId");
      }
      if (className !== undefined) {
        localStorage.setItem("className", className);
      } else {
        localStorage.removeItem("className");
      }
      setState({
        token,
        role: role as Role,
        userId,
        classId: classId ?? null,
        className: className ?? null,
        isAuthenticated: true,
      });
    },
    [],
  );

  const logout = useCallback(() => {
    // Best-effort server-side logout — don't block on failure
    const refreshToken = localStorage.getItem("refreshToken");
    if (refreshToken) {
      fetch("/api/auth/logout", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      }).catch(() => {});
    }

    localStorage.removeItem("token");
    localStorage.removeItem("refreshToken");
    localStorage.removeItem("role");
    localStorage.removeItem("userId");
    localStorage.removeItem("classId");
    localStorage.removeItem("className");
    localStorage.removeItem("currentClassId");
    setState({ token: null, role: null, userId: null, classId: null, className: null, isAuthenticated: false });
    navigate("/login");
  }, [navigate]);

  return (
    <AuthContext value={{ ...state, login, logout }}>
      {children}
    </AuthContext>
  );
}
