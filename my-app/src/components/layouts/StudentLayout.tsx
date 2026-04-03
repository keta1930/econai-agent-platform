import { Outlet, Link, useLocation } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { cn } from "@/lib/utils";

const navItems = [
  { label: "任务列表", href: "/student/tasks" },
  { label: "我的成绩", href: "/student/grades" },
  { label: "课程分享", href: "/student/sharing" },
];

export function StudentLayout() {
  const { logout } = useAuth();
  const location = useLocation();

  return (
    <div className="min-h-screen bg-background">
      {/* Top navigation bar */}
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

        {/* Logout */}
        <button
          type="button"
          onClick={logout}
          className="ml-auto rounded-lg px-4 py-2 text-[13px] font-medium text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
        >
          登出
        </button>
      </header>

      {/* Content area */}
      <main className="mx-auto max-w-[720px] px-6 py-12">
        <Outlet />
      </main>
    </div>
  );
}
