import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/EmptyState";
import { ConfirmDialog } from "@/components/confirm-dialog";
import { useApi } from "@/hooks/useApi";
import { useClassContext } from "@/contexts/ClassContext";
import { tasksApi } from "@/api/tasks";
import { toast } from "sonner";
import { formatDate } from "@/lib/format";
import { ClipboardList, PlusCircle, Trash2 } from "lucide-react";
import type { Task, TaskStatsResponse } from "@/types/task";

export default function DashboardPage() {
  const navigate = useNavigate();
  const { currentClass } = useClassContext();
  const [deleteTarget, setDeleteTarget] = useState<Task | null>(null);
  const [deleting, setDeleting] = useState(false);

  const classId = currentClass?.id;

  const { data, loading, error, refetch } = useApi(async () => {
    if (!classId) return { tasks: [], statsMap: new Map<string, TaskStatsResponse>() };

    const tasksRes = await tasksApi.list("published", classId);
    const tasks = tasksRes.items;
    if (tasks.length === 0) return { tasks, statsMap: new Map<string, TaskStatsResponse>() };

    const statsArr = await Promise.all(tasks.map((t) => tasksApi.stats(t.id)));
    const statsMap = new Map<string, TaskStatsResponse>();
    for (const s of statsArr) {
      statsMap.set(s.task_id, s);
    }
    return { tasks, statsMap };
  }, [classId]);

  if (!currentClass) {
    return (
      <EmptyState
        icon={<ClipboardList className="h-12 w-12" />}
        title="请先选择班级"
        description="在左侧导航栏选择一个班级，或先创建班级"
        action={
          <button
            className="btn-scholarly"
            onClick={() => navigate("/admin/classes")}
          >
            <PlusCircle className="mr-2 h-4 w-4" />
            前往班级管理
          </button>
        }
      />
    );
  }

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex items-center justify-between">
          <Skeleton className="h-8 w-32" />
          <Skeleton className="h-10 w-28" />
        </div>
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-24 w-full rounded-xl" />
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
      {/* Page header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-heading font-semibold page-title-decorated">作业列表</h1>
        <button
          className="btn-scholarly"
          onClick={() => navigate("/admin/tasks/new")}
        >
          <PlusCircle className="mr-2 h-4 w-4" />
          创建作业
        </button>
      </div>

      {tasks.length === 0 ? (
        <EmptyState
          icon={<ClipboardList className="h-12 w-12" />}
          title="暂无任务"
          description="创建第一个作业，开始管理课程"
          action={
            <button
              className="btn-scholarly"
              onClick={() => navigate("/admin/tasks/new")}
            >
              <PlusCircle className="mr-2 h-4 w-4" />
              创建第一个作业
            </button>
          }
        />
      ) : (
        <div className="grid grid-cols-[repeat(auto-fill,minmax(400px,1fr))] gap-6">
          {tasks.map((task, index) => {
            const stats = statsMap.get(task.id);
            const submitted = stats?.submitted_count ?? 0;
            const total = stats?.total_students ?? 0;
            const rate = total > 0 ? Math.round((submitted / total) * 100) : 0;

            return (
              <div
                key={task.id}
                className="task-card-scholarly animate-scroll-reveal"
                style={{ '--stagger-index': index } as React.CSSProperties}
                onClick={() => navigate(`/admin/tasks/${task.id}`)}
              >
                {/* Delete button — visible only on hover */}
                <button
                  className="task-delete-btn"
                  onClick={(e) => {
                    e.stopPropagation();
                    setDeleteTarget(task);
                  }}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>

                {/* Header: title + date | stats */}
                <div className="flex items-start justify-between">
                  <div>
                    <h3 className="font-heading text-base font-semibold text-foreground">
                      {task.title}
                    </h3>
                    <p className="mt-1.5 text-xs text-muted-foreground">
                      发布于 {formatDate(task.created_at)}
                    </p>
                  </div>
                  <div className="text-right shrink-0 ml-4">
                    <p className="text-sm font-semibold text-primary">
                      {submitted}/{total}
                    </p>
                    <p className="text-[11px] text-muted-foreground mt-0.5">
                      已提交 ({rate}%)
                    </p>
                  </div>
                </div>

                {/* Progress bar */}
                <div className="mt-4 h-1 w-full overflow-hidden rounded-sm bg-[var(--paper-deep)]">
                  <div
                    className="h-full rounded-sm progress-fill-cyan transition-all duration-700"
                    style={{ width: `${rate}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
      <ConfirmDialog
        open={!!deleteTarget}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="删除任务"
        description={`确定要删除任务「${deleteTarget?.title}」吗？该任务下所有学生的提交记录和文件将被一并删除，此操作不可撤销。`}
        confirmText="删除"
        onConfirm={handleDelete}
        loading={deleting}
      />
    </div>
  );
}
