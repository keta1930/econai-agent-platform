import { useState, type FormEvent } from "react";
import { Link, Navigate, useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { authApi } from "@/api/auth";
import { useAuth } from "@/hooks/useAuth";
import { isClassSelection } from "@/types/auth";
import type { ClassOption } from "@/types/auth";
import { Loader2, ArrowLeft } from "lucide-react";
import { AuthLayout } from "@/components/layouts/AuthLayout";

function getRedirectPath(role: string): string {
  if (role === "super_admin") return "/super-admin/admins";
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

  if (auth.isAuthenticated) {
    return <Navigate to={getRedirectPath(auth.role!)} replace />;
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      const res = await authApi.login({ username, password });

      if (isClassSelection(res)) {
        setClassOptions(res.classes);
        return;
      }

      const payload = JSON.parse(atob(res.access_token.split(".")[1]));
      auth.login(
        res.access_token,
        res.role,
        Number(payload.sub),
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
        username,
        password,
        class_id: option.class_id,
      });

      const payload = JSON.parse(atob(res.access_token.split(".")[1]));
      auth.login(
        res.access_token,
        res.role,
        Number(payload.sub),
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
        <Card className="w-full max-w-[400px]">
          <CardHeader className="text-center">
            <CardTitle className="text-2xl font-semibold">选择班级</CardTitle>
            <p className="text-sm text-muted-foreground mt-1">
              你在多个班级中注册，请选择要登录的班级
            </p>
          </CardHeader>
          <CardContent className="space-y-3">
            {classOptions.map((opt) => (
              <Button
                key={opt.class_id}
                variant="outline"
                className="w-full justify-start h-auto py-3"
                disabled={loading}
                onClick={() => handleSelectClass(opt)}
              >
                <div className="text-left">
                  <div className="font-medium">{opt.class_name}</div>
                  <div className="text-xs text-muted-foreground">{opt.admin_name}</div>
                </div>
              </Button>
            ))}
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
            <Button
              variant="ghost"
              className="w-full"
              onClick={() => {
                setClassOptions(null);
                setError("");
              }}
            >
              <ArrowLeft className="mr-2 h-4 w-4" />
              返回
            </Button>
          </CardContent>
        </Card>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout>
      <Card className="w-full max-w-[400px]">
        <CardHeader className="text-center">
          <CardTitle className="text-2xl font-semibold">登录</CardTitle>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="username">账号</Label>
              <Input
                id="username"
                type="text"
                placeholder="请输入学号或管理员账号"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">密码</Label>
              <Input
                id="password"
                type="password"
                placeholder="请输入密码"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
            {error && (
              <p className="text-sm text-destructive">{error}</p>
            )}
            <Button type="submit" className="w-full" disabled={loading || !username || !password}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              登录
            </Button>
          </form>
          <p className="mt-4 text-center text-sm text-muted-foreground">
            还没有账号？{" "}
            <Link to="/register" className="text-primary hover:underline">
              注册
            </Link>
          </p>
        </CardContent>
      </Card>
    </AuthLayout>
  );
}
