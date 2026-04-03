import { useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { EmptyState } from "@/components/EmptyState";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { useApi } from "@/hooks/useApi";
import { backupsApi } from "@/api/backups";
import { formatDate, formatFileSize } from "@/lib/format";
import { Loader2, Database, Download, Trash2 } from "lucide-react";
import type { BackupInfo } from "@/types/backup";

export default function BackupManagePage() {
  const { data, loading, refetch } = useApi(() => backupsApi.list(), []);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState("");

  // Delete state
  const [deleteTarget, setDeleteTarget] = useState<BackupInfo | null>(null);
  const [deleting, setDeleting] = useState(false);

  async function handleCreate() {
    setCreating(true);
    setCreateError("");
    try {
      await backupsApi.create();
      await refetch();
    } catch (e) {
      setCreateError(e instanceof Error ? e.message : "备份失败");
    } finally {
      setCreating(false);
    }
  }

  async function handleDownload(filename: string) {
    try {
      const res = await backupsApi.getDownloadUrl(filename);
      window.open(res.download_url, "_blank");
    } catch {
      // Silently fail — user can retry
    }
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await backupsApi.delete(deleteTarget.filename);
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
        <Button onClick={handleCreate} disabled={creating}>
          {creating ? (
            <Loader2 className="mr-2 h-4 w-4 animate-spin" />
          ) : (
            <Database className="mr-2 h-4 w-4" />
          )}
          {creating ? "备份中..." : "立即备份"}
        </Button>
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
                  key={backup.filename}
                  className="flex items-center justify-between px-4 py-3 text-sm"
                >
                  <div className="flex flex-col gap-0.5">
                    <span className="font-medium">{backup.filename}</span>
                    <span className="text-xs text-muted-foreground">
                      {formatFileSize(backup.size)} · {formatDate(backup.created_at, {
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
                      onClick={() => handleDownload(backup.filename)}
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
        onOpenChange={(open) => { if (!open) setDeleteTarget(null); }}
        title="删除备份"
        description={`确定要删除备份 ${deleteTarget?.filename ?? ""} 吗？此操作不可撤销。`}
        onConfirm={handleDelete}
        confirmText="删除"
        loading={deleting}
      />
    </div>
  );
}
