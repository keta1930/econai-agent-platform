import { useNavigate } from "react-router-dom";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/EmptyState";
import { useApi } from "@/hooks/useApi";
import { tasksApi } from "@/api/tasks";
import { ClipboardList, PlusCircle } from "lucide-react";
import type { TaskStatsResponse } from "@/types/task";

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

export default function DashboardPage() {
  const navigate = useNavigate();

  const { data, loading, error } = useApi(async () => {
    const tasksRes = await tasksApi.list();
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
                  <span className="text-sm font-medium text-muted-foreground">
                    {submitted}/{total} ({rate}%)
                  </span>
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
    </div>
  );
}
