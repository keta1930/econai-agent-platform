import { Outlet, Link, useLocation } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent, SheetTrigger, SheetTitle } from "@/components/ui/sheet";
import { useAuth } from "@/hooks/useAuth";
import { Shield, Ticket, LogOut, Menu } from "lucide-react";
import { cn } from "@/lib/utils";
import { useState } from "react";

const navItems = [
  { label: "邀请码管理", href: "/super-admin/invite-codes", icon: Ticket },
  { label: "教师管理", href: "/super-admin/teachers", icon: Shield },
];

function SidebarContent({ onNavigate }: { onNavigate?: () => void }) {
  const { logout } = useAuth();
  const location = useLocation();

  return (
    <div className="flex h-full flex-col pt-6">
      <div className="px-6 pb-6 border-b border-[var(--ink-mid)] mb-4">
        <span className="font-heading text-base font-semibold text-gold tracking-[2px]">系统管理</span>
        <p className="text-[11px] text-[var(--text-on-dark-secondary)] mt-1 tracking-[1px]">SYSTEM MANAGEMENT</p>
      </div>
      <div className="px-6 pt-3 pb-2 text-[10px] font-semibold text-[var(--text-on-dark-secondary)] tracking-[3px] uppercase">管理</div>
      <nav className="flex-1">
        {navItems.map((item) => {
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
      </nav>
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

export function SuperAdminLayout() {
  const [sheetOpen, setSheetOpen] = useState(false);

  return (
    <div className="min-h-screen bg-background">
      <header className="sticky top-0 z-40 flex h-16 items-center border-b bg-background/95 backdrop-blur px-4 lg:hidden">
        <Sheet open={sheetOpen} onOpenChange={setSheetOpen}>
          <SheetTrigger
            render={<Button variant="ghost" size="icon" />}
          >
            <Menu className="h-5 w-5" />
          </SheetTrigger>
          <SheetContent side="left" className="w-60 p-0 bg-[var(--ink-deep)]">
            <SheetTitle className="sr-only">导航菜单</SheetTitle>
            <SidebarContent onNavigate={() => setSheetOpen(false)} />
          </SheetContent>
        </Sheet>
        <span className="ml-3 font-heading font-semibold text-primary">系统管理</span>
      </header>

      <div className="flex">
        <aside className="hidden lg:flex lg:w-60 lg:flex-col lg:fixed lg:inset-y-0 bg-[var(--ink-deep)] border-r border-[var(--ink-mid)]">
          <SidebarContent />
        </aside>

        <main className="flex-1 lg:ml-60">
          <div className="min-w-0 px-6 py-8 lg:px-12 lg:py-12">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
