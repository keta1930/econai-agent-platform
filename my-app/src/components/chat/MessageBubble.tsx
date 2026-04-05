import type { Message, Block, ToolUseBlock, ToolResultBlock } from "@/types/assistant";
import { MarkdownContent } from "@/components/ui/markdown-content";
import { ToolCallCard } from "./ToolCallCard";
import { AskUserCard } from "./AskUserCard";
import { cn } from "@/lib/utils";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface MessageBubbleProps {
  message: Message;
  /** Tool results keyed by tool_call_id — sourced from subsequent "tool" role messages */
  toolResults: Map<string, { result: string; isError: boolean }>;
  /** Whether the assistant is still streaming this message */
  isStreaming: boolean;
  onAnswer: (answer: string) => void;
  isPendingAnswer: boolean;
}

// ---------------------------------------------------------------------------
// Streaming indicator
// ---------------------------------------------------------------------------

function StreamingIndicator() {
  return (
    <span className="inline-flex items-center gap-0.5 ml-1" aria-label="typing">
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

// ---------------------------------------------------------------------------
// Block renderers
// ---------------------------------------------------------------------------

function renderBlock(
  block: Block,
  index: number,
  toolResults: Map<string, { result: string; isError: boolean }>,
  onAnswer: (answer: string) => void,
  isPendingAnswer: boolean,
) {
  switch (block.type) {
    case "text":
      return block.text ? (
        <MarkdownContent
          key={index}
          content={block.text}
          className="text-sm [&_p]:leading-relaxed"
        />
      ) : null;

    case "tool_use": {
      const toolBlock = block as ToolUseBlock;

      // ask_user tool_use gets special card
      if (toolBlock.name === "ask_user") {
        const input = toolBlock.input as {
          question?: string;
          options?: (string | { label: string; description?: string })[];
          select_mode?: "single" | "multiple";
        };
        const answered = toolResults.has(toolBlock.tool_call_id);
        const tr = toolResults.get(toolBlock.tool_call_id);
        return (
          <AskUserCard
            key={index}
            question={input.question ?? ""}
            options={input.options}
            selectMode={input.select_mode}
            onAnswer={onAnswer}
            disabled={answered || !isPendingAnswer}
            selectedAnswer={tr?.result}
          />
        );
      }

      // Regular tool call card
      const tr = toolResults.get(toolBlock.tool_call_id);
      let status: "running" | "complete" | "error" = "running";
      if (tr) {
        status = tr.isError ? "error" : "complete";
      }

      return (
        <ToolCallCard
          key={index}
          name={toolBlock.name}
          args={toolBlock.input}
          result={tr?.result}
          isError={tr?.isError}
          status={status}
        />
      );
    }

    // tool_result and file blocks are not rendered directly in the bubble
    case "tool_result":
    case "file":
      return null;
  }
}

// ---------------------------------------------------------------------------
// MessageBubble
// ---------------------------------------------------------------------------

export function MessageBubble({
  message,
  toolResults,
  isStreaming,
  onAnswer,
  isPendingAnswer,
}: MessageBubbleProps) {
  // "tool" role messages are consumed by the assistant bubble via toolResults map
  if (message.role === "tool" || message.role === "system") {
    return null;
  }

  const isUser = message.role === "user";

  // File blocks in user messages
  const fileBlocks = isUser
    ? message.content.filter((b): b is Extract<Block, { type: "file" }> => b.type === "file")
    : [];

  return (
    <div className={cn("flex mb-3", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[85%] rounded-lg px-3 py-2",
          isUser
            ? "bg-[var(--ink-deep)] text-[var(--text-on-dark)]"
            : "bg-white border border-[var(--paper-border)] text-foreground shadow-[var(--shadow-sm)]",
        )}
      >
        {/* User file attachments */}
        {fileBlocks.length > 0 && (
          <div className="flex flex-wrap gap-1.5 mb-1.5">
            {fileBlocks.map((f) => (
              <span
                key={f.file_id}
                className="inline-flex items-center gap-1 text-[11px] px-2 py-0.5 rounded bg-white/15"
              >
                {f.filename}
              </span>
            ))}
          </div>
        )}

        {/* Content blocks */}
        {message.content.map((block, i) =>
          renderBlock(block, i, toolResults, onAnswer, isPendingAnswer),
        )}

        {/* Streaming indicator */}
        {isStreaming && !isUser && message.id === "__streaming__" && (
          <StreamingIndicator />
        )}
      </div>
    </div>
  );
}
