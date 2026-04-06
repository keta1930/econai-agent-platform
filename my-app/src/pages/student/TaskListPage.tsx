import { useNavigate } from "react-router-dom";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
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
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-64 w-full rounded-lg" />
      </div>
    );
  }

  if (tasksError) {
    return <p className="text-sm text-destructive">{tasksError}</p>;
  }

  const tasks = tasksData?.items ?? [];

  const submissionMap = new Map<string, string>();
  if (subsData?.items) {
    for (const sub of subsData.items) {
      if (!submissionMap.has(sub.task_id)) {
        submissionMap.set(sub.task_id, sub.status);
      }
    }
  }

  return (
    <div className="space-y-4 animate-fade-in-up">
      <h1 className="text-2xl font-heading font-semibold page-title-decorated">
        任务列表
      </h1>

      {tasks.length === 0 ? (
        <EmptyState
          icon={<ClipboardList className="h-12 w-12" />}
          title="暂无任务"
          description="老师还没有发布任何任务"
        />
      ) : (
        <Table className="data-table">
          <TableHeader>
            <TableRow>
              <TableHead>任务标题</TableHead>
              <TableHead>发布时间</TableHead>
              <TableHead>提交状态</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {tasks.map((task) => (
              <TableRow
                key={task.id}
                className="cursor-pointer"
                onClick={() => navigate(`/student/tasks/${task.id}`)}
              >
                <TableCell className="font-medium">{task.title}</TableCell>
                <TableCell className="text-muted-foreground">
                  {formatDate(task.created_at)}
                </TableCell>
                <TableCell>
                  <StatusBadge status={submissionMap.get(task.id) ?? "not_submitted"} />
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
