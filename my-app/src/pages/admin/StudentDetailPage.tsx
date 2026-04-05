import { useParams, useNavigate } from "react-router-dom";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { StatusBadge } from "@/components/StatusBadge";
import { EmptyState } from "@/components/EmptyState";
import { useApi } from "@/hooks/useApi";
import { submissionsApi } from "@/api/submissions";
import { FileText, Eye } from "lucide-react";
import { cn } from "@/lib/utils";
import { scoreColor } from "@/lib/format";
import { GradingFeedback } from "@/components/GradingFeedback";

export default function StudentDetailPage() {
  const { studentId } = useParams<{ studentId: string }>();
  const navigate = useNavigate();

  const { data, loading, error } = useApi(
    () => submissionsApi.getStudentSubmissions(studentId!),
    [studentId],
  );

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-64 w-full rounded-lg" />
      </div>
    );
  }

  if (error) {
    return <p className="text-sm text-destructive">{error}</p>;
  }

  const submissions = data?.items ?? [];

  return (
    <div className="space-y-0 animate-fade-in-up">
      <h1 className="text-2xl font-heading font-semibold page-title-decorated">学生详情</h1>

      {submissions.length === 0 ? (
        <div className="mt-4">
          <EmptyState
            icon={<FileText className="h-12 w-12" />}
            title="该学生暂无提交记录"
            description="该学生尚未提交任何作业"
          />
        </div>
      ) : (
        <div className="mt-6">
          <h3 className="font-heading text-sm font-semibold text-muted-foreground tracking-wide mb-3 pb-2 border-b border-[var(--paper-deep)]">
            提交记录
          </h3>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>任务标题</TableHead>
                <TableHead>版本</TableHead>
                <TableHead>提交时间</TableHead>
                <TableHead>状态</TableHead>
                <TableHead className="text-right">分数</TableHead>
                <TableHead>批改详情</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {submissions.map((sub) => (
                <TableRow key={sub.id}>
                  <TableCell className="font-medium">{sub.task_title}</TableCell>
                  <TableCell className="text-muted-foreground">v{sub.version}</TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(sub.submitted_at).toLocaleString("zh-CN")}
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={sub.status} />
                  </TableCell>
                  <TableCell className={cn("text-right", scoreColor(sub.score))}>
                    {sub.score !== null ? sub.score : "-"}
                  </TableCell>
                  <TableCell>
                    {sub.feedback && sub.score !== null ? (
                      <Dialog>
                        <DialogTrigger
                          render={<Button variant="ghost" size="sm" className="text-xs" />}
                        >
                          查看详情
                        </DialogTrigger>
                        <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto">
                          <DialogHeader>
                            <DialogTitle>批改详情 - {sub.task_title}</DialogTitle>
                          </DialogHeader>
                          <GradingFeedback
                            feedback={sub.feedback}
                            score={sub.score}
                            gradedAt={sub.graded_at}
                            version={sub.version}
                          />
                        </DialogContent>
                      </Dialog>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        navigate(`/admin/tasks/${sub.task_id}/submissions/${studentId}`)
                      }
                    >
                      <Eye className="mr-1 h-4 w-4" />
                      查看
                    </Button>
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
