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
import { FileText } from "lucide-react";

function scoreColor(score: number | null): string {
  if (score === null) return "";
  if (score >= 80) return "text-green-600 font-medium";
  if (score >= 60) return "text-amber-600 font-medium";
  return "text-red-600 font-medium";
}

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

  const submissions = data?.items ?? [];

  return (
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">我的成绩</h1>
      {submissions.length === 0 ? (
        <EmptyState
          icon={<FileText className="h-12 w-12" />}
          title="暂无提交记录"
          description="完成任务并提交后，成绩将在此显示"
        />
      ) : (
        <div className="rounded-lg border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>任务标题</TableHead>
                <TableHead>提交时间</TableHead>
                <TableHead>状态</TableHead>
                <TableHead className="text-right">分数</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {submissions.map((sub) => (
                <TableRow
                  key={sub.id}
                  className="cursor-pointer hover:bg-muted/50"
                  onClick={() => navigate(`/student/tasks/${sub.task_id}`)}
                >
                  <TableCell className="font-medium">{sub.task_title}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(sub.submitted_at).toLocaleDateString("zh-CN")}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={sub.status} />
                  </TableCell>
                  <TableCell className={cn("text-right", scoreColor(sub.score))}>
                    {sub.score !== null ? sub.score : "-"}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  );
}
