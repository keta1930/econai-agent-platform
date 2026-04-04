import { useState, useEffect, type FormEvent } from "react";
import { Outlet, Link, useLocation } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { authApi } from "@/api/auth";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import {
  Loader2, ClipboardList, BarChart3, Share2,
  UserPlus, ArrowLeftRight, KeyRound, LogOut, Menu,
} from "lucide-react";
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
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from "@/components/ui/sheet";
import type { MyClassItem } from "@/types/auth";

interface NavItem {
  label: string;
  href: string;
  icon: typeof ClipboardList;
}

interface ActionItem {
  label: string;
  icon: typeof ClipboardList;
  onClick: () => void;
}

const learningNav: NavItem[] = [
  { label: "任务列表", href: "/student/tasks", icon: ClipboardList },
  { label: "我的成绩", href: "/student/grades", icon: BarChart3 },
  { label: "课程分享", href: "/student/sharing", icon: Share2 },
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

function JoinClassDialog({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const auth = useAuth();
  const [joinToken, setJoinToken] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  function handleClose() {
    setJoinToken("");
    setError("");
    onOpenChange(false);
  }

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
      handleClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "加入失败");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Dialog open={open} onOpenChange={(o) => !o && handleClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>加入班级</DialogTitle>
          <DialogDescription>
            请输入老师提供的加入凭证
          </DialogDescription>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="space-y-2">
            <Label htmlFor="join-token">加入凭证</Label>
            <Input
              id="join-token"
              placeholder="请输入加入凭证"
              value={joinToken}
              onChange={(e) => setJoinToken(e.target.value)}
              autoFocus
            />
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <DialogFooter>
            <Button variant="outline" type="button" onClick={handleClose}>
              取消
            </Button>
            <Button
              type="submit"
              disabled={!joinToken.trim() || loading}
            >
              {loading && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              加入班级
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

function NavSection({
  label,
  items,
  onNavigate,
}: {
  label: string;
  items: NavItem[];
  onNavigate?: () => void;
}) {
  const location = useLocation();

  return (
    <>
      <div className="px-6 pt-3 pb-2 text-[10px] font-semibold text-[var(--text-on-dark-secondary)] tracking-[3px] uppercase">
        {label}
      </div>
      {items.map((item) => {
        const Icon = item.icon;
        const isActive = location.pathname.startsWith(item.href);
        return (
          <Link
            key={item.href}
            to={item.href}
            onClick={onNavigate}
            className={cn(
              "flex items-center gap-3 border-l-2 px-6 py-2.5 text-[13px] transition-colors",
              isActive
                ? "text-gold bg-[rgba(201,169,110,0.06)] border-l-gold"
                : "border-l-transparent text-[var(--text-on-dark-secondary)] hover:text-[var(--text-on-dark)] hover:bg-[var(--ink-mid)]",
            )}
          >
            <Icon className="h-[18px] w-[18px] opacity-70" />
            {item.label}
          </Link>
        );
      })}
    </>
  );
}

function ActionSection({
  label,
  items,
  onNavigate,
}: {
  label: string;
  items: ActionItem[];
  onNavigate?: () => void;
}) {
  return (
    <>
      <div className="px-6 pt-3 pb-2 text-[10px] font-semibold text-[var(--text-on-dark-secondary)] tracking-[3px] uppercase">
        {label}
      </div>
      {items.map((item) => {
        const Icon = item.icon;
        return (
          <button
            key={item.label}
            type="button"
            onClick={() => {
              onNavigate?.();
              item.onClick();
            }}
            className="flex w-full items-center gap-3 border-l-2 border-l-transparent px-6 py-2.5 text-[13px] text-[var(--text-on-dark-secondary)] transition-colors hover:text-[var(--text-on-dark)] hover:bg-[var(--ink-mid)]"
          >
            <Icon className="h-[18px] w-[18px] opacity-70" />
            {item.label}
          </button>
        );
      })}
    </>
  );
}

function SidebarContent({
  onNavigate,
  classActions,
  accountActions,
  logout,
}: {
  onNavigate?: () => void;
  classActions: ActionItem[];
  accountActions: ActionItem[];
  logout: () => void;
}) {
  return (
    <div className="flex h-full flex-col pt-6">
      {/* Brand area */}
      <div className="px-6 pb-6 border-b border-[var(--ink-mid)] mb-4">
        <span className="font-heading text-base font-semibold text-gold tracking-[2px]">
          智能体课程
        </span>
        <p className="text-[11px] text-[var(--text-on-dark-secondary)] mt-1 tracking-[1px]">
          学生学习平台
        </p>
      </div>

      {/* Navigation */}
      <nav className="flex-1">
        <NavSection label="学 习" items={learningNav} onNavigate={onNavigate} />
        <ActionSection label="班 级" items={classActions} onNavigate={onNavigate} />
        <ActionSection label="账 号" items={accountActions} onNavigate={onNavigate} />
      </nav>

      {/* Footer logout */}
      <div className="border-t border-[var(--ink-mid)] px-6 py-4">
        <button
          onClick={() => {
            onNavigate?.();
            logout();
          }}
          className="flex items-center gap-3 text-[13px] text-[var(--text-on-dark-secondary)] hover:text-[var(--text-on-dark)] transition-colors"
        >
          <LogOut className="h-[18px] w-[18px] opacity-70" />
          登出
        </button>
      </div>
    </div>
  );
}

export function StudentLayout() {
  const { logout, className: currentClassName, classId } = useAuth();

  const [needsProfile, setNeedsProfile] = useState(false);
  const [showPasswordDialog, setShowPasswordDialog] = useState(false);
  const [showClassDialog, setShowClassDialog] = useState(false);
  const [showJoinDialog, setShowJoinDialog] = useState(false);
  const [sheetOpen, setSheetOpen] = useState(false);

  const classActions: ActionItem[] = [
    { label: "加入班级", icon: UserPlus, onClick: () => setShowJoinDialog(true) },
    { label: "切换班级", icon: ArrowLeftRight, onClick: () => setShowClassDialog(true) },
  ];

  const accountActions: ActionItem[] = [
    { label: "修改密码", icon: KeyRound, onClick: () => setShowPasswordDialog(true) },
  ];

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
      {/* Mobile header */}
      <header className="sticky top-0 z-40 flex h-14 items-center border-b border-[var(--paper-border)] bg-background/95 backdrop-blur px-4 lg:hidden">
        <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
          <SheetTrigger
            render={<Button variant="ghost" size="icon" />}
          >
            <Menu className="h-5 w-5" />
          </SheetTrigger>
          <SheetContent side="left" className="w-60 p-0 bg-[var(--ink-deep)]">
            <SheetTitle className="sr-only">导航菜单</SheetTitle>
            <SidebarContent
              onNavigate={() => setSheetOpen(false)}
              classActions={classActions}
              accountActions={accountActions}
              logout={logout}
            />
          </SheetContent>
        </Sheet>
        <span className="ml-3 font-heading font-semibold text-primary tracking-[2px]">智能体课程</span>
        {currentClassName && (
          <span className="ml-auto text-[13px] text-muted-foreground">{currentClassName}</span>
        )}
      </header>

      <div className="flex">
        {/* Desktop sidebar */}
        <aside className="hidden lg:flex lg:w-60 lg:flex-col lg:fixed lg:inset-y-0 border-r border-[var(--ink-mid)] bg-[var(--ink-deep)]">
          <SidebarContent
            classActions={classActions}
            accountActions={accountActions}
            logout={logout}
          />
        </aside>

        {/* Main content */}
        <main className="flex-1 lg:ml-60">
          <div className="min-w-0 px-6 py-8 lg:px-12 lg:py-12">
            <Outlet />
          </div>
        </main>
      </div>

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

      {/* Join class */}
      <JoinClassDialog
        open={showJoinDialog}
        onOpenChange={setShowJoinDialog}
      />
    </div>
  );
}
