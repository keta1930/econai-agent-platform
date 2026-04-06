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
import { submissionsApi } from "@/api/submissions";
import { cn } from "@/lib/utils";
import { scoreColor, formatDate } from "@/lib/format";
import { FileText } from "lucide-react";

export default function GradesPage() {
  const navigate = useNavigate();
  const { data, loading, error } = useApi(() => submissionsApi.listMy(), []);

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-32" />
        <Skeleton className="h-64 w-full rounded-lg" />
      </div>
    );
  }

  if (error) {
    return <p className="text-sm text-destructive">{error}</p>;
  }

  const allSubmissions = data?.items ?? [];
  const submissions = (() => {
    const seen = new Set<string>();
    return allSubmissions.filter((sub) => {
      if (seen.has(sub.task_id)) return false;
      seen.add(sub.task_id);
      return true;
    });
  })();

  const versionCountByTask = new Map<string, number>();
  for (const sub of allSubmissions) {
    versionCountByTask.set(sub.task_id, (versionCountByTask.get(sub.task_id) ?? 0) + 1);
  }

  return (
    <div className="space-y-4 animate-fade-in-up">
      <h1 className="text-2xl font-heading font-semibold page-title-decorated">
        我的成绩
      </h1>

      {submissions.length === 0 ? (
        <EmptyState
          icon={<FileText className="h-12 w-12" />}
          title="暂无提交记录"
          description="完成任务并提交后，成绩将在此显示"
        />
      ) : (
        <Table className="data-table">
          <TableHeader>
            <TableRow>
              <TableHead>任务标题</TableHead>
              <TableHead>提交时间</TableHead>
              <TableHead>版本</TableHead>
              <TableHead>状态</TableHead>
              <TableHead className="text-right">分数</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {submissions.map((sub) => (
              <TableRow
                key={sub.id}
                className="cursor-pointer"
                onClick={() => navigate(`/student/tasks/${sub.task_id}`)}
              >
                <TableCell className="font-medium">{sub.task_title}</TableCell>
                <TableCell className="text-muted-foreground">
                  {formatDate(sub.submitted_at)}
                </TableCell>
                <TableCell className="text-muted-foreground">
                  {versionCountByTask.get(sub.task_id) ?? 1} 次提交
                </TableCell>
                <TableCell>
                  <StatusBadge status={sub.status} />
                </TableCell>
                <TableCell className={cn("text-right font-medium", scoreColor(sub.score))}>
                  {sub.score !== null ? sub.score : "-"}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      )}
    </div>
  );
}
