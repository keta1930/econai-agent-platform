import { useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
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
      <div className="space-y-4">
        {Array.from({ length: 3 }).map((_, i) => (
          <Skeleton key={i} className="h-20 w-full rounded-lg" />
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

  // Build a map of task_id -> submission status
  const submissionMap = new Map<number, string>();
  if (subsData?.items) {
    for (const sub of subsData.items) {
      submissionMap.set(sub.task_id, sub.status);
    }
  }

  return (
    <div className="space-y-4 animate-fade-in-up">
      <h1 className="text-2xl font-heading font-semibold">任务列表</h1>
      {tasks.map((task, index) => (
        <Card
          key={task.id}
          className="cursor-pointer transition-all hover:shadow-md hover:-translate-y-0.5 animate-stagger"
          style={{ '--stagger-index': index } as React.CSSProperties}
          onClick={() => navigate(`/student/tasks/${task.id}`)}
        >
          <CardContent className="flex items-center justify-between py-5">
            <div>
              <h3 className="text-base font-medium">{task.title}</h3>
              <p className="mt-1 text-sm text-muted-foreground">
                发布于 {formatDate(task.created_at)}
              </p>
            </div>
            <StatusBadge status={submissionMap.get(task.id) ?? "not_submitted"} />
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
