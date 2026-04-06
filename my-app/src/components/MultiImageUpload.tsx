import { useRef, useState, useCallback, useEffect, type DragEvent, type ClipboardEvent } from "react";
import { ImageIcon, X, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatFileSize } from "@/lib/format";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const MAX_IMAGES = 10;
const MAX_SINGLE_SIZE = 5 * 1024 * 1024; // 5 MB
const MAX_TOTAL_SIZE = 50 * 1024 * 1024; // 50 MB
const ACCEPTED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".webp"];
const ACCEPT_STRING = ACCEPTED_EXTENSIONS.join(",");

function isValidImage(file: File): boolean {
  return ACCEPTED_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext));
}

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface MultiImageUploadProps {
  onFilesChange: (files: File[]) => void;
  disabled?: boolean;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function MultiImageUpload({ onFilesChange, disabled }: MultiImageUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [files, setFiles] = useState<File[]>([]);
  const [previewUrls, setPreviewUrls] = useState<string[]>([]);
  const [errors, setErrors] = useState<string[]>([]);
  const [dragOver, setDragOver] = useState(false);

  // Revoke all ObjectURLs on unmount
  useEffect(() => {
    return () => {
      previewUrls.forEach((url) => URL.revokeObjectURL(url));
    };
    // Only on unmount
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const totalSize = files.reduce((sum, f) => sum + f.size, 0);
  const isFull = files.length >= MAX_IMAGES;

  const handleFiles = useCallback(
    (newFileList: FileList | File[]) => {
      const incoming = Array.from(newFileList);
      const newErrors: string[] = [];
      const accepted: File[] = [];

      for (const file of incoming) {
        if (!isValidImage(file)) {
          newErrors.push(`${file.name}: 不支持的格式，仅支持 ${ACCEPTED_EXTENSIONS.join("、")}`);
          continue;
        }
        if (file.size > MAX_SINGLE_SIZE) {
          newErrors.push(`${file.name}: 超过单张 ${formatFileSize(MAX_SINGLE_SIZE)} 限制`);
          continue;
        }
        accepted.push(file);
      }

      setFiles((prev) => {
        const remaining = MAX_IMAGES - prev.length;
        if (remaining <= 0) {
          newErrors.push(`最多上传 ${MAX_IMAGES} 张图片`);
          setErrors(newErrors);
          return prev;
        }

        const toAdd: File[] = [];
        let currentTotal = prev.reduce((s, f) => s + f.size, 0);

        for (const file of accepted.slice(0, remaining)) {
          if (currentTotal + file.size > MAX_TOTAL_SIZE) {
            newErrors.push(`${file.name}: 总大小超过 ${formatFileSize(MAX_TOTAL_SIZE)} 限制`);
            continue;
          }
          currentTotal += file.size;
          toAdd.push(file);
        }

        if (accepted.length > remaining) {
          newErrors.push(`已忽略 ${accepted.length - remaining} 张图片（超出上限）`);
        }

        setErrors(newErrors);

        if (toAdd.length === 0) return prev;

        const updated = [...prev, ...toAdd];
        const newUrls = toAdd.map((f) => URL.createObjectURL(f));
        setPreviewUrls((urls) => [...urls, ...newUrls]);
        onFilesChange(updated);
        return updated;
      });
    },
    [onFilesChange],
  );

  const removeFile = useCallback(
    (index: number) => {
      setFiles((prev) => {
        const updated = prev.filter((_, i) => i !== index);
        onFilesChange(updated);
        return updated;
      });
      setPreviewUrls((prev) => {
        URL.revokeObjectURL(prev[index]);
        return prev.filter((_, i) => i !== index);
      });
      setErrors([]);
    },
    [onFilesChange],
  );

  const handleDrop = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      if (disabled) return;
      handleFiles(e.dataTransfer.files);
    },
    [disabled, handleFiles],
  );

  const handleDragOver = useCallback(
    (e: DragEvent) => {
      e.preventDefault();
      if (!disabled) setDragOver(true);
    },
    [disabled],
  );

  const handleDragLeave = useCallback((e: DragEvent) => {
    e.preventDefault();
    setDragOver(false);
  }, []);

  const handlePaste = useCallback(
    (e: ClipboardEvent) => {
      if (disabled) return;
      const items = e.clipboardData?.items;
      if (!items) return;
      const imageFiles: File[] = [];
      for (const item of items) {
        if (item.type.startsWith("image/")) {
          const file = item.getAsFile();
          if (file) imageFiles.push(file);
        }
      }
      if (imageFiles.length > 0) {
        e.preventDefault();
        handleFiles(imageFiles);
      }
    },
    [disabled, handleFiles],
  );

  return (
    <div className="space-y-3" onPaste={handlePaste} tabIndex={0}>
      {/* Thumbnail grid */}
      {files.length > 0 && (
        <div className="grid grid-cols-5 gap-2">
          {files.map((file, i) => (
            <div
              key={`${file.name}-${file.size}-${i}`}
              className="group relative rounded-md border border-[var(--paper-border)] bg-[var(--paper-warm)] overflow-hidden"
            >
              <img
                src={previewUrls[i]}
                alt={file.name}
                className="aspect-square w-full object-cover"
              />
              <button
                type="button"
                onClick={() => removeFile(i)}
                disabled={disabled}
                className={cn(
                  "absolute top-1 right-1 rounded-full p-0.5",
                  "bg-[var(--destructive)] text-white",
                  "opacity-0 group-hover:opacity-100 transition-opacity",
                  "hover:bg-[var(--destructive)]/90",
                  disabled && "hidden",
                )}
                aria-label={`移除 ${file.name}`}
              >
                <X className="h-3 w-3" />
              </button>
              <div className="absolute bottom-0 inset-x-0 bg-black/50 px-1.5 py-0.5">
                <p className="text-[10px] text-white truncate">{file.name}</p>
                <p className="text-[9px] text-white/70">{formatFileSize(file.size)}</p>
              </div>
            </div>
          ))}

          {/* Add more button (inline in grid) */}
          {!isFull && !disabled && (
            <button
              type="button"
              onClick={() => inputRef.current?.click()}
              className={cn(
                "flex flex-col items-center justify-center gap-1",
                "aspect-square rounded-md border-2 border-dashed border-[var(--paper-border)]",
                "text-[var(--muted-foreground)] hover:border-[var(--cyan-light)] hover:text-[var(--cyan-mid)]",
                "transition-colors cursor-pointer",
              )}
            >
              <Plus className="h-5 w-5" />
              <span className="text-[10px]">添加</span>
            </button>
          )}
        </div>
      )}

      {/* Drop zone (shown when no images yet, or as a supplementary area) */}
      {files.length === 0 && (
        <div
          onClick={() => !disabled && inputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={cn(
            "flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors cursor-pointer",
            dragOver
              ? "border-[var(--cyan-light)] bg-[var(--cyan-light)]/5"
              : "border-[var(--paper-border)]",
            disabled && "opacity-50 cursor-not-allowed",
          )}
        >
          <ImageIcon className="h-8 w-8 text-[var(--muted-foreground)]" />
          <p className="text-sm text-[var(--muted-foreground)]">
            拖拽或粘贴图片到此处，或
            <span className="text-[var(--cyan-mid)] font-medium">点击选择</span>
          </p>
          <p className="text-xs text-[var(--muted-foreground)]">
            支持 {ACCEPTED_EXTENSIONS.join("、")} 格式，最多 {MAX_IMAGES} 张
          </p>
        </div>
      )}

      {/* Drop zone overlay when images exist */}
      {files.length > 0 && !isFull && (
        <div
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={handleDragLeave}
          className={cn(
            "rounded-lg border-2 border-dashed p-3 text-center transition-colors",
            dragOver
              ? "border-[var(--cyan-light)] bg-[var(--cyan-light)]/5"
              : "border-[var(--paper-border)]",
          )}
        >
          <p className="text-xs text-[var(--muted-foreground)]">
            拖拽更多图片到此处
          </p>
        </div>
      )}

      {/* Status bar */}
      {files.length > 0 && (
        <p className="text-xs text-[var(--muted-foreground)]">
          已选 {files.length}/{MAX_IMAGES} 张，共 {formatFileSize(totalSize)} / {formatFileSize(MAX_TOTAL_SIZE)}
        </p>
      )}

      {/* Errors */}
      {errors.length > 0 && (
        <div className="space-y-0.5">
          {errors.map((err, i) => (
            <p key={i} className="text-xs text-[var(--destructive)]">{err}</p>
          ))}
        </div>
      )}

      {/* Hidden file input */}
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT_STRING}
        multiple
        className="hidden"
        disabled={disabled}
        onChange={(e) => {
          if (e.target.files) handleFiles(e.target.files);
          e.target.value = "";
        }}
      />
    </div>
  );
}
