import { Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import type { ReactNode } from "react";

interface RequireAuthProps {
  role: "admin" | "student";
  children: ReactNode;
}

export function RequireAuth({ role, children }: RequireAuthProps) {
  const { isAuthenticated, role: userRole } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (userRole !== role) {
    const redirectTo = userRole === "admin" ? "/admin/dashboard" : "/student/tasks";
    return <Navigate to={redirectTo} replace />;
  }

  return <>{children}</>;
}
