import { MarkdownContent } from "@/components/ui/markdown-content";
import { ToolCallCard } from "./ToolCallCard";
import type { StreamingBlock } from "@/types/assistant";

// ---------------------------------------------------------------------------
// StreamingBlockDisplay — renders the streaming block array during SSE
// ---------------------------------------------------------------------------

interface StreamingBlockDisplayProps {
  blocks: StreamingBlock[];
}

export function StreamingBlockDisplay({ blocks }: StreamingBlockDisplayProps) {
  return (
    <div className="flex justify-start mb-3">
      <div className="max-w-[85%] rounded-lg px-3 py-2 bg-white border border-[var(--paper-border)] text-foreground">
        {blocks.map((block) => (
          <StreamingBlockRenderer key={block.id} block={block} />
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Per-block renderer — dispatches by block type
// ---------------------------------------------------------------------------

function StreamingBlockRenderer({ block }: { block: StreamingBlock }) {
  switch (block.type) {
    case "content":
      return <ContentBlock content={block.content} isComplete={block.isComplete} />;

    case "tool_calls":
      return <ToolCallsBlock block={block} />;

    case "reasoning":
      return <ReasoningBlock content={block.content} />;
  }
}

// ---------------------------------------------------------------------------
// Content block — markdown + streaming cursor
// ---------------------------------------------------------------------------

function ContentBlock({ content, isComplete }: { content: string; isComplete: boolean }) {
  if (!content && !isComplete) {
    return (
      <span className="inline-flex items-center gap-0.5" aria-label="typing">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="inline-block h-1.5 w-1.5 rounded-full bg-[var(--cyan-mid)] animate-pulse"
            style={{ animationDelay: `${i * 0.2}s` }}
          />
        ))}
      </span>
    );
  }

  // Append streaming cursor while content is still being received
  const displayContent = isComplete ? content : content + " ▋";

  return (
    <MarkdownContent
      content={displayContent}
      className="text-sm [&_p]:leading-relaxed"
    />
  );
}

// ---------------------------------------------------------------------------
// Tool calls block — renders each tool call as a card
// ---------------------------------------------------------------------------

function ToolCallsBlock({ block }: { block: StreamingBlock }) {
  if (!block.toolCalls?.length) return null;

  return (
    <div className="space-y-1">
      {block.toolCalls.map((tc) => {
        let status: "running" | "complete" | "error" = "running";
        if (tc.result !== undefined) {
          status = tc.isError ? "error" : "complete";
        }

        return (
          <ToolCallCard
            key={tc.id}
            name={tc.name || tc.displayName}
            args={tc.args}
            result={tc.result}
            isError={tc.isError}
            status={status}
          />
        );
      })}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Reasoning block — collapsible panel (reserved for future SSE reasoning events)
// ---------------------------------------------------------------------------

function ReasoningBlock({ content }: { content: string }) {
  if (!content) return null;

  return (
    <details className="text-xs text-[var(--muted-foreground)] my-1">
      <summary className="cursor-pointer select-none">推理过程</summary>
      <pre className="mt-1 whitespace-pre-wrap break-all text-[11px] bg-[var(--paper-deep)] rounded p-2">
        {content}
      </pre>
    </details>
  );
}
