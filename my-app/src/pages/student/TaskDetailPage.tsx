import { useState } from "react";
import { useParams } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { MarkdownContent } from "@/components/ui/markdown-content";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { FileUpload } from "@/components/FileUpload";
import { MultiImageUpload } from "@/components/MultiImageUpload";
import { StatusBadge } from "@/components/StatusBadge";
import { scoreColor } from "@/lib/format";
import { useApi } from "@/hooks/useApi";
import { tasksApi } from "@/api/tasks";
import { submissionsApi } from "@/api/submissions";
import {
  Loader2,
  XCircle,
  Clock,
  ChevronDown,
  ChevronRight,
  History,
  Eye,
  BookOpen,
} from "lucide-react";
import { GradingFeedback } from "@/components/GradingFeedback";
import type { SubmissionDetail } from "@/types/submission";

export default function TaskDetailPage() {
  const { taskId } = useParams<{ taskId: string }>();
  const id = taskId!;

  const { data: task, loading: taskLoading } = useApi(() => tasksApi.get(id), [id]);

  const {
    data: submissionData,
    loading: subLoading,
    refetch,
  } = useApi(() => submissionsApi.getMy(id), [id]);

  const [activeTab, setActiveTab] = useState("text");
  const [textContent, setTextContent] = useState("");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedImages, setSelectedImages] = useState<File[]>([]);
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState("");
  const [historyOpen, setHistoryOpen] = useState(false);

  const submissions = submissionData?.items ?? [];
  const latestSubmission: SubmissionDetail | null = submissions[0] ?? null;
  const historySubmissions = submissions.slice(1);
  const hasSubmitted = submissions.length > 0;
  const isLatestPending =
    latestSubmission?.status === "pending" || latestSubmission?.status === "grading";

  const canSubmit =
    (activeTab === "text" && textContent.trim().length > 0) ||
    (activeTab === "file" && selectedFile !== null) ||
    (activeTab === "image" && selectedImages.length > 0);

  async function handleSubmit() {
    setSubmitting(true);
    setSubmitError("");
    try {
      if (activeTab === "text") {
        await submissionsApi.submit(id, "text", textContent);
        setTextContent("");
      } else if (activeTab === "file") {
        await submissionsApi.submit(id, "file", selectedFile!);
        setSelectedFile(null);
      } else {
        await submissionsApi.submitImages(id, selectedImages);
        setSelectedImages([]);
      }
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
        <Skeleton className="h-48 w-full rounded-xl" />
        <Skeleton className="h-32 w-full rounded-xl" />
      </div>
    );
  }

  if (!task) {
    return <p className="text-sm text-destructive">任务不存在</p>;
  }

  return (
    <div className="space-y-6 animate-fade-in-up">
      {/* Task info */}
      <div>
        <h1 className="text-[22px] font-heading font-semibold page-title-decorated mb-2">
          {task.title}
        </h1>
        <p className="pl-4 text-xs" style={{ color: "var(--text-tertiary,#8a8479)" }}>
          发布于 {new Date(task.created_at).toLocaleDateString("zh-CN")}
        </p>
      </div>

      <Card>
        <CardContent className="space-y-4 pt-6">
          <div>
            <h4 className="font-heading text-sm font-semibold text-muted-foreground tracking-wide mb-3 pb-2 border-b border-[var(--paper-deep)]">任务说明</h4>
            <p className="whitespace-pre-wrap text-sm">{task.description}</p>
          </div>
          <div>
            <h4 className="font-heading text-sm font-semibold text-muted-foreground tracking-wide mb-3 pb-2 border-b border-[var(--paper-deep)]">打分标准</h4>
            <MarkdownContent content={task.grading_criteria} />
          </div>
          {task.learning_resources && task.learning_resources.length > 0 && (
            <div>
              <h4 className="font-heading text-sm font-semibold text-muted-foreground tracking-wide mb-3 pb-2 border-b border-[var(--paper-deep)]">学习资源</h4>
              <div className="space-y-2">
                {task.learning_resources.map((resource, index) => (
                  <div
                    key={index}
                    className="flex items-start gap-3 rounded-md border border-[var(--paper-border)] p-2.5"
                  >
                    <BookOpen className="h-4 w-4 mt-0.5 text-muted-foreground shrink-0" />
                    <div className="min-w-0">
                      <a
                        href={resource.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm font-medium text-[var(--cyan-mid)] hover:underline"
                      >
                        {resource.title}
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Submit section */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg font-heading">
            {hasSubmitted ? "重新提交" : "提交作业"}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {isLatestPending ? (
            <p className="text-sm text-muted-foreground">
              最新提交正在批改中，批改完成后可重新提交
            </p>
          ) : (
            <>
              <Tabs value={activeTab} onValueChange={setActiveTab}>
                <TabsList>
                  <TabsTrigger value="text">文本粘贴</TabsTrigger>
                  <TabsTrigger value="file">文件上传</TabsTrigger>
                  <TabsTrigger value="image">图片上传</TabsTrigger>
                </TabsList>

                <TabsContent value="text">
                  <div className="space-y-2">
                    <Textarea
                      placeholder="在此输入作业内容..."
                      value={textContent}
                      onChange={(e) => setTextContent(e.target.value)}
                      disabled={submitting}
                      className="min-h-[160px] resize-y"
                    />
                    <p className="text-xs text-muted-foreground text-right">
                      {textContent.length} 字
                    </p>
                  </div>
                </TabsContent>

                <TabsContent value="file">
                  <FileUpload
                    onFileSelect={setSelectedFile}
                    disabled={submitting}
                    accept=".md,.txt,.json,.py,.yaml,.jsonl"
                    maxSize={2 * 1024 * 1024}
                  />
                </TabsContent>

                <TabsContent value="image">
                  <MultiImageUpload
                    onFilesChange={setSelectedImages}
                    disabled={submitting}
                  />
                </TabsContent>
              </Tabs>

              {submitError && <p className="text-sm text-destructive">{submitError}</p>}
              <Button onClick={handleSubmit} disabled={!canSubmit || submitting}>
                {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
                {hasSubmitted ? "重新提交" : "提交"}
              </Button>
            </>
          )}
        </CardContent>
      </Card>

      {/* Latest submission result */}
      {isLatestPending && (
        <Card>
          <CardContent className="flex flex-col items-center py-12 text-center">
            <Loader2 className="h-10 w-10 animate-spin text-primary" />
            <p className="mt-4 font-medium">AI 正在批改中...</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {latestSubmission.status === "pending"
                ? "已提交，等待批改"
                : "批改进行中，请稍候"}
            </p>
          </CardContent>
        </Card>
      )}

      {latestSubmission?.status === "manual_review" && (
        <Card>
          <CardContent className="flex flex-col items-center py-12 text-center">
            <Eye className="h-10 w-10 text-info" />
            <p className="mt-4 font-medium">已提交，待人工审核</p>
            <p className="mt-1 text-sm text-muted-foreground">
              {latestSubmission.content_type === "image"
                ? "当前 AI 模型不支持图片批改，已转为人工审核"
                : "该提交需要人工审核，请耐心等待"}
            </p>
          </CardContent>
        </Card>
      )}

      {latestSubmission?.status === "completed" &&
        latestSubmission.score !== null &&
        (latestSubmission.feedback ? (
          <GradingFeedback
            feedback={latestSubmission.feedback}
            score={latestSubmission.score}
            gradedAt={latestSubmission.graded_at}
            version={latestSubmission.version}
          />
        ) : (
          <Card>
            <CardContent className="py-6 text-center">
              <p className="text-4xl font-bold" style={{ color: scoreColor(latestSubmission.score) }}>
                {latestSubmission.score}
              </p>
              <p className="mt-2 text-sm text-muted-foreground">批改完成</p>
            </CardContent>
          </Card>
        ))}

      {latestSubmission?.status === "failed" && (
        <Card>
          <CardContent className="flex flex-col items-center py-12 text-center">
            <XCircle className="h-10 w-10 text-destructive" />
            <p className="mt-4 font-medium">批改失败</p>
            <p className="mt-1 text-sm text-muted-foreground">
              AI 批改过程中出现错误，请联系教师
            </p>
          </CardContent>
        </Card>
      )}

      {latestSubmission &&
        !["pending", "grading", "completed", "failed", "manual_review"].includes(
          latestSubmission.status
        ) && (
          <Card>
            <CardContent className="flex items-center gap-2 py-8 justify-center">
              <Clock className="h-5 w-5 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">已提交，等待处理</p>
            </CardContent>
          </Card>
        )}

      {/* History versions */}
      {historySubmissions.length > 0 && (
        <Card>
          <CardHeader className="pb-3">
            <button
              type="button"
              onClick={() => setHistoryOpen(!historyOpen)}
              className="flex w-full items-center gap-2 text-left"
            >
              <History className="h-4 w-4 text-muted-foreground" />
              <CardTitle className="text-base font-heading">历史版本</CardTitle>
              <span className="text-sm text-muted-foreground">
                ({historySubmissions.length})
              </span>
              <span className="ml-auto text-muted-foreground">
                {historyOpen ? (
                  <ChevronDown className="h-4 w-4" />
                ) : (
                  <ChevronRight className="h-4 w-4" />
                )}
              </span>
            </button>
          </CardHeader>
          {historyOpen && (
            <CardContent className="pt-0">
              <div className="rounded-md border border-[var(--paper-border)] overflow-hidden">
                {historySubmissions.map((sub) => (
                  <div
                    key={sub.id}
                    className="flex items-center justify-between px-4 py-3.5 text-sm border-b border-[var(--paper-deep)] last:border-b-0 transition-colors hover:bg-[var(--paper-warm)]"
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-medium">
                        第 {sub.version} 次提交
                      </span>
                      <span className="text-muted-foreground">
                        {new Date(sub.submitted_at).toLocaleString("zh-CN")}
                      </span>
                    </div>
                    <div className="flex items-center gap-3">
                      {sub.status === "completed" && sub.score !== null ? (
                        <span className="font-medium">{sub.score} 分</span>
                      ) : (
                        <StatusBadge status={sub.status} />
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          )}
        </Card>
      )}
    </div>
  );
}
