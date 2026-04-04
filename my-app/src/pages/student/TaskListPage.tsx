import { useNavigate } from "react-router-dom";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/StatusBadge";
import { EmptyState } from "@/components/EmptyState";
import { useApi } from "@/hooks/useApi";
import { tasksApi } from "@/api/tasks";
import { submissionsApi } from "@/api/submissions";
import { formatDate } from "@/lib/format";
import { ClipboardList } from "lucide-react";

export default function TaskListPage() {
  const navigate = useNavigate();
  const { data: tasksData, loading: tasksLoading, error: tasksError } = useApi(
    () => tasksApi.list("published"),
    [],
  );
  const { data: subsData } = useApi(() => submissionsApi.listMy(), []);

  if (tasksLoading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-[72px] w-full rounded-xl" />
        ))}
      </div>
    );
  }

  if (tasksError) {
    return <p className="text-sm text-destructive">{tasksError}</p>;
  }

  const tasks = tasksData?.items ?? [];
  if (tasks.length === 0) {
    return (
      <EmptyState
        icon={<ClipboardList className="h-12 w-12" />}
        title="暂无任务"
        description="老师还没有发布任何任务"
      />
    );
  }

  const submissionMap = new Map<string, string>();
  if (subsData?.items) {
    for (const sub of subsData.items) {
      if (!submissionMap.has(sub.task_id)) {
        submissionMap.set(sub.task_id, sub.status);
      }
    }
  }

  return (
    <div className="animate-fade-in-up">
      <h1 className="text-[22px] font-heading font-semibold page-title-decorated mb-6">
        任务列表
      </h1>
      <div className="space-y-3">
        {tasks.map((task, index) => (
          <button
            key={task.id}
            type="button"
            className="student-task-card animate-scroll-reveal"
            style={{ "--stagger-index": index } as React.CSSProperties}
            onClick={() => navigate(`/student/tasks/${task.id}`)}
          >
            <div>
              <h3 className="text-[15px] font-heading font-semibold text-[var(--text-primary,#1c1a17)]">
                {task.title}
              </h3>
              <p className="mt-1 text-xs" style={{ color: "var(--text-tertiary,#8a8479)" }}>
                发布于 {formatDate(task.created_at)}
              </p>
            </div>
            <StatusBadge status={submissionMap.get(task.id) ?? "not_submitted"} />
          </button>
        ))}
      </div>
    </div>
  );
}
