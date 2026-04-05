import { useCallback, useRef, useState, type DragEvent, type KeyboardEvent } from "react";
import { cn } from "@/lib/utils";
import { Paperclip, Send, Square, X } from "lucide-react";
import type { UploadedFile } from "@/types/assistant";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const ACCEPTED_TYPES = ".xlsx,.xls,.csv";
const ACCEPTED_MIME = new Set([
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.ms-excel",
  "text/csv",
]);
const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10 MB

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface ChatInputProps {
  onSend: (content: string) => void;
  onStop: () => void;
  onUpload: (file: File) => Promise<UploadedFile>;
  onRemoveFile: (fileId: string) => void;
  attachedFiles: UploadedFile[];
  isStreaming: boolean;
  isPendingAnswer: boolean;
  disabled: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function ChatInput({
  onSend,
  onStop,
  onUpload,
  onRemoveFile,
  attachedFiles,
  isStreaming,
  isPendingAnswer,
  disabled,
}: ChatInputProps) {
  const [text, setText] = useState("");
  const [isDragOver, setIsDragOver] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // ---- Auto-resize textarea ----
  const adjustHeight = useCallback(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, []);

  // ---- Submit logic ----
  const handleSubmit = useCallback(() => {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText("");
    // Reset textarea height after sending
    requestAnimationFrame(() => {
      if (textareaRef.current) {
        textareaRef.current.style.height = "auto";
      }
    });
  }, [text, disabled, onSend]);

  const handleKeyDown = useCallback(
    (e: KeyboardEvent<HTMLTextAreaElement>) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  // ---- File handling ----
  const processFile = useCallback(
    async (file: File) => {
      setUploadError(null);

      if (!ACCEPTED_MIME.has(file.type) && !file.name.match(/\.(xlsx|xls|csv)$/i)) {
        setUploadError("仅支持 .xlsx、.xls、.csv 格式");
        return;
      }
      if (file.size > MAX_FILE_SIZE) {
        setUploadError("文件大小不能超过 10MB");
        return;
      }

      try {
        await onUpload(file);
      } catch {
        setUploadError("文件上传失败，请重试");
      }
    },
    [onUpload],
  );

  const handleFileSelect = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleFileChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const file = e.target.files?.[0];
      if (file) processFile(file);
      // Reset so the same file can be re-selected
      e.target.value = "";
    },
    [processFile],
  );

  // ---- Drag & drop ----
  const handleDragOver = useCallback((e: DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      setIsDragOver(false);
      const file = e.dataTransfer.files[0];
      if (file) processFile(file);
    },
    [processFile],
  );

  // ---- Placeholder ----
  const placeholder = isPendingAnswer
    ? "回答助教的问题..."
    : "输入消息...";

  return (
    <div
      className={cn(
        "border-t border-[var(--paper-border)] bg-background",
        isDragOver && "ring-2 ring-[var(--cyan-mid)]/20",
      )}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
    >
      {/* File attachments */}
      {attachedFiles.length > 0 && (
        <div className="flex flex-wrap gap-1.5 px-3 pt-2">
          {attachedFiles.map((f) => (
            <span
              key={f.file_id}
              className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded bg-[var(--paper-warm)] border border-[var(--paper-border)] text-foreground"
            >
              {f.filename}
              <button
                type="button"
                onClick={() => onRemoveFile(f.file_id)}
                className="text-[var(--muted-foreground)] hover:text-[var(--danger)]"
                aria-label="移除附件"
              >
                <X className="h-3 w-3" />
              </button>
            </span>
          ))}
        </div>
      )}

      {/* Upload error */}
      {uploadError && (
        <p className="text-[11px] text-[var(--danger)] px-3 pt-1.5">{uploadError}</p>
      )}

      {/* Input row */}
      <div className="flex items-end gap-2 px-3 py-2">
        {/* Attach button */}
        <button
          type="button"
          onClick={handleFileSelect}
          disabled={isStreaming}
          className={cn(
            "shrink-0 p-1.5 rounded-md text-[var(--muted-foreground)]",
            "hover:text-foreground hover:bg-[var(--paper-warm)]",
            "focus-visible:border-[var(--cyan-mid)] focus-visible:ring-2 focus-visible:ring-[var(--cyan-mid)]/10",
            "transition-colors",
            isStreaming && "opacity-50 cursor-not-allowed",
          )}
          aria-label="添加附件"
        >
          <Paperclip className="h-4 w-4" />
        </button>
        <input
          ref={fileInputRef}
          type="file"
          accept={ACCEPTED_TYPES}
          className="hidden"
          onChange={handleFileChange}
        />

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={text}
          onChange={(e) => {
            setText(e.target.value);
            adjustHeight();
          }}
          onKeyDown={handleKeyDown}
          placeholder={placeholder}
          disabled={disabled}
          rows={1}
          className={cn(
            "flex-1 resize-none rounded-md border border-[var(--paper-border)] bg-white px-3 py-2",
            "text-sm text-foreground placeholder:text-[var(--muted-foreground)]",
            "focus-visible:border-[var(--cyan-mid)] focus-visible:ring-2 focus-visible:ring-[var(--cyan-mid)]/10",
            "focus-visible:outline-none",
            "disabled:opacity-50 disabled:cursor-not-allowed",
            "transition-colors",
          )}
          style={{ maxHeight: 160, minHeight: 36 }}
        />

        {/* Send / Stop button */}
        {isStreaming ? (
          <button
            type="button"
            onClick={onStop}
            className={cn(
              "shrink-0 p-1.5 rounded-md",
              "bg-[var(--danger)] text-white",
              "hover:bg-[var(--danger)]/90",
              "focus-visible:border-destructive/40 focus-visible:ring-2 focus-visible:ring-destructive/10",
              "transition-colors",
            )}
            aria-label="停止生成"
          >
            <Square className="h-4 w-4" />
          </button>
        ) : (
          <button
            type="button"
            onClick={handleSubmit}
            disabled={!text.trim() || disabled}
            className={cn(
              "shrink-0 p-1.5 rounded-md",
              "bg-[var(--ink-deep)] text-[var(--text-on-dark)]",
              "hover:bg-[var(--ink-mid)]",
              "focus-visible:border-[var(--cyan-mid)] focus-visible:ring-2 focus-visible:ring-[var(--cyan-mid)]/10",
              "transition-colors",
              (!text.trim() || disabled) && "opacity-50 cursor-not-allowed",
            )}
            aria-label="发送消息"
          >
            <Send className="h-4 w-4" />
          </button>
        )}
      </div>
    </div>
  );
}
