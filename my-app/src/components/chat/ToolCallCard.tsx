import { useState } from "react";
import { cn } from "@/lib/utils";
import { TOOL_DISPLAY } from "@/types/assistant";
import {
  ChevronRight,
  Loader2,
  CheckCircle2,
  XCircle,
  School,
  ClipboardList,
  FileText,
  BarChart3,
  Users,
  FileCheck,
  Eye,
  MessageSquare,
  FilePlus,
  Send,
  PlusCircle,
  Upload,
  HelpCircle,
  Globe,
  FileSpreadsheet,
  Wrench,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";

// ---------------------------------------------------------------------------
// Icon registry — maps Lucide icon names from TOOL_DISPLAY to components
// ---------------------------------------------------------------------------

const ICON_MAP: Record<string, LucideIcon> = {
  School,
  ClipboardList,
  FileText,
  BarChart3,
  Users,
  FileCheck,
  Eye,
  MessageSquare,
  FilePlus,
  Send,
  PlusCircle,
  Upload,
  HelpCircle,
  Globe,
  FileSpreadsheet,
};

type ToolStatus = "running" | "complete" | "error";

interface ToolCallCardProps {
  name: string;
  args: Record<string, unknown>;
  result?: string;
  isError?: boolean;
  status: ToolStatus;
}

function getToolIcon(name: string): LucideIcon {
  const display = TOOL_DISPLAY[name];
  if (display) {
    const Icon = ICON_MAP[display.icon];
    if (Icon) return Icon;
  }
  return Wrench;
}

function getDisplayName(name: string): string {
  return TOOL_DISPLAY[name]?.label ?? name;
}

export function ToolCallCard({ name, args, result, isError, status }: ToolCallCardProps) {
  const [expanded, setExpanded] = useState(false);
  const Icon = getToolIcon(name);
  const displayName = getDisplayName(name);

  return (
    <div
      className={cn(
        "rounded-md border my-1 text-xs transition-colors",
        status === "running" && "bg-[var(--paper-warm)] border-[var(--paper-border)]",
        status === "complete" && "bg-[var(--paper)] border-[var(--paper-border)]",
        status === "error" && "bg-red-50 border-[var(--danger)]/30",
      )}
    >
      {/* Header — always visible */}
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left"
      >
        <Icon className="h-3.5 w-3.5 text-[var(--muted-foreground)] shrink-0" />
        <span className="font-medium text-foreground flex-1 truncate">{displayName}</span>

        {/* Status indicator */}
        {status === "running" && (
          <Loader2 className="h-3.5 w-3.5 text-[var(--cyan-mid)] animate-spin shrink-0" />
        )}
        {status === "complete" && (
          <CheckCircle2 className="h-3.5 w-3.5 text-[var(--success)] shrink-0" />
        )}
        {status === "error" && (
          <XCircle className="h-3.5 w-3.5 text-[var(--danger)] shrink-0" />
        )}

        <ChevronRight
          className={cn(
            "h-3.5 w-3.5 text-[var(--muted-foreground)] transition-transform shrink-0",
            expanded && "rotate-90",
          )}
        />
      </button>

      {/* Expanded detail */}
      {expanded && (
        <div className="border-t border-[var(--paper-border)] px-3 py-2 space-y-2">
          {Object.keys(args).length > 0 && (
            <div>
              <div className="text-[10px] font-medium text-[var(--muted-foreground)] tracking-wider mb-1">
                参数
              </div>
              <pre className="text-[11px] text-foreground bg-[var(--paper-deep)] rounded p-2 overflow-x-auto whitespace-pre-wrap break-all">
                {JSON.stringify(args, null, 2)}
              </pre>
            </div>
          )}
          {result !== undefined && (
            <div>
              <div className="text-[10px] font-medium text-[var(--muted-foreground)] tracking-wider mb-1">
                {isError ? "错误" : "结果"}
              </div>
              <pre
                className={cn(
                  "text-[11px] rounded p-2 overflow-x-auto whitespace-pre-wrap break-all",
                  isError
                    ? "text-[var(--danger)] bg-red-50"
                    : "text-foreground bg-[var(--paper-deep)]",
                )}
              >
                {result}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
