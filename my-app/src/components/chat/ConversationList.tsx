import { cn } from "@/lib/utils";
import { Plus, Trash2 } from "lucide-react";
import type { Conversation } from "@/types/assistant";

interface ConversationListProps {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onDelete: (id: string) => void;
}

function formatRelativeTime(iso: string): string {
  const diff = Date.now() - new Date(iso).getTime();
  const minutes = Math.floor(diff / 60_000);
  if (minutes < 1) return "刚刚";
  if (minutes < 60) return `${minutes}分钟前`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}小时前`;
  const days = Math.floor(hours / 24);
  if (days < 30) return `${days}天前`;
  return new Date(iso).toLocaleDateString("zh-CN");
}

export function ConversationList({
  conversations,
  activeId,
  onSelect,
  onCreate,
  onDelete,
}: ConversationListProps) {
  return (
    <div className="flex flex-col">
      {/* New conversation button */}
      <button
        type="button"
        onClick={onCreate}
        className={cn(
          "flex items-center gap-2 mx-3 mb-2 px-3 py-2 text-sm rounded-md border border-dashed",
          "border-[var(--paper-border)] text-[var(--muted-foreground)]",
          "hover:border-[var(--cyan-mid)] hover:text-[var(--cyan-mid)] hover:bg-[var(--paper-warm)]",
          "transition-colors",
          "focus-visible:border-[var(--cyan-mid)] focus-visible:ring-2 focus-visible:ring-[var(--cyan-mid)]/10",
        )}
      >
        <Plus className="h-4 w-4" />
        新建对话
      </button>

      {/* Conversation items */}
      <div className="flex-1 overflow-y-auto px-3 space-y-1">
        {conversations.map((conv) => {
          const isActive = conv.id === activeId;
          return (
            <div
              key={conv.id}
              className={cn(
                "group flex items-center gap-2 rounded-md px-3 py-2 cursor-pointer transition-colors",
                isActive
                  ? "bg-[var(--cyan-mid)]/[0.06] border border-[var(--cyan-mid)]/30"
                  : "border border-transparent hover:bg-[var(--paper-warm)]",
              )}
              onClick={() => onSelect(conv.id)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") onSelect(conv.id);
              }}
            >
              <div className="flex-1 min-w-0">
                <div className="text-sm truncate text-foreground">
                  {conv.title ?? "新对话"}
                </div>
                <div className="text-[11px] text-[var(--muted-foreground)]">
                  {formatRelativeTime(conv.updated_at)}
                </div>
              </div>
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(conv.id);
                }}
                className={cn(
                  "shrink-0 p-1 rounded opacity-0 group-hover:opacity-100 transition-opacity",
                  "text-[var(--muted-foreground)] hover:text-[var(--danger)] hover:bg-[var(--danger)]/10",
                  "focus-visible:opacity-100 focus-visible:ring-2 focus-visible:ring-[var(--cyan-mid)]/10",
                )}
                aria-label="删除对话"
              >
                <Trash2 className="h-3.5 w-3.5" />
              </button>
            </div>
          );
        })}

        {conversations.length === 0 && (
          <p className="text-center text-[var(--muted-foreground)] text-sm py-8">
            暂无对话
          </p>
        )}
      </div>
    </div>
  );
}
