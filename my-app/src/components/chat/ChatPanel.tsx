import { useCallback, useEffect, useRef, useState } from "react";
import { useChatContext } from "@/contexts/ChatContext";
import { useChat } from "@/hooks/useChat";
import { ConversationList } from "./ConversationList";
import { MessageBubble } from "./MessageBubble";
import { TokenBar } from "./TokenBar";
import { ChatInput } from "./ChatInput";
import { cn } from "@/lib/utils";
import {
  Sheet,
  SheetContent,
  SheetTitle,
} from "@/components/ui/sheet";
import {
  MessageSquare,
  ChevronRight,
  ChevronLeft,
  List,
} from "lucide-react";
import { StreamingBlockDisplay } from "./StreamingBlockDisplay";
import type { Message, ToolResultBlock, StreamingBlock } from "@/types/assistant";

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build a lookup map from tool_call_id → {result, isError} from "tool" role messages */
function buildToolResultsMap(
  messages: Message[],
): Map<string, { result: string; isError: boolean }> {
  const map = new Map<string, { result: string; isError: boolean }>();
  for (const msg of messages) {
    if (msg.role !== "tool") continue;
    for (const block of msg.content) {
      if (block.type === "tool_result") {
        const tr = block as ToolResultBlock;
        map.set(tr.tool_call_id, { result: tr.content, isError: tr.is_error });
      }
    }
  }
  return map;
}

// ---------------------------------------------------------------------------
// Panel header
// ---------------------------------------------------------------------------

interface PanelHeaderProps {
  showList: boolean;
  onToggleList: () => void;
  onClose: () => void;
}

