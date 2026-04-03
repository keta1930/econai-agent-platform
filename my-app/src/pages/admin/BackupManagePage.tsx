import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { EmptyState } from "@/components/EmptyState";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/hooks/useApi";
import { backupsApi } from "@/api/backups";
import { ApiError } from "@/api/client";
import { formatDate, formatFileSize } from "@/lib/format";
import { Loader2, Database, Download, Trash2, Pencil } from "lucide-react";
import type { BackupInfo } from "@/types/backup";

export default function BackupManagePage() {
  const { data, loading, refetch } = useApi(() => backupsApi.list(), []);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");
  const [customName, setCustomName] = useState("");

  // Inline rename state
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState("");

  // Delete state
  const [deleteTarget, setDeleteTarget] = useState<BackupInfo | null>(null);
  const [deleting, setDeleting] = useState(false);

  async function handleCreate() {
    setCreating(true);
    setCreateError("");
    try {
      await backupsApi.create(customName.trim() || undefined);
      setCustomName("");
      await refetch();
    } catch (e) {
      if (e instanceof ApiError && e.status === 409) {
        setCreateError(e.message);
      } else {
        setCreateError(e instanceof Error ? e.message : "备份失败");
      }
    } finally {
      setCreating(false);
    }
  }

  async function handleDownload(id: number) {
    try {
      const res = await backupsApi.getDownloadUrl(id);
      window.open(res.download_url, "_blank");
    } catch {
      // Silently fail — user can retry
    }
  }

  function startRename(backup: BackupInfo) {
    setRenamingId(backup.id);
    setRenameValue(backup.display_name);
  }

  async function handleRename(id: number) {
    const trimmed = renameValue.trim();
    if (!trimmed) {
      setRenamingId(null);
      return;
    }
    try {
      await backupsApi.rename(id, trimmed);
      setRenamingId(null);
      await refetch();
    } catch {
      // Keep editing on failure
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await backupsApi.delete(deleteTarget.id);
      setDeleteTarget(null);
      await refetch();
    } catch {
      // Keep dialog open for retry
    } finally {
      setDeleting(false);
    }
  }

  const backups = data?.items ?? [];

  return (
    <div className="space-y-6 animate-fade-in-up">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-heading font-semibold">数据库管理</h1>
        <div className="flex items-center gap-2">
          <Input
            className="w-56"
            placeholder="可选，输入备份名称"
            value={customName}
            onChange={(e) => setCustomName(e.target.value)}
            disabled={creating}
          />
          <Button onClick={handleCreate} disabled={creating}>
            {creating ? (
              <Loader2 className="mr-2 h-4 w-4 animate-spin" />
            ) : (
              <Database className="mr-2 h-4 w-4" />
            )}
            {creating ? "备份中..." : "创建备份"}
          </Button>
        </div>
      </div>

      {createError && (
        <p className="text-sm text-destructive">{createError}</p>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-lg">备份列表</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="space-y-3">
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
              <Skeleton className="h-10 w-full" />
            </div>
          ) : backups.length === 0 ? (
            <EmptyState
              icon={<Database className="h-12 w-12" />}
              title="暂无备份"
              description="点击上方按钮创建第一个数据库备份"
            />
          ) : (
            <div className="divide-y rounded-md border">
              {backups.map((backup) => (
                <div
                  key={backup.id}
                  className="flex items-center justify-between px-4 py-3 text-sm"
                >
                  <div className="flex flex-col gap-0.5">
                    {renamingId === backup.id ? (
                      <Input
                        className="h-7 w-56 text-sm"
                        value={renameValue}
                        onChange={(e) => setRenameValue(e.target.value)}
                        onBlur={() => handleRename(backup.id)}
                        onKeyDown={(e) => {
                          if (e.key === "Enter") handleRename(backup.id);
                          if (e.key === "Escape") setRenamingId(null);
                        }}
                        autoFocus
                      />
                    ) : (
                      <span className="flex items-center gap-1.5">
                        <span className="font-medium">
                          {backup.display_name}
                        </span>
                        <button
                          className="text-muted-foreground hover:text-foreground transition-colors"
                          onClick={() => startRename(backup)}
                        >
                          <Pencil className="h-3.5 w-3.5" />
                        </button>
                      </span>
                    )}
                    <span className="text-xs text-muted-foreground">
                      {formatFileSize(backup.size)} ·{" "}
                      {formatDate(backup.created_at, {
                        hour: "2-digit",
                        minute: "2-digit",
                        second: "2-digit",
                      })}
                    </span>
                  </div>
                  <div className="flex items-center gap-2">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDownload(backup.id)}
                    >
                      <Download className="h-4 w-4" />
                    </Button>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setDeleteTarget(backup)}
                    >
                      <Trash2 className="h-4 w-4 text-destructive" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        title="删除备份"
        description={`确定要删除备份「${deleteTarget?.display_name ?? ""}」吗？此操作不可撤销。`}
        onConfirm={handleDelete}
        confirmText="删除"
        loading={deleting}
      />
    </div>
  );
}
