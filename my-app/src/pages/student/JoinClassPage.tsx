import { useState, type FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { authApi } from "@/api/auth";
import { useAuth } from "@/hooks/useAuth";
import { Loader2 } from "lucide-react";
import { AuthLayout } from "@/components/layouts/AuthLayout";
import { toast } from "sonner";

export default function JoinClassPage() {
  const [joinToken, setJoinToken] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();
  const auth = useAuth();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!joinToken.trim()) return;
    setError("");
    setLoading(true);

    try {
      const res = await authApi.joinClass({ join_token: joinToken.trim() });

      const payload = JSON.parse(atob(res.access_token.split(".")[1]));
      auth.login(
        res.access_token,
        res.refresh_token,
        "student",
        payload.sub,
        res.class_id,
        res.class_name,
      );
      toast.success(`已加入班级「${res.class_name}」`);
      navigate("/student/tasks", { replace: true });
    } catch (err) {
      setError(err instanceof Error ? err.message : "加入失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout>
      <div className="auth-card">
        <div className="auth-card-header">
          <h2 className="auth-card-title">加入班级</h2>
          <p className="mt-2 text-sm text-[var(--muted-foreground)]">
            请输入老师提供的班级 Token 加入班级
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-1.5">
            <label htmlFor="joinToken" className="auth-label">
              班级 Token
            </label>
            <input
              id="joinToken"
              type="text"
              placeholder="请输入班级 Token"
              className="auth-input"
              value={joinToken}
              onChange={(e) => setJoinToken(e.target.value)}
              autoFocus
            />
          </div>

          {error && <p className="text-sm text-[var(--danger)]">{error}</p>}

          <button
            type="submit"
            className="auth-btn-primary"
            disabled={loading || !joinToken.trim()}
          >
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            加入班级
          </button>
        </form>
      </div>
    </AuthLayout>
  );
}
