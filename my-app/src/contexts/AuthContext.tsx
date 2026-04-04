import { createContext, useState, useCallback, useEffect, type ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import { authApi } from "@/api/auth";

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
  switchClass: (classId: string) => Promise<void>;
}

export const AuthContext = createContext<AuthContextValue | null>(null);

function clearLocalStorage() {
  localStorage.removeItem("token");
  localStorage.removeItem("refreshToken");
  localStorage.removeItem("role");
  localStorage.removeItem("userId");
  localStorage.removeItem("classId");
  localStorage.removeItem("className");
  localStorage.removeItem("currentClassId");
}

const EMPTY_STATE: AuthState = { token: null, role: null, userId: null, classId: null, className: null, isAuthenticated: false };

function isTokenExpired(token: string): boolean {
  try {
    const payload = JSON.parse(atob(token.split(".")[1]));
    return payload.exp * 1000 < Date.now();
  } catch {
    return true;
  }
}

function getInitialState(): AuthState {
  const token = localStorage.getItem("token");
  const refreshToken = localStorage.getItem("refreshToken");
  const role = localStorage.getItem("role") as Role | null;

  // No tokens at all — not authenticated
  if (!token && !refreshToken) {
    return EMPTY_STATE;
  }

  // Must have role to be a valid session
  if (!role) {
    clearLocalStorage();
    return EMPTY_STATE;
  }

  // If access token exists and is not expired, use it
  if (token && !isTokenExpired(token)) {
    const userId = localStorage.getItem("userId");
    const classId = localStorage.getItem("classId");
    const className = localStorage.getItem("className");
    return { token, role, userId, classId, className, isAuthenticated: true };
  }

  // Access token expired or missing — don't mark as authenticated yet.
  // The useEffect will attempt refresh; if it succeeds, state updates to authenticated.
  // If it fails, localStorage gets cleared. Either way, start as not authenticated.

  // Nothing valid — clean up
  clearLocalStorage();
  return EMPTY_STATE;
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<AuthState>(getInitialState);
  const navigate = useNavigate();

  // On mount: if access token is expired but refresh token exists, try to refresh.
  // If refresh fails (e.g. database was cleared), clean up and redirect to login.
  useEffect(() => {
    const token = localStorage.getItem("token");
    const refreshToken = localStorage.getItem("refreshToken");
    if (refreshToken && (!token || isTokenExpired(token))) {
      fetch("/api/auth/refresh", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
      })
        .then((res) => {
          if (!res.ok) throw new Error("refresh failed");
          return res.json();
        })
        .then((data) => {
          localStorage.setItem("token", data.access_token);
        })
        .catch(() => {
          // Refresh failed — session is dead, clean up
          clearLocalStorage();
          setState(EMPTY_STATE);
        });
    }
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

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
    // Best-effort server-side logout -- don't block on failure
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

  const switchClass = useCallback(
    async (classId: string) => {
      const res = await authApi.switchClass({ class_id: classId });
      const payload = JSON.parse(atob(res.access_token.split(".")[1]));
      login(
        res.access_token,
        res.refresh_token,
        res.role,
        payload.sub,
        res.class_id ?? undefined,
        res.class_name ?? undefined,
      );
    },
    [login],
  );

  return (
    <AuthContext value={{ ...state, login, logout, switchClass }}>
      {children}
    </AuthContext>
  );
}