function PanelHeader({ showList, onToggleList, onClose }: PanelHeaderProps) {
  return (
    <div className="flex items-center gap-2 px-4 py-3 border-b border-[var(--paper-border)]">
      <button
        type="button"
        onClick={onToggleList}
        className={cn(
          "p-1 rounded-md text-[var(--muted-foreground)]",
          "hover:text-foreground hover:bg-[var(--paper-warm)]",
          "focus-visible:ring-2 focus-visible:ring-[var(--cyan-mid)]/10",
          "transition-colors",
        )}
        aria-label={showList ? "隐藏对话列表" : "显示对话列表"}
      >
        <List className="h-4 w-4" />
      </button>
      <MessageSquare className="h-4 w-4 text-[var(--cyan-mid)]" />
      <span className="font-heading text-sm font-medium text-foreground flex-1">
        AI 助教
      </span>
      <button
        type="button"
        onClick={onClose}
        className={cn(
          "p-1 rounded-md text-[var(--muted-foreground)]",
          "hover:text-foreground hover:bg-[var(--paper-warm)]",
          "focus-visible:ring-2 focus-visible:ring-[var(--cyan-mid)]/10",
          "transition-colors",
        )}
        aria-label="收起面板"
      >
        <ChevronRight className="h-4 w-4" />
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Message area
// ---------------------------------------------------------------------------

interface MessageAreaProps {
  messages: Message[];
  isStreaming: boolean;
  isPendingAnswer: boolean;
  onAnswer: (answer: string) => void;
  streamingBlocks: StreamingBlock[];
}

function MessageArea({ messages, isStreaming, isPendingAnswer, onAnswer, streamingBlocks }: MessageAreaProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const [userScrolled, setUserScrolled] = useState(false);

  // Auto-scroll to bottom when new messages arrive (unless user manually scrolled up)
  useEffect(() => {
    if (userScrolled) return;
    const el = scrollRef.current;
    if (el) {
      el.scrollTop = el.scrollHeight;
    }
  }, [messages, streamingBlocks, userScrolled]);

  const handleScroll = useCallback(() => {
    const el = scrollRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setUserScrolled(distanceFromBottom > 60);
  }, []);

  const toolResults = buildToolResultsMap(messages);

  return (
    <div
      ref={scrollRef}
      onScroll={handleScroll}
      className="flex-1 overflow-y-auto px-3 py-3"
    >
      {messages.length === 0 && (
        <div className="flex flex-col items-center justify-center h-full text-center text-[var(--muted-foreground)]">
          <MessageSquare className="h-10 w-10 mb-3 opacity-30" />
          <p className="text-sm">开始与 AI 助教对话</p>
          <p className="text-xs mt-1">输入消息或选择已有对话</p>
        </div>
      )}

      {messages.map((msg) => (
        <MessageBubble
          key={msg.id}
          message={msg}
          toolResults={toolResults}
          isStreaming={false}
          onAnswer={onAnswer}
          isPendingAnswer={isPendingAnswer}
        />
      ))}

      {isStreaming && streamingBlocks.length > 0 && (
        <StreamingBlockDisplay blocks={streamingBlocks} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Panel content (shared between desktop inline & mobile sheet)
// ---------------------------------------------------------------------------

function PanelContent({ onClose }: { onClose: () => void }) {
  const { state } = useChatContext();
  const {
    sendMessage,
    answerQuestion,
    stopGeneration,
    loadConversations,
    selectConversation,
    createConversation,
    deleteConversation,
    uploadFile,
    removeAttachment,
  } = useChat();

  const [showList, setShowList] = useState(!state.activeConversationId);
  const loadedRef = useRef(false);

  // Load conversations on first render
  useEffect(() => {
    if (!loadedRef.current) {
      loadedRef.current = true;
      loadConversations();
    }
  }, [loadConversations]);

  const handleSelectConversation = useCallback(
    (id: string) => {
      selectConversation(id);
      setShowList(false);
    },
    [selectConversation],
  );

  const handleCreateConversation = useCallback(async () => {
    await createConversation();
    setShowList(false);
  }, [createConversation]);

  const handleSend = useCallback(
    (content: string) => {
      if (state.isPendingAnswer) {
        answerQuestion(content);
      } else {
        sendMessage(content);
      }
    },
    [state.isPendingAnswer, answerQuestion, sendMessage],
  );

  return (
    <div className="flex flex-col h-full bg-background">
      <PanelHeader
        showList={showList}
        onToggleList={() => setShowList((prev) => !prev)}
        onClose={onClose}
      />

      {showList ? (
        <div className="flex-1 overflow-y-auto py-2">
          <ConversationList
            conversations={state.conversations}
            activeId={state.activeConversationId}
            onSelect={handleSelectConversation}
            onCreate={handleCreateConversation}
            onDelete={deleteConversation}
          />
        </div>
      ) : (
        <>
          <MessageArea
            messages={state.messages}
            isStreaming={state.isStreaming}
            isPendingAnswer={state.isPendingAnswer}
            onAnswer={answerQuestion}
            streamingBlocks={state.streamingBlocks}
          />

          {state.tokenUsage.total > 0 && (
            <TokenBar usage={state.tokenUsage} />
          )}

          <ChatInput
            onSend={handleSend}
            onStop={stopGeneration}
            onUpload={uploadFile}
            onRemoveFile={removeAttachment}
            attachedFiles={state.attachedFiles}
            isStreaming={state.isStreaming}
            isPendingAnswer={state.isPendingAnswer}
            disabled={!state.activeConversationId || (state.isStreaming && !state.isPendingAnswer)}
          />
        </>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// ChatPanel — responsive wrapper
// ---------------------------------------------------------------------------

export function ChatPanel() {
  const { isPanelOpen, closePanel } = useChatContext();

  return (
    <>
      {/* Desktop: inline panel (lg and up) */}
      <div
        className={cn(
          "hidden lg:flex flex-col border-l border-[var(--paper-border)] transition-all duration-300 ease-in-out overflow-hidden",
          isPanelOpen
            ? "xl:w-[360px] lg:w-[320px] opacity-100"
            : "w-0 opacity-0",
        )}
        style={{ minHeight: 0 }}
      >
        {isPanelOpen && <PanelContent onClose={closePanel} />}
      </div>

      {/* Mobile: sheet mode (below lg) */}
      <div className="lg:hidden">
        <Sheet open={isPanelOpen} onOpenChange={(open) => !open && closePanel()}>
          <SheetContent
            side="right"
            className="w-full sm:w-[400px] p-0"
            showCloseButton={false}
          >
            <SheetTitle className="sr-only">AI 助教</SheetTitle>
            <PanelContent onClose={closePanel} />
          </SheetContent>
        </Sheet>
      </div>
    </>
  );
}
