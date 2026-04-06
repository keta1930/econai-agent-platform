import { useState } from "react";
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
  const [renamingId, setRenamingId] = useState<string | null>(null);
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

  async function handleDownload(backup: BackupInfo) {
    try {
      await backupsApi.download(backup.id, `${backup.display_name}.json`);
    } catch {
      // Silently fail — user can retry
    }
  }

  function startRename(backup: BackupInfo) {
    setRenamingId(backup.id);
    setRenameValue(backup.display_name);
  }

  async function handleRename(id: string) {
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
        <div className="flex items-center gap-6">
          <h1 className="text-2xl font-heading font-semibold page-title-decorated">数据备份</h1>
          {!loading && backups.length > 0 && (
            <span className="text-sm text-muted-foreground">共 {backups.length} 份备份</span>
          )}
        </div>
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
        <>
          <table className="data-table">
            <thead>
              <tr>
                <th>备份名称</th>
                <th>大小</th>
                <th>创建时间</th>
                <th className="text-right">操作</th>
              </tr>
            </thead>
            <tbody>
              {backups.map((backup) => (
                <tr key={backup.id}>
                  <td>
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
                  </td>
                  <td className="text-muted-foreground">
                    {formatFileSize(backup.size)}
                  </td>
                  <td className="text-muted-foreground">
                    {formatDate(backup.created_at, {
                      hour: "2-digit",
                      minute: "2-digit",
                      second: "2-digit",
                    })}
                  </td>
                  <td className="text-right">
                    <div className="flex items-center justify-end gap-2">
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleDownload(backup)}
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
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}

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
