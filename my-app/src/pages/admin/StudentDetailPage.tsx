import { useParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
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
import { FileText } from "lucide-react";
import { cn } from "@/lib/utils";

function scoreColor(score: number | null): string {
  if (score === null) return "";
  if (score >= 80) return "text-green-600 font-medium";
  if (score >= 60) return "text-amber-600 font-medium";
  return "text-red-600 font-medium";
}

export default function StudentDetailPage() {
  const { studentId } = useParams<{ studentId: string }>();

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
    <div className="space-y-4">
      <h1 className="text-2xl font-semibold">学生 {studentId}</h1>

      {submissions.length === 0 ? (
        <EmptyState
          icon={<FileText className="h-12 w-12" />}
          title="该学生暂无提交记录"
          description="该学生尚未提交任何作业"
        />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">提交记录</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="rounded-lg border">
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>任务标题</TableHead>
                    <TableHead>提交时间</TableHead>
                    <TableHead>状态</TableHead>
                    <TableHead className="text-right">分数</TableHead>
                    <TableHead>AI 建议</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {submissions.map((sub) => (
                    <TableRow key={sub.id}>
                      <TableCell className="font-medium">{sub.task_title}</TableCell>
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
                        {sub.suggestion ? (
                          <Dialog>
                            <DialogTrigger
                              render={<Button variant="ghost" size="sm" className="text-xs" />}
                            >
                              {sub.suggestion.length > 30
                                ? sub.suggestion.slice(0, 30) + "..."
                                : sub.suggestion}
                            </DialogTrigger>
                            <DialogContent className="max-w-lg">
                              <DialogHeader>
                                <DialogTitle>AI 建议 - {sub.task_title}</DialogTitle>
                              </DialogHeader>
                              <p className="whitespace-pre-wrap text-sm">{sub.suggestion}</p>
                            </DialogContent>
                          </Dialog>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
