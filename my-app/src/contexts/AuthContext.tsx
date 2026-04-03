import { createContext, useState, useCallback, useEffect, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";

type Role = "super_admin" | "admin" | "student";

interface AuthState {
  token: string | null;
  role: Role | null;
  userId: number | null;
  classId: number | null;
  className: string | null;
  isAuthenticated: boolean;
}

export interface AuthContextValue extends AuthState {
  login: (token: string, role: string, userId: number, classId?: number, className?: string) => void;
  logout: () => void;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

function parseToken(token: string): { sub: number; role: string; class_id: number | null; exp: number } | null {
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
    return { token: null, role: null, userId: null, classId: null, className: null, isAuthenticated: false };
  }

  const payload = parseToken(token);
  if (!payload || payload.exp * 1000 < Date.now()) {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    localStorage.removeItem("userId");
    localStorage.removeItem("classId");
    localStorage.removeItem("className");
    return { token: null, role: null, userId: null, classId: null, className: null, isAuthenticated: false };
  }

  const role = localStorage.getItem("role") as Role | null;
  const userIdStr = localStorage.getItem("userId");
  const userId = userIdStr ? Number(userIdStr) : null;
  const classIdStr = localStorage.getItem("classId");
  const classId = classIdStr ? Number(classIdStr) : null;
  const className = localStorage.getItem("className");
  return { token, role, userId, classId, className, isAuthenticated: true };
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(getInitialState);
  const navigate = useNavigate();

  const login = useCallback(
    (token: string, role: string, userId: number, classId?: number, className?: string) => {
      localStorage.setItem("token", token);
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
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    localStorage.removeItem("userId");
    localStorage.removeItem("classId");
    localStorage.removeItem("className");
    localStorage.removeItem("currentClassId");
    setState({ token: null, role: null, userId: null, classId: null, className: null, isAuthenticated: false });
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
