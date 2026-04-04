import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { authApi } from "@/api/auth";
import { useAuth } from "@/hooks/useAuth";
import { isClassSelection, isJoinClassRequired } from "@/types/auth";
import type { ClassOption } from "@/types/auth";
import { Loader2, ArrowLeft } from "lucide-react";
import { AuthLayout } from "@/components/layouts/AuthLayout";

function getRedirectPath(role: string): string {
  if (role === "super_admin") return "/super-admin/teachers";
  if (role === "admin") return "/admin/dashboard";
  return "/student/tasks";
}

export default function LoginPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const auth = useAuth();

  // Class selection state
  const [classOptions, setClassOptions] = useState<ClassOption[] | null>(null);

  // Only redirect if we have a valid session (role must exist)
  if (auth.isAuthenticated && auth.role && !classOptions) {
    return <Navigate to={getRedirectPath(auth.role)} replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await authApi.login({ username, password });

      if (isJoinClassRequired(res)) {
        // Login with no class — student can join a class from the student dashboard
        const tempPayload = JSON.parse(atob(res.temp_access_token.split(".")[1]));
        auth.login(
          res.temp_access_token,
          res.temp_refresh_token,
          "student",
          tempPayload.sub,
        );
        navigate("/student/tasks", { replace: true });
        return;
      }

      if (isClassSelection(res)) {
        // Store temp tokens for Bearer auth on select-class
        const tempPayload = JSON.parse(atob(res.temp_access_token.split(".")[1]));
        auth.login(
          res.temp_access_token,
          res.temp_refresh_token,
          "student",
          tempPayload.sub,
        );
        setClassOptions(res.classes);
        return;
      }

      const payload = JSON.parse(atob(res.access_token.split(".")[1]));
      auth.login(
        res.access_token,
        res.refresh_token,
        res.role,
        payload.sub,
        res.class_id ?? undefined,
        res.class_name ?? undefined,
      );
      navigate(getRedirectPath(res.role), { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setLoading(false);
    }
  }

  async function handleSelectClass(option: ClassOption) {
    setError("");
    setLoading(true);

    try {
      const res = await authApi.selectClass({
        class_id: option.class_id,
      });

      const payload = JSON.parse(atob(res.access_token.split(".")[1]));
      auth.login(
        res.access_token,
        res.refresh_token,
        res.role,
        payload.sub,
        res.class_id ?? undefined,
        res.class_name ?? undefined,
      );
      navigate(getRedirectPath(res.role), { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "登录失败");
    } finally {
      setLoading(false);
    }
  }

  // Class selection step
  if (classOptions) {
    return (
      <AuthLayout>
        <div className="auth-card">
          <div className="auth-card-header">
            <h2 className="auth-card-title">选择班级</h2>
            <p className="mt-2 text-sm text-[var(--muted-foreground)]">
              你在多个班级中注册，请选择要登录的班级
            </p>
          </div>

          <div className="space-y-3">
            {classOptions.map((opt) => (
              <button
                key={opt.class_id}
                type="button"
                className="w-full text-left px-4 py-3 rounded-lg border border-[var(--paper-border)] bg-white hover:border-[var(--gold)] hover:shadow-[var(--shadow-md)] transition-all duration-200 disabled:opacity-50"
                disabled={loading}
                onClick={() => handleSelectClass(opt)}
              >
                <div className="font-medium text-sm">{opt.class_name}</div>
                <div className="text-xs text-[var(--muted-foreground)] mt-0.5">
                  {opt.admin_name}
                </div>
              </button>
            ))}

            {error && (
              <p className="text-sm text-[var(--danger)]">{error}</p>
            )}

            <button
              type="button"
              className="w-full flex items-center justify-center gap-2 py-2.5 text-sm text-[var(--muted-foreground)] hover:text-[var(--foreground)] transition-colors"
              onClick={() => {
                setClassOptions(null);
                setError("");
              }}
            >
              <ArrowLeft className="h-4 w-4" />
              返回
            </button>
          </div>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout>
      <div className="auth-card">
        <div className="auth-card-header">
          <h2 className="auth-card-title">登录</h2>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-1.5">
            <label
              htmlFor="username"
              className="auth-label"
            >
              账号
            </label>
            <input
              id="username"
              type="text"
              placeholder="请输入学号或教师账号"
              className="auth-input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <label
              htmlFor="password"
              className="auth-label"
            >
              密码
            </label>
            <input
              id="password"
              type="password"
              placeholder="请输入密码"
              className="auth-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          {error && (
            <p className="text-sm text-[var(--danger)]">{error}</p>
          )}

          <button
            type="submit"
            className="auth-btn-primary"
            disabled={loading || !username || !password}
          >
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            登录
          </button>
        </form>

        <div className="mt-5 space-y-2 text-center">
          <p className="text-[13px] text-[var(--muted-foreground)]">
            忘记密码？请联系您的任课老师重置密码
          </p>
          <p className="text-[13px] text-[var(--muted-foreground)]">
            还没有账号？{" "}
            <Link
              to="/register"
              className="text-[var(--cyan-mid)] hover:text-[var(--cyan-light)] hover:underline transition-colors"
            >
              注册
            </Link>
          </p>
        </div>
      </div>
    </AuthLayout>
  );
}
