const DATE_DEFAULTS: Intl.DateTimeFormatOptions = {
  year: "numeric",
  month: "2-digit",
  day: "2-digit",
}

export function formatDate(
  iso: string,
  options?: Intl.DateTimeFormatOptions,
): string {
  return new Date(iso).toLocaleDateString("zh-CN", {
    ...DATE_DEFAULTS,
    ...options,
  })
}

export function scoreColor(score: number | null): string {
  if (score === null) return ""
  if (score >= 80) return "text-success font-medium"
  if (score >= 60) return "text-warning font-medium"
  return "text-destructive font-medium"
}

export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}
