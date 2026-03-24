import { Outlet, Link, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { useAuth } from "@/hooks/useAuth";
import { BookOpen, LogOut } from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { label: "任务列表", href: "/student/tasks" },
  { label: "我的成绩", href: "/student/grades" },
];

export function StudentLayout() {
  const { logout } = useAuth();
  const location = useLocation();

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 h-16 border-b bg-background/95 backdrop-blur">
        <div className="mx-auto flex h-full max-w-4xl items-center justify-between px-4 lg:px-8">
          <div className="flex items-center gap-6">
            <Link to="/student/tasks" className="flex items-center gap-2 text-primary font-heading font-semibold">
              <BookOpen className="h-5 w-5" />
              <span className="hidden sm:inline">智能体课程平台</span>
            </Link>
            <nav className="flex items-center gap-1">
              {navItems.map((item) => (
                <Link
                  key={item.href}
                  to={item.href}
                  className={cn(
                    "rounded-md px-3 py-2 text-sm font-medium transition-colors",
                    location.pathname.startsWith(item.href)
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:text-foreground hover:bg-accent",
                  )}
                >
                  {item.label}
                </Link>
              ))}
            </nav>
          </div>
          <Button variant="ghost" size="sm" onClick={logout}>
            <LogOut className="mr-2 h-4 w-4" />
            登出
          </Button>
        </div>
      </header>
      <main className="mx-auto max-w-4xl px-4 py-6 lg:px-8">
        <Outlet />
      </main>
    </div>
  );
}
