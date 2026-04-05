import { Outlet, Link, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from "@/components/ui/sheet";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { useAuth } from "@/hooks/useAuth";
import { useClassContext } from "@/contexts/ClassContext";
import {
  School, LayoutDashboard, PlusCircle, Users, Cpu, Presentation, Database,
  LogOut, Menu, Bot,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useState, useEffect } from "react";
import { ChatPanel } from "@/components/chat/ChatPanel";
import { ChatProvider, useChatContext } from "@/contexts/ChatContext";
import { passwordResetApi } from "@/api/password-reset";

interface NavItem {
  label: string;
  href: string;
  icon: typeof School;
  /** When set, the item acts as a button instead of a link */
  action?: () => void;
  /** Badge count shown next to the label */
  badge?: number;
}

function getClassNav(resetBadge?: number): NavItem[] {
  return [
    { label: "班级管理", href: "/admin/classes", icon: School },
    { label: "学生名单", href: "/admin/roster", icon: Users, badge: resetBadge },
  ];
}

function getTaskNav(_togglePanel?: () => void): NavItem[] {
  return [
    { label: "作业列表", href: "/admin/dashboard", icon: LayoutDashboard },
    { label: "创建作业", href: "/admin/tasks/new", icon: PlusCircle },
    { label: "分享管理", href: "/admin/sharing", icon: Presentation },
  ];
}

function getAssistantNav(togglePanel?: () => void): NavItem[] {
  return [
    { label: "AI 助教", href: "#ai-assistant", icon: Bot, action: togglePanel },
  ];
}

const systemNav: NavItem[] = [
  { label: "模型管理", href: "/admin/models", icon: Cpu },
  { label: "数据备份", href: "/admin/backups", icon: Database },
];

function ClassSelector() {
  const { currentClass, classes, setCurrentClass } = useClassContext();

  if (classes.length === 0) return null;

  return (
    <div className="mx-4 mb-4">
      <Select
        value={currentClass?.name}
        onValueChange={(name) => {
          const found = classes.find((c) => c.name === name);
          if (found) setCurrentClass(found);
        }}
      >
        <SelectTrigger
          className={cn(
            "w-full text-xs h-9 rounded-lg",
            "bg-[var(--ink-mid)] border-[rgba(201,169,110,0.15)] text-[var(--text-on-dark)]",
            // hover / focus 融入墨蓝 + 金色体系
            "hover:border-[var(--gold-dim)] hover:bg-[var(--ink-light)]",
            "focus-visible:border-[var(--gold)]/30 focus-visible:ring-2 focus-visible:ring-[var(--gold)]/10",
            // 下拉箭头适配浅色
            "[&_svg]:text-[var(--text-on-dark-secondary)]",
          )}
        >
          <SelectValue placeholder="选择班级" />
        </SelectTrigger>
        <SelectContent
          className={cn(
            "bg-[var(--ink-light)] border-[rgba(201,169,110,0.12)]",
            "shadow-[0_8px_24px_rgba(0,0,0,0.4)]",
          )}
        >
          {classes.map((c) => (
            <SelectItem
              key={c.id}
              value={c.name}
              className={cn(
                "text-xs text-[var(--text-on-dark-secondary)] rounded-none",
                "focus:bg-[var(--ink-mid)] focus:text-[var(--text-on-dark)]",
              )}
            >
              {c.name}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}

function NavSection({ label, items, onNavigate, isPanelOpen }: { label: string; items: NavItem[]; onNavigate?: () => void; isPanelOpen?: boolean }) {
  const location = useLocation();

  return (
    <>
      <div className="px-6 pt-3 pb-2 text-[10px] font-semibold text-[var(--text-on-dark-secondary)] tracking-[3px] uppercase">
        {label}
      </div>
      {items.map((item) => {
        const Icon = item.icon;
        const isActive =
          item.href === "/admin/dashboard"
            ? location.pathname === "/admin/dashboard" || location.pathname === "/admin"
            : item.action
              ? !!isPanelOpen
              : location.pathname.startsWith(item.href);

        const className = cn(
          "flex items-center gap-3 border-l-2 px-6 py-2.5 text-[13px] transition-colors w-full",
          isActive
            ? "text-gold bg-[rgba(201,169,110,0.06)] border-l-gold"
            : "border-l-transparent text-[var(--text-on-dark-secondary)] hover:text-[var(--text-on-dark)] hover:bg-[var(--ink-mid)]",
        );

        const badgeEl = item.badge != null && item.badge > 0 ? (
          <span className="ml-auto inline-flex items-center justify-center min-w-[18px] h-[18px] px-1 rounded-full bg-[var(--gold)]/20 text-[var(--gold)] text-[10px] font-semibold leading-none">
            {item.badge}
          </span>
        ) : null;

        // Action items render as buttons instead of links
        if (item.action) {
          return (
            <button
              key={item.href}
              type="button"
              onClick={() => {
                item.action?.();
                onNavigate?.();
              }}
              className={className}
            >
              <Icon className="h-[18px] w-[18px] opacity-70" />
              {item.label}
              {badgeEl}
            </button>
          );
        }

        return (
          <Link
            key={item.href}
            to={item.href}
            onClick={onNavigate}
            className={className}
          >
            <Icon className="h-[18px] w-[18px] opacity-70" />
            {item.label}
            {badgeEl}
          </Link>
        );
      })}
    </>
  );
}

function SidebarContent({ onNavigate, togglePanel, isPanelOpen, resetBadge }: { onNavigate?: () => void; togglePanel?: () => void; isPanelOpen?: boolean; resetBadge?: number }) {
  const { logout } = useAuth();
  const classNav = getClassNav(resetBadge);
  const taskNav = getTaskNav(togglePanel);
  const assistantNav = getAssistantNav(togglePanel);

  return (
    <div className="flex h-full flex-col pt-6">
      {/* Brand area */}
      <div className="px-6 pb-6 border-b border-[var(--ink-mid)] mb-4">
        <span className="font-heading text-base font-semibold text-gold tracking-[2px]">
          智能体课程
        </span>
        <p className="text-[11px] text-[var(--text-on-dark-secondary)] mt-1 tracking-[1px]">
          教学管理平台
        </p>
      </div>

      {/* Class selector */}
      <ClassSelector />

      {/* Navigation */}
      <nav className="flex-1">
        <NavSection label="班 级" items={classNav} onNavigate={onNavigate} />
        <NavSection label="教 学" items={taskNav} onNavigate={onNavigate} />
        <NavSection label="助 手" items={assistantNav} onNavigate={onNavigate} isPanelOpen={isPanelOpen} />
        <NavSection label="系 统" items={systemNav} onNavigate={onNavigate} />
      </nav>

      {/* Footer logout */}
      <div className="border-t border-[var(--ink-mid)] px-6 py-4">
        <button
          onClick={logout}
          className="flex items-center gap-3 text-[13px] text-[var(--text-on-dark-secondary)] hover:text-[var(--text-on-dark)] transition-colors"
        >
          <LogOut className="h-[18px] w-[18px] opacity-70" />
          登出
        </button>
      </div>
    </div>
  );
}

function AdminLayoutInner() {
  const [sheetOpen, setSheetOpen] = useState(false);
  const { togglePanel, isPanelOpen } = useChatContext();
  const { currentClass } = useClassContext();
  const [resetBadge, setResetBadge] = useState<number | undefined>(undefined);

  useEffect(() => {
    if (!currentClass?.id) {
      setResetBadge(undefined);
      return;
    }
    let cancelled = false;
    passwordResetApi.count(currentClass.id).then((res) => {
      if (!cancelled) setResetBadge(res.count);
    }).catch(() => {
      if (!cancelled) setResetBadge(undefined);
    });
    return () => { cancelled = true; };
  }, [currentClass?.id]);

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
            <SidebarContent onNavigate={() => setSheetOpen(false)} togglePanel={togglePanel} isPanelOpen={isPanelOpen} resetBadge={resetBadge} />
          </SheetContent>
        </Sheet>
        <span className="ml-3 font-heading font-semibold text-primary tracking-[2px]">智能体课程</span>
      </header>

      <div className="flex">
        {/* Desktop sidebar */}
        <aside className="hidden lg:flex lg:w-60 lg:flex-col lg:fixed lg:inset-y-0 border-r border-[var(--ink-mid)] bg-[var(--ink-deep)]">
          <SidebarContent togglePanel={togglePanel} isPanelOpen={isPanelOpen} resetBadge={resetBadge} />
        </aside>

        {/* Main content + Chat panel */}
        <main className="flex-1 lg:ml-60 flex h-[calc(100vh-3.5rem)] lg:h-screen">
          <div className="flex-1 min-w-0 overflow-y-auto px-6 py-8 lg:px-12 lg:py-12">
            <Outlet />
          </div>
          <ChatPanel />
        </main>
      </div>
    </div>
  );
}

export function AdminLayout() {
  return (
    <ChatProvider>
      <AdminLayoutInner />
    </ChatProvider>
  );
}
