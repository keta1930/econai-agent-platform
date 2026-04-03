import { useRef, useState, useCallback, useEffect, type DragEvent } from "react";
import { ImageIcon, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { formatFileSize } from "@/lib/format";

const ACCEPTED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".gif", ".webp"];
const MAX_IMAGE_SIZE = 10 * 1024 * 1024; // 10 MB
const ACCEPT_STRING = ACCEPTED_EXTENSIONS.join(",");

function isValidImage(file: File): boolean {
  return ACCEPTED_EXTENSIONS.some((ext) => file.name.toLowerCase().endsWith(ext));
}

interface ImageUploadProps {
  onFileSelect: (file: File) => void;
  onClear?: () => void;
  disabled?: boolean;
}

export function ImageUpload({ onFileSelect, onClear, disabled }: ImageUploadProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [dragOver, setDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [error, setError] = useState("");

  // Clean up object URL on unmount or change
  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  const handleFile = useCallback(
    (file: File) => {
      setError("");
      if (!isValidImage(file)) {
        setError(`仅支持 ${ACCEPTED_EXTENSIONS.join("、")} 格式`);
        return;
      }
      if (file.size > MAX_IMAGE_SIZE) {
        setError(`图片大小超过 ${formatFileSize(MAX_IMAGE_SIZE)} 限制`);
        return;
      }
      if (previewUrl) URL.revokeObjectURL(previewUrl);
      const url = URL.createObjectURL(file);
      setPreviewUrl(url);
      setSelectedFile(file);
      onFileSelect(file);
    },
    [onFileSelect, previewUrl],
  );

  function clearSelection() {
    if (previewUrl) URL.revokeObjectURL(previewUrl);
    setPreviewUrl(null);
    setSelectedFile(null);
    onClear?.();
    if (inputRef.current) inputRef.current.value = "";
  }

  function handleDrop(e: DragEvent) {
    e.preventDefault();
    setDragOver(false);
    if (disabled) return;
    const file = e.dataTransfer.files[0];
    if (file) handleFile(file);
  }

  function handleDragOver(e: DragEvent) {
    e.preventDefault();
    if (!disabled) setDragOver(true);
  }

  return (
    <div>
      {selectedFile && previewUrl ? (
        <div className="relative rounded-lg border p-4">
          <button
            type="button"
            onClick={clearSelection}
            disabled={disabled}
            className="absolute top-2 right-2 rounded-full bg-background/80 p-1 hover:bg-muted transition-colors"
          >
            <X className="h-4 w-4" />
          </button>
          <div className="flex items-start gap-4">
            <img
              src={previewUrl}
              alt="Preview"
              className="h-32 w-32 rounded-md object-cover"
            />
            <div className="flex flex-col gap-1 pt-1">
              <p className="text-sm font-medium">{selectedFile.name}</p>
              <p className="text-xs text-muted-foreground">
                {formatFileSize(selectedFile.size)}
              </p>
            </div>
          </div>
        </div>
      ) : (
        <div
          onClick={() => !disabled && inputRef.current?.click()}
          onDrop={handleDrop}
          onDragOver={handleDragOver}
          onDragLeave={() => setDragOver(false)}
          className={cn(
            "flex flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors cursor-pointer",
            dragOver ? "border-primary bg-primary/5" : "border-border",
            disabled && "opacity-50 cursor-not-allowed",
          )}
        >
          <ImageIcon className="h-8 w-8 text-muted-foreground" />
          <p className="text-sm text-muted-foreground">
            拖拽图片到此处，或<span className="text-primary font-medium">点击选择</span>
          </p>
          <p className="text-xs text-muted-foreground">
            支持 {ACCEPTED_EXTENSIONS.join("、")} 格式（最大 {formatFileSize(MAX_IMAGE_SIZE)}）
          </p>
        </div>
      )}
      {error && <p className="mt-2 text-sm text-destructive">{error}</p>}
      <input
        ref={inputRef}
        type="file"
        accept={ACCEPT_STRING}
        className="hidden"
        disabled={disabled}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handleFile(file);
        }}
      />
    </div>
  );
}
