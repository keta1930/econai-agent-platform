import { useState, useCallback, type ReactNode } from "react";
import { Copy, Check } from "lucide-react";

interface ChatCodeBlockProps {
  language: string;
  children: ReactNode;
}

/** Extract plain text from React children tree for clipboard copy. */
function extractText(node: ReactNode): string {
  if (typeof node === "string") return node;
  if (typeof node === "number") return String(node);
  if (node == null || typeof node === "boolean") return "";
  if (Array.isArray(node)) return node.map(extractText).join("");
  if (typeof node === "object" && "props" in node) {
    return extractText((node as React.ReactElement).props.children as ReactNode);
  }
  return "";
}

export function ChatCodeBlock({ language, children }: ChatCodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    const text = extractText(children);
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => { /* non-HTTPS or denied */ });
  }, [children]);

  const displayLang = language || "CODE";

  return (
    <div className="rounded-md border border-[var(--paper-border)] overflow-hidden my-2">
      {/* Header bar */}
      <div className="flex items-center justify-between px-3 py-1.5 bg-[var(--paper-deep)] border-b border-[var(--paper-border)]">
        <span className="text-[10px] font-medium text-[var(--muted-foreground)] uppercase tracking-wider select-none">
          {displayLang}
        </span>
        <button
          type="button"
          onClick={handleCopy}
          className="flex items-center gap-1 text-[var(--muted-foreground)] hover:text-[var(--cyan-mid)] transition-colors"
          aria-label="复制代码"
        >
          {copied ? (
            <Check className="h-3.5 w-3.5 text-[var(--success)]" />
          ) : (
            <Copy className="h-3.5 w-3.5" />
          )}
        </button>
      </div>

      {/* Code area */}
      <div className="overflow-y-auto max-h-[300px] bg-[var(--paper)]/80">
        <pre className="p-3 m-0">
          <code className="font-mono text-[13px] leading-relaxed">
            {children}
          </code>
        </pre>
      </div>
    </div>
  );
}
