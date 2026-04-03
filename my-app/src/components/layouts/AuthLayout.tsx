import type { ReactNode } from "react";

/**
 * Auth pages layout — split-screen with ink brand panel (left) and form area (right).
 * Left panel hidden below 768px.
 */
export function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <div className="min-h-screen flex">
      {/* Left: Ink Brand Panel */}
      <div
        className="hidden md:flex md:w-1/2 items-center justify-center relative overflow-hidden ink-brand-panel"
        style={{
          background:
            "linear-gradient(165deg, #0d1520 0%, #1a2332 40%, #243044 100%)",
        }}
      >
        {/* Decorative ink strokes */}
        <div className="absolute top-[20%] left-[5%] w-[120px] h-px -rotate-[15deg] bg-gradient-to-r from-transparent via-[var(--cyan-mid)] to-transparent opacity-10" />
        <div className="absolute bottom-[25%] right-[8%] w-[80px] h-px rotate-[10deg] bg-gradient-to-r from-transparent via-[var(--cyan-mid)] to-transparent opacity-10" />
        <div className="absolute top-[60%] left-[10%] w-[60px] h-px -rotate-[5deg] bg-gradient-to-r from-transparent via-[var(--cyan-mid)] to-transparent opacity-10" />

        {/* Brand content */}
        <div className="relative z-10 text-center p-12">
          {/* Seal logo — 印章式 */}
          <div className="relative w-20 h-20 border-2 border-[var(--gold)] rounded-sm flex items-center justify-center -rotate-[3deg] mx-auto mb-8">
            <span className="font-heading text-4xl font-bold text-[var(--gold)]">
              学
            </span>
            {/* Outer auxiliary border */}
            <div className="absolute inset-[-4px] border border-[var(--gold-dim)] rounded-md pointer-events-none" />
          </div>

          <h1 className="font-heading text-[28px] font-semibold text-[var(--text-on-dark)] tracking-[4px] leading-relaxed">
            经济金融
            <br />
            AI 智能体设计
          </h1>

          {/* Gold divider */}
          <div
            className="w-12 h-px mx-auto my-6"
            style={{
              background:
                "linear-gradient(90deg, transparent, var(--gold), transparent)",
            }}
          />

          <p className="text-[15px] text-[var(--text-on-dark-secondary)] tracking-[6px]">
            岭南学院
          </p>
        </div>
      </div>

      {/* Right: Form Panel */}
      <div className="flex-1 flex items-center justify-center p-12 bg-[var(--paper)] relative paper-texture">
        {children}
      </div>
    </div>
  );
}
