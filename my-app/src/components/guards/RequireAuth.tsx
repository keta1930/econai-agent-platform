import { Navigate } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import type { ReactNode } from "react";

interface RequireAuthProps {
  role: "super_admin" | "admin" | "student";
  children: ReactNode;
}

function getRedirectPath(role: string | null): string {
  if (role === "super_admin") return "/super-admin/admins";
  if (role === "admin") return "/admin/dashboard";
  return "/student/tasks";
}

export function RequireAuth({ role, children }: RequireAuthProps) {
  const { isAuthenticated, role: userRole } = useAuth();

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (userRole !== role) {
    return <Navigate to={getRedirectPath(userRole)} replace />;
  }

  return <>{children}</>;
}
