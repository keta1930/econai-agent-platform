import type { TokenUsage } from "@/types/assistant";
import { cn } from "@/lib/utils";

interface TokenBarProps {
  usage: TokenUsage;
}

function formatTokenCount(n: number): string {
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return String(n);
}

function getBarColor(ratio: number): string {
  if (ratio > 0.7) return "bg-[var(--danger)]";
  if (ratio > 0.5) return "bg-[var(--warning)]";
  return "bg-[var(--cyan-mid)]";
}

export function TokenBar({ usage }: TokenBarProps) {
  const percent = Math.min(usage.ratio * 100, 100);

  return (
    <div className="px-4 py-2 border-t border-[var(--paper-border)]">
      <div className="flex items-center justify-between text-[11px] text-[var(--muted-foreground)] mb-1">
        <span>
          对话容量: {formatTokenCount(usage.total)} / {formatTokenCount(usage.max)}{" "}
          ({percent.toFixed(1)}%)
        </span>
        {usage.ratio > 0.7 && (
          <span className="text-[var(--danger)] font-medium">
            对话较长，即将自动精简
          </span>
        )}
      </div>
      <div className="h-1 w-full rounded-full bg-[var(--paper-deep)]">
        <div
          className={cn("h-full rounded-full transition-all", getBarColor(usage.ratio))}
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}
