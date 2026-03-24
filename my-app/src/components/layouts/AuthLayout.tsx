import type { ReactNode } from "react";

export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex">
      {/* Brand panel - desktop only */}
      <div className="hidden lg:flex lg:w-1/2 bg-primary text-primary-foreground relative overflow-hidden">
        <div className="relative z-10 flex flex-col items-center justify-center w-full px-12 text-center">
          <h1 className="font-heading text-4xl font-semibold tracking-tight">
            经济金融AI智能体设计课程平台
          </h1>
          <p className="mt-4 text-lg opacity-80 max-w-md">
            岭南学院
          </p>
        </div>

        {/* Decorative geometric elements */}
        <div className="absolute top-12 left-12 h-24 w-24 rounded-full border border-primary-foreground/20" />
        <div className="absolute top-20 left-20 h-16 w-16 rounded-full bg-primary-foreground/10" />
        <div className="absolute bottom-16 right-16 h-32 w-32 rounded-full border border-primary-foreground/15" />
        <div className="absolute bottom-24 right-24 h-20 w-20 rounded-full bg-primary-foreground/8" />
        <div className="absolute top-1/3 right-12 h-px w-24 bg-primary-foreground/20" />
        <div className="absolute bottom-1/3 left-8 h-px w-32 bg-primary-foreground/15" />
        <div className="absolute top-1/2 left-1/4 h-3 w-3 rounded-full bg-primary-foreground/20" />
        <div className="absolute bottom-1/4 right-1/3 h-2 w-2 rounded-full bg-primary-foreground/25" />
      </div>

      {/* Form area */}
      <div className="flex-1 flex items-center justify-center px-4 bg-muted/30">
        {children}
      </div>
    </div>
  );
}
