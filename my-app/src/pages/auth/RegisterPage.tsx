import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authApi } from "@/api/auth";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { AuthLayout } from "@/components/layouts/AuthLayout";

export default function RegisterPage() {
  const [adminName, setAdminName] = useState("");
  const [className, setClassName] = useState("");
  const [studentId, setStudentId] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const isFormValid = adminName.trim() && className.trim() && studentId.trim() && password;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await authApi.register({
        admin_name: adminName.trim(),
        class_name: className.trim(),
        student_id: studentId.trim(),
        password,
      });
      toast.success("注册成功，请登录");
      navigate("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "注册失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <AuthLayout>
      <div className="auth-card">
        <div className="auth-card-header">
          <h2 className="auth-card-title">注册</h2>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div className="space-y-1.5">
            <label htmlFor="adminName" className="auth-label">
              管理员名称
            </label>
            <input
              id="adminName"
              type="text"
              placeholder="请输入管理员名称"
              className="auth-input"
              value={adminName}
              onChange={(e) => setAdminName(e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="className" className="auth-label">
              班级名称
            </label>
            <input
              id="className"
              type="text"
              placeholder="请输入班级名称"
              className="auth-input"
              value={className}
              onChange={(e) => setClassName(e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="studentId" className="auth-label">
              学号
            </label>
            <input
              id="studentId"
              type="text"
              placeholder="请输入学号"
              className="auth-input"
              value={studentId}
              onChange={(e) => setStudentId(e.target.value)}
            />
          </div>

          <div className="space-y-1.5">
            <label htmlFor="password" className="auth-label">
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
            disabled={loading || !isFormValid}
          >
            {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            注册
          </button>
        </form>

        <p className="mt-5 text-center text-[13px] text-[var(--muted-foreground)]">
          已有账号？{" "}
          <Link
            to="/login"
            className="text-[var(--cyan-mid)] hover:text-[var(--cyan-light)] hover:underline transition-colors"
          >
            登录
          </Link>
        </p>
      </div>
    </AuthLayout>
  );
}
