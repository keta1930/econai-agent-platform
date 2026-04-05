import { useState } from "react";
import { MarkdownContent } from "@/components/ui/markdown-content";
import { ToolCallCard } from "./ToolCallCard";
import { AskUserCard } from "./AskUserCard";
import { useChatContext } from "@/contexts/ChatContext";
import { Brain, ChevronRight } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AskUserQuestion, StreamingBlock } from "@/types/assistant";

// ---------------------------------------------------------------------------
// StreamingBlockDisplay — renders the streaming block array during SSE
// ---------------------------------------------------------------------------

interface StreamingBlockDisplayProps {
  blocks: StreamingBlock[];
  onAnswer: (answer: string) => void;
}

export function StreamingBlockDisplay({ blocks, onAnswer }: StreamingBlockDisplayProps) {
  return (
    <div className="flex justify-start mb-3">
      <div className="max-w-[85%] rounded-lg px-3 py-2 bg-white border border-[var(--paper-border)] text-foreground shadow-[var(--shadow-sm)]">
        {blocks.map((block) => (
          <StreamingBlockRenderer key={block.id} block={block} onAnswer={onAnswer} />
        ))}
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Per-block renderer — dispatches by block type
// ---------------------------------------------------------------------------

function StreamingBlockRenderer({ block, onAnswer }: { block: StreamingBlock; onAnswer: (answer: string) => void }) {
  switch (block.type) {
    case "content":
      return <ContentBlock content={block.content} isComplete={block.isComplete} />;

    case "tool_calls":
      return <ToolCallsBlock block={block} onAnswer={onAnswer} />;

    case "reasoning":
      return <ReasoningBlock content={block.content} />;
  }
}

// ---------------------------------------------------------------------------
// Content block — markdown + streaming cursor
// ---------------------------------------------------------------------------

function StreamingCursor() {
  return (
    <span
      className="inline-block w-[2px] h-[1em] bg-[var(--cyan-mid)] ml-0.5 align-text-bottom animate-cursor-blink"
      aria-hidden="true"
    />
  );
}

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

  return (
    <>
      <MarkdownContent
        content={content}
        className="text-sm [&_p]:leading-relaxed"
      />
      {!isComplete && <StreamingCursor />}
    </>
  );
}

// ---------------------------------------------------------------------------
// Tool calls block — renders each tool call as a card
// ---------------------------------------------------------------------------

function ToolCallsBlock({ block, onAnswer }: { block: StreamingBlock; onAnswer: (answer: string) => void }) {
  const { state } = useChatContext();

  if (!block.toolCalls?.length) return null;

  return (
    <div className="space-y-1">
      {block.toolCalls.map((tc) => {
        // Render ask_user tool calls as an interactive AskUserCard
        if (tc.name === "ask_user") {
          const args = tc.args as {
            question?: string;
            options?: (string | { label: string; description?: string })[];
            select_mode?: "single" | "multiple";
            questions?: AskUserQuestion[];
          };
          // Normalize legacy format to questions array
          const questions: AskUserQuestion[] = args.questions ?? [{
            question: args.question ?? "",
            options: args.options,
            select_mode: args.select_mode,
          }];
          return (
            <AskUserCard
              key={tc.id}
              questions={questions}
              onAnswer={onAnswer}
              disabled={!state.isPendingAnswer}
            />
          );
        }

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
// Reasoning block — collapsible panel with Brain icon + chevron
// ---------------------------------------------------------------------------

function ReasoningBlock({ content }: { content: string }) {
  const [expanded, setExpanded] = useState(false);

  if (!content) return null;

  return (
    <div className="rounded-md border border-[var(--paper-border)] bg-[var(--paper)] my-1 text-xs">
      <button
        type="button"
        onClick={() => setExpanded((prev) => !prev)}
        className="flex w-full items-center gap-2 px-3 py-2 text-left"
      >
        <Brain className="h-3.5 w-3.5 text-[var(--muted-foreground)]" />
        <span className="font-medium text-[var(--muted-foreground)]">推理过程</span>
        <ChevronRight
          className={cn(
            "h-3.5 w-3.5 text-[var(--muted-foreground)] transition-transform ml-auto",
            expanded && "rotate-90",
          )}
        />
      </button>
      {expanded && (
        <div className="border-t border-[var(--paper-border)] px-3 py-2 animate-in fade-in-0 duration-150">
          <pre className="whitespace-pre-wrap break-all text-[11px] text-[var(--muted-foreground)] bg-[var(--paper-deep)] rounded p-2">
            {content}
          </pre>
        </div>
      )}
    </div>
  );
}
