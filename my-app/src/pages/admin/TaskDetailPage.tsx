import { useParams, useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import { Users, FileCheck, BarChart3 } from "lucide-react";

export default function AdminTaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const id = Number(taskId);

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
    <div className="space-y-6 animate-fade-in-up">
      {/* Task info */}
      <Card>
        <CardHeader>
          <CardTitle className="text-xl">{task.title}</CardTitle>
          <p className="text-sm text-muted-foreground">
            发布于 {new Date(task.created_at).toLocaleDateString("zh-CN")}
          </p>
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <h4 className="mb-2 text-sm font-medium text-muted-foreground">任务说明</h4>
            <p className="whitespace-pre-wrap text-sm">{task.description}</p>
          </div>
          <div>
            <h4 className="mb-2 text-sm font-medium text-muted-foreground">打分标准</h4>
            <MarkdownContent content={task.grading_criteria} />
          </div>
        </CardContent>
      </Card>

      {/* Statistics */}
      {stats && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <Card className="animate-stagger" style={{ '--stagger-index': 0 } as React.CSSProperties}>
            <CardContent className="flex items-center gap-3 py-4">
              <div className="rounded-full p-2 bg-primary/10">
                <Users className="h-8 w-8 text-primary" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.total_students}</p>
                <p className="text-xs text-muted-foreground">总人数</p>
              </div>
            </CardContent>
          </Card>
          <Card className="animate-stagger" style={{ '--stagger-index': 1 } as React.CSSProperties}>
            <CardContent className="flex items-center gap-3 py-4">
              <div className="rounded-full p-2 bg-blue-50">
                <FileCheck className="h-8 w-8 text-blue-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{stats.submitted_count}</p>
                <p className="text-xs text-muted-foreground">已提交</p>
              </div>
            </CardContent>
          </Card>
          <Card className="animate-stagger" style={{ '--stagger-index': 2 } as React.CSSProperties}>
            <CardContent className="flex items-center gap-3 py-4">
              <div className="rounded-full p-2 bg-green-50">
                <BarChart3 className="h-8 w-8 text-green-600" />
              </div>
              <div>
                <p className="text-2xl font-bold">{ratePercent}%</p>
                <p className="text-xs text-muted-foreground">提交率</p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Submitted students */}
      {stats && stats.submissions.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">已提交学生</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>学号</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead className="text-right">分数</TableHead>
                    <TableHead>提交时间</TableHead>
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
                          {sub.student_id}
                        </button>
                      </TableCell>
                      <TableCell>
                        <StatusBadge status={sub.status} />
                      </TableCell>
                      <TableCell className="text-right">
                        {sub.score !== null ? sub.score : "-"}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {new Date(sub.submitted_at).toLocaleString("zh-CN")}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Not submitted students */}
      {stats && stats.not_submitted.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">未提交学生</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {stats.not_submitted.map((sid) => (
                <span
                  key={sid}
                  className="rounded-md bg-muted px-3 py-1 text-sm text-muted-foreground"
                >
                  {sid}
                </span>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
