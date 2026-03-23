import { useState } from "react";
import { useParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { FileUpload } from "@/components/FileUpload";
import { useApi } from "@/hooks/useApi";
import { tasksApi } from "@/api/tasks";
import { submissionsApi } from "@/api/submissions";
import { ApiError } from "@/api/client";
import { Loader2, CheckCircle2, XCircle, Clock } from "lucide-react";
import type { SubmissionDetail } from "@/types/submission";

export default function TaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const id = Number(taskId);

  const { data: task, loading: taskLoading } = useApi(() => tasksApi.get(id), [id]);

  const {
    data: submission,
    loading: subLoading,
    refetch,
  } = useApi<SubmissionDetail | null>(async () => {
    try {
      return await submissionsApi.getMy(id);
    } catch (e) {
      // 404 means not submitted
      if (e instanceof ApiError && e.status === 404) return null;
      throw e;
    }
  }, [id]);

  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");

  async function handleSubmit() {
    if (!selectedFile) return;
    setSubmitting(true);
    setSubmitError("");
    try {
      await submissionsApi.submit(id, selectedFile);
      setSelectedFile(null);
      await refetch();
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : "提交失败");
    } finally {
      setSubmitting(false);
    }
  }

  if (taskLoading || subLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-48" />
        <Skeleton className="h-48 w-full rounded-lg" />
        <Skeleton className="h-32 w-full rounded-lg" />
      </div>
    );
  }

  if (!task) {
    return <p className="text-sm text-destructive">任务不存在</p>;
  }

  return (
    <div className="space-y-6">
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
            <p className="whitespace-pre-wrap text-sm">{task.grading_criteria}</p>
          </div>
        </CardContent>
      </Card>

      {/* Submission section */}
      {!submission && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">提交作业</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <FileUpload onFileSelect={setSelectedFile} disabled={submitting} />
            {submitError && <p className="text-sm text-destructive">{submitError}</p>}
            <Button onClick={handleSubmit} disabled={!selectedFile || submitting}>
              {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              提交
            </Button>
          </CardContent>
        </Card>
      )}

      {submission?.status === "pending" || submission?.status === "grading" ? (
        <Card>
          <CardContent className="flex flex-col items-center py-12 text-center">
            <Loader2 className="h-10 w-10 animate-spin text-primary" />
            <p className="mt-4 font-medium">AI 正在批改中...</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {submission.status === "pending" ? "已提交，等待批改" : "批改进行中，请稍候"}
            </p>
          </CardContent>
        </Card>
      ) : null}

      {submission?.status === "completed" && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-lg">
              <CheckCircle2 className="h-5 w-5 text-success" />
              批改结果
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-baseline gap-2">
              <span className="text-4xl font-bold text-primary">{submission.score}</span>
              <span className="text-sm text-muted-foreground">分</span>
            </div>
            {submission.suggestion && (
              <div>
                <h4 className="mb-2 text-sm font-medium text-muted-foreground">AI 建议</h4>
                <p className="whitespace-pre-wrap text-sm rounded-md bg-muted p-4">
                  {submission.suggestion}
                </p>
              </div>
            )}
            {submission.graded_at && (
              <p className="text-xs text-muted-foreground">
                批改完成于 {new Date(submission.graded_at).toLocaleString("zh-CN")}
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {submission?.status === "failed" && (
        <Card>
          <CardContent className="flex flex-col items-center py-12 text-center">
            <XCircle className="h-10 w-10 text-destructive" />
            <p className="mt-4 font-medium">批改失败</p>
            <p className="mt-1 text-sm text-muted-foreground">
              AI 批改过程中出现错误，请联系管理员
            </p>
          </CardContent>
        </Card>
      )}

      {submission && !["pending", "grading", "completed", "failed"].includes(submission.status) && (
        <Card>
          <CardContent className="flex items-center gap-2 py-8 justify-center">
            <Clock className="h-5 w-5 text-muted-foreground" />
            <p className="text-sm text-muted-foreground">已提交，等待处理</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
