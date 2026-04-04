import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { authApi } from "@/api/auth";
import { toast } from "sonner";
import { Loader2 } from "lucide-react";
import { AuthLayout } from "@/components/layouts/AuthLayout";
import { cn } from "@/lib/utils";

type TabType = "student" | "teacher";

const COLLEGES = [
  { value: "lingnan" as const, label: "岭南学院" },
  { value: "physics" as const, label: "物理学院" },
];

function StudentForm() {
  const [studentId, setStudentId] = useState("");
  const [college, setCollege] = useState<"lingnan" | "physics" | "">("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const isFormValid = studentId.trim() && college && password;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!college) return;
    setError("");
    setLoading(true);

    try {
      await authApi.register({
        student_id: studentId.trim(),
        college,
        password,
      });
      toast.success("注册成功，请登录后加入班级");
      navigate("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "注册失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-5">
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
        <label htmlFor="college" className="auth-label">
          学院
        </label>
        <select
          id="college"
          className="auth-input"
          value={college}
          onChange={(e) => setCollege(e.target.value as "lingnan" | "physics" | "")}
        >
          <option value="" disabled>
            请选择学院
          </option>
          {COLLEGES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label}
            </option>
          ))}
        </select>
      </div>

      <div className="space-y-1.5">
        <label htmlFor="student-password" className="auth-label">
          密码
        </label>
        <input
          id="student-password"
          type="password"
          placeholder="请输入密码"
          className="auth-input"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>

      {error && <p className="text-sm text-[var(--danger)]">{error}</p>}

      <button
        type="submit"
        className="auth-btn-primary"
        disabled={loading || !isFormValid}
      >
        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        注册
      </button>
    </form>
  );
}

function TeacherForm() {
  const [inviteCode, setInviteCode] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const isFormValid = inviteCode.trim() && username.trim() && password;

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setLoading(true);

    try {
      await authApi.registerTeacher({
        invite_code: inviteCode.trim(),
        username: username.trim(),
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
    <form onSubmit={handleSubmit} className="space-y-5">
      <div className="space-y-1.5">
        <label htmlFor="inviteCode" className="auth-label">
          邀请码
        </label>
        <input
          id="inviteCode"
          type="text"
          placeholder="请输入邀请码"
          className="auth-input"
          value={inviteCode}
          onChange={(e) => setInviteCode(e.target.value)}
        />
      </div>

      <div className="space-y-1.5">
        <label htmlFor="teacher-username" className="auth-label">
          用户名
        </label>
        <input
          id="teacher-username"
          type="text"
          placeholder="请输入用户名"
          className="auth-input"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
        />
      </div>

      <div className="space-y-1.5">
        <label htmlFor="teacher-password" className="auth-label">
          密码
        </label>
        <input
          id="teacher-password"
          type="password"
          placeholder="请输入密码"
          className="auth-input"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
        />
      </div>

      {error && <p className="text-sm text-[var(--danger)]">{error}</p>}

      <button
        type="submit"
        className="auth-btn-primary"
        disabled={loading || !isFormValid}
      >
        {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
        注册
      </button>
    </form>
  );
}

export default function RegisterPage() {
  const [activeTab, setActiveTab] = useState<TabType>("student");

  return (
    <AuthLayout>
      <div className="auth-card">
        <div className="auth-card-header">
          <h2 className="auth-card-title">注册</h2>
        </div>

        <div className="flex rounded-lg border border-[var(--paper-border)] p-1 mb-5">
          <button
            type="button"
            className={cn(
              "flex-1 rounded-md py-2 text-sm font-medium transition-colors",
              activeTab === "student"
                ? "bg-[var(--gold)] text-white shadow-sm"
                : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]",
            )}
            onClick={() => setActiveTab("student")}
          >
            我是学生
          </button>
          <button
            type="button"
            className={cn(
              "flex-1 rounded-md py-2 text-sm font-medium transition-colors",
              activeTab === "teacher"
                ? "bg-[var(--gold)] text-white shadow-sm"
                : "text-[var(--muted-foreground)] hover:text-[var(--foreground)]",
            )}
            onClick={() => setActiveTab("teacher")}
          >
            我是教师
          </button>
        </div>

        {activeTab === "student" ? <StudentForm /> : <TeacherForm />}

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
