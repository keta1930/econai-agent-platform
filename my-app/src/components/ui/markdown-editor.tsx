import { useState } from "react";
import { cn } from "@/lib/utils";
import { Eye, Pencil, Columns2 } from "lucide-react";
import { MarkdownContent } from "./markdown-content";

type ViewMode = "edit" | "preview" | "split";

interface MarkdownEditorProps {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
  className?: string;
}

function ViewToggle({
  mode,
  active,
  onClick,
  children,
}: {
  mode: ViewMode;
  active: boolean;
  onClick: (mode: ViewMode) => void;
  children: React.ReactNode;
}) {
  return (
    <button
      type="button"
      onClick={() => onClick(mode)}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-md px-2.5 py-1 text-xs font-medium transition-all",
        active
          ? "bg-white text-foreground shadow-[var(--shadow-sm)] border border-[var(--paper-border)]"
          : "text-muted-foreground hover:text-foreground"
      )}
    >
      {children}
    </button>
  );
}

function MarkdownPreview({
  content,
  className,
}: {
  content: string;
  className?: string;
}) {
  if (!content) {
    return (
      <div className={cn("overflow-auto px-3 py-2", className)}>
        <p className="text-sm text-muted-foreground">暂无内容</p>
      </div>
    );
  }

  return (
    <MarkdownContent
      content={content}
      className={cn("overflow-auto px-3 py-2", className)}
    />
  );
}

export function MarkdownEditor({
  value,
  onChange,
  placeholder,
  className,
}: MarkdownEditorProps) {
  const [viewMode, setViewMode] = useState<ViewMode>("edit");

  const textareaClasses =
    "w-full resize-none bg-transparent px-3 py-2 font-mono text-sm leading-relaxed outline-none placeholder:text-muted-foreground min-h-[320px]";

  return (
    <div
      className={cn(
        "rounded-lg border border-input overflow-hidden transition-colors focus-within:border-[var(--cyan-mid)] focus-within:ring-2 focus-within:ring-[var(--cyan-mid)]/10",
        className
      )}
    >
      {/* View toggle bar */}
      <div className="flex items-center gap-0.5 border-b border-input bg-muted/30 px-2 py-1">
        <ViewToggle
          mode="edit"
          active={viewMode === "edit"}
          onClick={setViewMode}
        >
          <Pencil className="h-3 w-3" />
          编辑
        </ViewToggle>
        <ViewToggle
          mode="preview"
          active={viewMode === "preview"}
          onClick={setViewMode}
        >
          <Eye className="h-3 w-3" />
          预览
        </ViewToggle>
        <ViewToggle
          mode="split"
          active={viewMode === "split"}
          onClick={setViewMode}
        >
          <Columns2 className="h-3 w-3" />
          分栏
        </ViewToggle>
      </div>

      {/* Content area */}
      {viewMode === "edit" && (
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className={cn(textareaClasses, "min-h-[320px]")}
        />
      )}

      {viewMode === "preview" && (
        <MarkdownPreview content={value} className="min-h-[320px]" />
      )}

      {viewMode === "split" && (
        <div className="grid grid-cols-2 divide-x divide-input">
          <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            placeholder={placeholder}
            className={cn(textareaClasses, "min-h-[320px]")}
          />
          <MarkdownPreview content={value} className="min-h-[320px]" />
        </div>
      )}
    </div>
  );
}
