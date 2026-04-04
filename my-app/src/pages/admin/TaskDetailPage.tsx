import { useParams, useNavigate } from "react-router-dom";
import { MarkdownContent } from "@/components/ui/markdown-content";
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
import { useApi } from "@/hooks/useApi";
import { tasksApi } from "@/api/tasks";
import { Button } from "@/components/ui/button";
import { Users, FileCheck, BarChart3, Eye } from "lucide-react";

export default function AdminTaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const id = taskId!;

  const { data: task, loading: taskLoading } = useApi(() => tasksApi.get(id), [id]);
  const { data: stats, loading: statsLoading } = useApi(() => tasksApi.stats(id), [id]);

  const loading = taskLoading || statsLoading;

  if (loading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-48 w-full rounded-lg" />
        <Skeleton className="h-24 w-full rounded-lg" />
        <Skeleton className="h-64 w-full rounded-lg" />
      </div>
    );
  }

  if (!task) {
    return <p className="text-sm text-destructive">任务不存在</p>;
  }

  const ratePercent = stats ? Math.round(stats.submission_rate * 100) : 0;

  return (
    <div className="space-y-0 animate-fade-in-up">
      {/* Page header: title left, stats right */}
      <div className="flex items-start justify-between gap-8 pb-4 border-b border-[var(--paper-deep,#e8e0d4)]">
        <div className="min-w-0">
          <h1 className="text-2xl font-heading font-semibold page-title-decorated">
            {task.title}
          </h1>
          <p className="mt-1 text-sm text-muted-foreground">
            发布于 {new Date(task.created_at).toLocaleDateString("zh-CN")}
          </p>
        </div>

      {stats && (
        <div className="flex shrink-0 gap-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--paper-warm)]">
              <Users className="h-5 w-5 text-[var(--ink-deep)]" />
            </div>
            <div>
              <p className="text-xl font-bold font-heading leading-none">{stats.total_students}</p>
              <p className="text-xs text-muted-foreground mt-0.5">总人数</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--paper-warm)]">
              <FileCheck className="h-5 w-5 text-[var(--ink-deep)]" />
            </div>
            <div>
              <p className="text-xl font-bold font-heading leading-none">{stats.submitted_count}</p>
              <p className="text-xs text-muted-foreground mt-0.5">已提交</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--paper-warm)]">
              <BarChart3 className="h-5 w-5 text-[var(--ink-deep)]" />
            </div>
            <div>
              <p className="text-xl font-bold font-heading leading-none">{ratePercent}%</p>
              <p className="text-xs text-muted-foreground mt-0.5">提交率</p>
            </div>
          </div>
        </div>
      )}
      </div>

      {/* Task description + grading criteria side by side */}
      <div className="mt-6 grid grid-cols-1 gap-6 md:grid-cols-2">
        <div>
          <h3 className="font-heading text-sm font-semibold text-muted-foreground tracking-wide mb-3 pb-2 border-b border-[var(--paper-deep)]">
            任务说明
          </h3>
          <p className="whitespace-pre-wrap text-sm leading-relaxed">{task.description}</p>
        </div>
        <div>
          <h3 className="font-heading text-sm font-semibold text-muted-foreground tracking-wide mb-3 pb-2 border-b border-[var(--paper-deep)]">
            打分标准
          </h3>
          <MarkdownContent content={task.grading_criteria} />
        </div>
      </div>

      {/* Submitted students table */}
      {stats && stats.submissions.length > 0 && (
        <div className="mt-6">
          <h3 className="font-heading text-sm font-semibold text-muted-foreground tracking-wide mb-3 pb-2 border-b border-[var(--paper-deep)]">
            已提交 ({stats.submissions.length})
          </h3>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>学号</TableHead>
                <TableHead>状态</TableHead>
                <TableHead className="text-right">分数</TableHead>
                <TableHead className="text-right">提交次数</TableHead>
                <TableHead>提交时间</TableHead>
                <TableHead className="text-right">操作</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {stats.submissions.map((sub) => (
                <TableRow key={sub.student_id}>
                  <TableCell>
                    <button
                      className="text-primary hover:underline font-medium"
                      onClick={() => navigate(`/admin/students/${sub.student_id}`)}
                    >
                      {sub.username}
                    </button>
                  </TableCell>
                  <TableCell>
                    <StatusBadge status={sub.status} />
                  </TableCell>
                  <TableCell className="text-right">
                    {sub.score !== null ? sub.score : "-"}
                  </TableCell>
                  <TableCell className="text-right text-muted-foreground">
                    {sub.submission_count}
                  </TableCell>
                  <TableCell className="text-muted-foreground">
                    {new Date(sub.submitted_at).toLocaleString("zh-CN")}
                  </TableCell>
                  <TableCell className="text-right">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() =>
                        navigate(`/admin/tasks/${taskId}/submissions/${sub.student_id}`)
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

      {/* Not submitted students — below the submitted table */}
      {stats && stats.not_submitted.length > 0 && (
        <div className="mt-6">
          <h3 className="font-heading text-sm font-semibold text-muted-foreground tracking-wide mb-3 pb-2 border-b border-[var(--paper-deep)]">
            未提交学生 ({stats.not_submitted.length})
          </h3>
          <div className="flex flex-wrap gap-2">
            {stats.not_submitted.map((sid) => (
              <span
                key={sid}
                className="rounded-md border border-[var(--paper-border)] bg-[var(--paper-warm)] px-3 py-1 text-sm text-muted-foreground"
              >
                {sid}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
