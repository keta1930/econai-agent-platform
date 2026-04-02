import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/EmptyState";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { useApi } from "@/hooks/useApi";
import { tasksApi } from "@/api/tasks";
import { toast } from "sonner";
import { ClipboardList, PlusCircle, Trash2 } from "lucide-react";
import type { Task, TaskStatsResponse } from "@/types/task";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const [deleteTarget, setDeleteTarget] = useState<Task | null>(null);
  const [deleting, setDeleting] = useState(false);

  const { data, loading, error, refetch } = useApi(async () => {
    const tasksRes = await tasksApi.list("published");
    const tasks = tasksRes.items;
    if (tasks.length === 0) return { tasks, statsMap: new Map<number, TaskStatsResponse>() };

    const statsArr = await Promise.all(tasks.map((t) => tasksApi.stats(t.id)));
    const statsMap = new Map<number, TaskStatsResponse>();
    for (const s of statsArr) {
      statsMap.set(s.task_id, s);
    }
    return { tasks, statsMap };
  }, []);

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-10 w-28" />
        </div>
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full rounded-lg" />
        ))}
      </div>
    );
  }

  if (error) {
    return <p className="text-sm text-destructive">{error}</p>;
  }

  async function handleDelete() {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      await tasksApi.delete(deleteTarget.id);
      toast.success("任务已删除");
      setDeleteTarget(null);
      refetch();
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "删除失败");
    } finally {
      setDeleting(false);
    }
  }

  const tasks = data?.tasks ?? [];
  const statsMap = data?.statsMap ?? new Map();

  return (
    <div className="space-y-4 animate-fade-in-up">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-heading font-semibold">仪表板</h1>
        <Button onClick={() => navigate("/admin/tasks/new")}>
          <PlusCircle className="mr-2 h-4 w-4" />
          发布新任务
        </Button>
      </div>

      {tasks.length === 0 ? (
        <EmptyState
          icon={<ClipboardList className="h-12 w-12" />}
          title="暂无任务"
          description="发布第一个任务，开始管理课程"
          action={
            <Button onClick={() => navigate("/admin/tasks/new")}>
              <PlusCircle className="mr-2 h-4 w-4" />
              发布第一个任务
            </Button>
          }
        />
      ) : (
        tasks.map((task, index) => {
          const stats = statsMap.get(task.id);
          const submitted = stats?.submitted_count ?? 0;
          const total = stats?.total_students ?? 0;
          const rate = total > 0 ? Math.round((submitted / total) * 100) : 0;

          return (
            <Card
              key={task.id}
              className="cursor-pointer transition-all hover:shadow-md hover:-translate-y-0.5 animate-stagger"
              style={{ '--stagger-index': index } as React.CSSProperties}
              onClick={() => navigate(`/admin/tasks/${task.id}`)}
            >
              <CardContent className="py-5">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-base font-medium">{task.title}</h3>
                    <p className="mt-1 text-sm text-muted-foreground">
                      发布于 {formatDate(task.created_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <span className="text-sm font-medium text-muted-foreground">
                      {submitted}/{total} ({rate}%)
                    </span>
                    <Button
                      variant="ghost"
                      size="icon"
                      className="h-8 w-8 text-muted-foreground hover:text-destructive"
                      onClick={(e) => {
                        e.stopPropagation();
                        setDeleteTarget(task);
                      }}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
                <div className="mt-3 h-2 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full bg-primary transition-all"
                    style={{ width: `${rate}%` }}
                  />
                </div>
              </CardContent>
            </Card>
          );
        })
      )}
      {/* Delete confirmation dialog */}
      <Dialog open={!!deleteTarget} onOpenChange={(open) => !open && setDeleteTarget(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>删除任务</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-muted-foreground">
            确定要删除任务「{deleteTarget?.title}」吗？该任务下所有学生的提交记录和文件将被一并删除，此操作不可撤销。
          </p>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteTarget(null)}>
              取消
            </Button>
            <Button variant="destructive" onClick={handleDelete} disabled={deleting}>
              {deleting ? "删除中..." : "删除"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
