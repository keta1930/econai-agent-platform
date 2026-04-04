import { useState, useEffect, type FormEvent } from "react";
import { Outlet, Link, useLocation } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { authApi } from "@/api/auth";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import { Loader2, ChevronDown, KeyRound, ArrowLeftRight } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Label } from "@/components/ui/label";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
  DialogDescription,
} from "@/components/ui/dialog";
import type { MyClassItem } from "@/types/auth";

const navItems = [
  { label: "任务列表", href: "/student/tasks" },
  { label: "我的成绩", href: "/student/grades" },
  { label: "课程分享", href: "/student/sharing" },
  { label: "加入班级", href: "/student/join-class" },
];

function ProfileDialog({
  open,
  onComplete,
}: {
  open: boolean;
  onComplete: (name: string) => void;
}) {
  const [displayName, setDisplayName] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!displayName.trim()) return;
    setError("");
    setLoading(true);
    try {
      const res = await authApi.updateProfile({
        display_name: displayName.trim(),
      });
      onComplete(res.display_name);
    } catch (err) {
      setError(err instanceof Error ? err.message : "保存失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open}>
      <DialogContent showCloseButton={false}>
        <DialogHeader>
          <DialogTitle>完善个人信息</DialogTitle>
          <DialogDescription>请填写你的真实姓名，方便教师识别</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="profile-name">姓名</Label>
            <Input
              id="profile-name"
              placeholder="请输入真实姓名"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              autoFocus
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <DialogFooter>
            <Button type="submit" disabled={!displayName.trim() || loading}>
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              保存
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function ChangePasswordDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function handleClose() {
    setCurrentPassword("");
    setNewPassword("");
    setError("");
    onOpenChange(false);
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!currentPassword || !newPassword) return;
    setError("");
    setLoading(true);
    try {
      const res = await authApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      toast.success(
        `密码修改成功（已使用 ${res.password_change_count}/3 次修改机会）`,
      );
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "修改失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && handleClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>修改密码</DialogTitle>
          <DialogDescription>每位学生最多可修改 3 次密码</DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="current-pwd">当前密码</Label>
            <Input
              id="current-pwd"
              type="password"
              placeholder="请输入当前密码"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="new-pwd">新密码</Label>
            <Input
              id="new-pwd"
              type="password"
              placeholder="请输入新密码"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <DialogFooter>
            <Button variant="outline" type="button" onClick={handleClose}>
              取消
            </Button>
            <Button
              type="submit"
              disabled={!currentPassword || !newPassword || loading}
            >
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              确认修改
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

function SwitchClassDialog({
  open,
  onOpenChange,
  currentClassId,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentClassId: string | null;
}) {
  const { switchClass } = useAuth();
  const [classes, setClasses] = useState<MyClassItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [switching, setSwitching] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setLoading(true);
    authApi
      .getMyClasses()
      .then((res) => setClasses(res.classes))
      .catch(() => toast.error("获取班级列表失败"))
      .finally(() => setLoading(false));
  }, [open]);

  async function handleSwitch(classId: string) {
    setSwitching(classId);
    try {
      await switchClass(classId);
      toast.success("班级切换成功");
      onOpenChange(false);
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "切换失败");
    } finally {
      setSwitching(null);
    }
  }

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>切换班级</DialogTitle>
        </DialogHeader>
        {loading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : classes.length === 0 ? (
          <p className="py-4 text-center text-sm text-muted-foreground">
            暂无可切换的班级
          </p>
        ) : (
          <div className="space-y-2">
            {classes.map((cls) => {
              const isCurrent = cls.class_id === currentClassId;
              return (
                <button
                  key={cls.class_id}
                  type="button"
                  disabled={isCurrent || switching !== null}
                  onClick={() => handleSwitch(cls.class_id)}
                  className={cn(
                    "flex w-full items-center justify-between rounded-lg border px-4 py-3 text-left transition-colors",
                    isCurrent
                      ? "border-[var(--gold)] bg-[rgba(201,169,110,0.08)]"
                      : "border-border hover:bg-muted",
                  )}
                >
                  <div>
                    <p className="text-sm font-medium">{cls.class_name}</p>
                    <p className="text-xs text-muted-foreground">
                      {cls.admin_name}
                    </p>
                  </div>
                  {isCurrent ? (
                    <span className="text-xs text-[var(--gold)]">当前</span>
                  ) : switching === cls.class_id ? (
                    <Loader2 className="h-4 w-4 animate-spin" />
                  ) : null}
                </button>
              );
            })}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

export function StudentLayout() {
  const { logout, className: currentClassName, classId } = useAuth();
  const location = useLocation();

  const [needsProfile, setNeedsProfile] = useState(false);
  const [showPasswordDialog, setShowPasswordDialog] = useState(false);
  const [showClassDialog, setShowClassDialog] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);

  // Check if display_name needs to be filled by decoding the JWT
  useEffect(() => {
    const token = localStorage.getItem("token");
    if (!token) return;
    try {
      const payload = JSON.parse(atob(token.split(".")[1]));
      if (payload.role === "student" && !payload.display_name) {
        setNeedsProfile(true);
      }
    } catch {
      // Ignore decode errors
    }
  }, []);

  function handleProfileComplete(name: string) {
    setNeedsProfile(false);
    toast.success(`姓名已设置为「${name}」`);
  }

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-50 flex h-14 items-center border-b border-[var(--paper-border)] bg-white px-4 md:px-8">
        {/* Brand */}
        <Link
          to="/student/tasks"
          className="mr-10 flex items-center gap-2 font-heading text-[15px] font-semibold text-[var(--ink-deep)]"
        >
          <span className="flex h-6 w-6 items-center justify-center rounded-sm border-[1.5px] border-gold font-heading text-xs font-bold text-gold -rotate-[3deg]">
            学
          </span>
          <span className="hidden sm:inline">智能体课程平台</span>
        </Link>

        {/* Nav items */}
        <nav className="flex items-center gap-1">
          {navItems.map((item) => {
            const isActive = location.pathname.startsWith(item.href);
            return (
              <Link
                key={item.href}
                to={item.href}
                className={cn(
                  "rounded-lg px-4 py-2 text-[13px] font-medium transition-colors",
                  isActive
                    ? "bg-[rgba(201,169,110,0.15)] text-[var(--ink-deep)]"
                    : "text-muted-foreground hover:bg-muted hover:text-foreground",
                )}
              >
                {item.label}
              </Link>
            );
          })}
        </nav>

        {/* Right section: class name + user menu */}
        <div className="ml-auto flex items-center gap-2">
          {/* Class indicator */}
          {currentClassName && (
            <button
              type="button"
              onClick={() => setShowClassDialog(true)}
              className="flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-[13px] font-medium text-[var(--ink-deep)] transition-colors hover:bg-muted"
              title="切换班级"
            >
              <ArrowLeftRight className="h-3.5 w-3.5 text-muted-foreground" />
              {currentClassName}
            </button>
          )}

          {/* User menu dropdown */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setMenuOpen(!menuOpen)}
              className="flex items-center gap-1 rounded-lg px-3 py-2 text-[13px] font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
            >
              更多
              <ChevronDown
                className={cn(
                  "h-3.5 w-3.5 transition-transform",
                  menuOpen && "rotate-180",
                )}
              />
            </button>
            {menuOpen && (
              <>
                {/* Click-away backdrop */}
                <div
                  className="fixed inset-0 z-40"
                  onClick={() => setMenuOpen(false)}
                />
                <div className="absolute right-0 top-full z-50 mt-1 w-40 rounded-lg border border-border bg-white py-1 shadow-lg">
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 px-3 py-2 text-[13px] text-foreground transition-colors hover:bg-muted"
                    onClick={() => {
                      setMenuOpen(false);
                      setShowPasswordDialog(true);
                    }}
                  >
                    <KeyRound className="h-3.5 w-3.5" />
                    修改密码
                  </button>
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 px-3 py-2 text-[13px] text-destructive transition-colors hover:bg-muted"
                    onClick={() => {
                      setMenuOpen(false);
                      logout();
                    }}
                  >
                    登出
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-[720px] px-6 py-12">
        <Outlet />
      </main>

      {/* Profile completion (non-dismissible) */}
      <ProfileDialog open={needsProfile} onComplete={handleProfileComplete} />

      {/* Password change */}
      <ChangePasswordDialog
        open={showPasswordDialog}
        onOpenChange={setShowPasswordDialog}
      />

      {/* Class switching */}
      <SwitchClassDialog
        open={showClassDialog}
        onOpenChange={setShowClassDialog}
        currentClassId={classId}
      />
    </div>
  );
}
