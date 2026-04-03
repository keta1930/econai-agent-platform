import { useState, useEffect, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { MarkdownContent } from "@/components/ui/markdown-content";
import { CodeBlock, extensionToLanguage } from "@/components/CodeBlock";
import { useApi } from "@/hooks/useApi";
import { tasksApi } from "@/api/tasks";
import { submissionsApi } from "@/api/submissions";
import type { SubmissionDetail, SubmissionContentResponse } from "@/types/submission";
import { ArrowLeft, GitCompareArrows, X, Loader2, AlertTriangle, Eye } from "lucide-react";

const CODE_EXTENSIONS = new Set([".py", ".json", ".yaml", ".jsonl"]);

function formatTime(iso: string): string {
  return new Date(iso).toLocaleString("zh-CN");
}

function versionLabel(sub: SubmissionDetail): string {
  return `第 ${sub.version} 次提交 · ${formatTime(sub.submitted_at)}`;
}

// --- Content renderer based on content_type and file_extension ---

function ContentRenderer({
  data,
  loading,
}: {
  data: SubmissionContentResponse | null;
  loading: boolean;
}) {
  if (loading) return <Skeleton className="h-48 w-full" />;
  if (!data) return <p className="text-sm text-muted-foreground">无法加载内容</p>;

  if (data.content_type === "image") {
    return (
      <div className="flex items-center justify-center p-4">
        <img
          src={data.content}
          alt={data.filename}
          className="max-h-[60vh] rounded-md object-contain"
        />
      </div>
    );
  }

  if (data.file_extension === ".md") {
    return <MarkdownContent content={data.content} />;
  }

  if (CODE_EXTENSIONS.has(data.file_extension)) {
    return (
      <CodeBlock
        code={data.content}
        language={extensionToLanguage(data.file_extension)}
      />
    );
  }

  // .txt or unknown — plain text
  return (
    <pre className="whitespace-pre-wrap text-sm leading-relaxed p-4 rounded-md bg-muted/30">
      {data.content}
    </pre>
  );
}

// --- Grading result panel ---

function GradingPanel({ submission }: { submission: SubmissionDetail }) {
  if (submission.status === "pending" || submission.status === "grading") {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16 text-muted-foreground">
        <Loader2 className="h-8 w-8 animate-spin" />
        <p className="text-sm">AI 批改进行中，请稍后刷新...</p>
      </div>
    );
  }

  if (submission.status === "failed") {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16 text-destructive">
        <AlertTriangle className="h-8 w-8" />
        <p className="text-sm">批改失败，请联系管理员</p>
      </div>
    );
  }

  if (submission.status === "manual_review") {
    return (
      <div className="flex flex-col items-center justify-center gap-3 py-16 text-blue-600">
        <Eye className="h-8 w-8" />
        <p className="text-sm">待人工审核</p>
        <p className="text-xs text-muted-foreground">图片类提交需要人工评分</p>
      </div>
    );
  }

  // completed
  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">分数</span>
        <span className="text-2xl font-bold">
          {submission.score !== null ? submission.score : "-"}
        </span>
      </div>
      {submission.suggestion && (
        <div>
          <h4 className="mb-2 text-sm font-medium text-muted-foreground">AI 建议</h4>
          <MarkdownContent content={submission.suggestion} />
        </div>
      )}
      {submission.graded_at && (
        <p className="text-xs text-muted-foreground">
          批改时间：{formatTime(submission.graded_at)}
        </p>
      )}
    </div>
  );
}

// --- Main page component ---

export default function SubmissionDetailPage() {
  const { taskId, studentId } = useParams<{ taskId: string; studentId: string }>();
  const navigate = useNavigate();
  const numericTaskId = Number(taskId);
  const numericStudentId = Number(studentId);

  // Fetch task info and all versions
  const { data: task } = useApi(() => tasksApi.get(numericTaskId), [numericTaskId]);
  const { data: versionsData, loading: versionsLoading } = useApi(
    () => submissionsApi.getStudentTaskSubmissions(numericTaskId, numericStudentId),
    [numericTaskId, numericStudentId],
  );

  const versions = versionsData?.items ?? [];

  // Current selected version
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [contentData, setContentData] = useState<SubmissionContentResponse | null>(null);
  const [contentLoading, setContentLoading] = useState(false);

  // Compare mode state
  const [compareMode, setCompareMode] = useState(false);
  const [compareLeftId, setCompareLeftId] = useState<number | null>(null);
  const [compareRightId, setCompareRightId] = useState<number | null>(null);
  const [contentLeft, setContentLeft] = useState<SubmissionContentResponse | null>(null);
  const [contentRight, setContentRight] = useState<SubmissionContentResponse | null>(null);
  const [leftLoading, setLeftLoading] = useState(false);
  const [rightLoading, setRightLoading] = useState(false);

  // Resolve effective selected ID: use explicit selection, or fall back to latest
  const effectiveSelectedId = selectedId ?? (versions.length > 0 ? versions[0].id : null);

  // Fetch content for current version
  const fetchContent = useCallback(async (submissionId: number) => {
    setContentLoading(true);
    try {
      const res = await submissionsApi.getContent(submissionId);
      setContentData(res);
    } catch {
      setContentData(null);
    } finally {
      setContentLoading(false);
    }
  }, []);

  useEffect(() => {
    if (effectiveSelectedId !== null) {
      fetchContent(effectiveSelectedId);
    }
  }, [effectiveSelectedId, fetchContent]);

  // Fetch content for compare panels
  const fetchCompareContent = useCallback(
    async (
      submissionId: number,
      setter: (v: SubmissionContentResponse | null) => void,
      setLoading: (v: boolean) => void,
    ) => {
      setLoading(true);
      try {
        const res = await submissionsApi.getContent(submissionId);
        setter(res);
      } catch {
        setter(null);
      } finally {
        setLoading(false);
      }
    },
    [],
  );

  useEffect(() => {
    if (compareLeftId !== null) {
      fetchCompareContent(compareLeftId, setContentLeft, setLeftLoading);
    }
  }, [compareLeftId, fetchCompareContent]);

  useEffect(() => {
    if (compareRightId !== null) {
      fetchCompareContent(compareRightId, setContentRight, setRightLoading);
    }
  }, [compareRightId, fetchCompareContent]);

  // Enter compare mode
  function enterCompare() {
    if (versions.length < 2) return;
    setCompareMode(true);
    setCompareLeftId(versions[versions.length - 1].id);
    setCompareRightId(versions[0].id);
  }

  function exitCompare() {
    setCompareMode(false);
    setCompareLeftId(null);
    setCompareRightId(null);
    setContentLeft(null);
    setContentRight(null);
  }

  const currentVersion = versions.find((v) => v.id === effectiveSelectedId) ?? null;

  if (versionsLoading) {
    return (
      <div className="space-y-4">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-[60vh] w-full rounded-lg" />
      </div>
    );
  }

  if (versions.length === 0) {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          <ArrowLeft className="mr-1 h-4 w-4" />
          返回
        </Button>
        <p className="text-sm text-muted-foreground">该学生暂无提交记录</p>
      </div>
    );
  }

  // --- Compare mode view ---
  if (compareMode) {
    const leftVersion = versions.find((v) => v.id === compareLeftId) ?? null;
    const rightVersion = versions.find((v) => v.id === compareRightId) ?? null;

    return (
      <div className="space-y-4 animate-fade-in-up">
        {/* Header */}
        <div className="flex flex-wrap items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
            <ArrowLeft className="mr-1 h-4 w-4" />
            返回
          </Button>
          <h1 className="text-lg font-heading font-semibold">版本对比</h1>
          <div className="flex items-center gap-2 ml-auto">
            <Select
              value={versions.find((v) => v.id === compareLeftId)?.version?.toString()}
              onValueChange={(ver) => {
                const found = versions.find((v) => v.version === Number(ver));
                if (found) setCompareLeftId(found.id);
              }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {versions.map((v) => (
                  <SelectItem key={v.id} value={String(v.version)}>
                    第 {v.version} 次提交
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <span className="text-sm text-muted-foreground">vs</span>
            <Select
              value={versions.find((v) => v.id === compareRightId)?.version?.toString()}
              onValueChange={(ver) => {
                const found = versions.find((v) => v.version === Number(ver));
                if (found) setCompareRightId(found.id);
              }}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {versions.map((v) => (
                  <SelectItem key={v.id} value={String(v.version)}>
                    第 {v.version} 次提交
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Button variant="outline" size="sm" onClick={exitCompare}>
              <X className="mr-1 h-4 w-4" />
              退出对比
            </Button>
          </div>
        </div>

        {/* Side-by-side content */}
        <div className="grid grid-cols-2 gap-4">
          <Card className="overflow-hidden">
            <CardHeader className="py-3">
              <CardTitle className="text-sm font-medium">
                {leftVersion ? versionLabel(leftVersion) : "选择版本"}
              </CardTitle>
            </CardHeader>
            <CardContent className="max-h-[70vh] overflow-y-auto">
              <ContentRenderer data={contentLeft} loading={leftLoading} />
            </CardContent>
          </Card>
          <Card className="overflow-hidden">
            <CardHeader className="py-3">
              <CardTitle className="text-sm font-medium">
                {rightVersion ? versionLabel(rightVersion) : "选择版本"}
              </CardTitle>
            </CardHeader>
            <CardContent className="max-h-[70vh] overflow-y-auto">
              <ContentRenderer data={contentRight} loading={rightLoading} />
            </CardContent>
          </Card>
        </div>
      </div>
    );
  }

  // --- Default detail view ---
  return (
    <div className="space-y-4 animate-fade-in-up">
      {/* Header */}
      <div className="flex flex-wrap items-center gap-3">
        <Button variant="ghost" size="sm" onClick={() => navigate(-1)}>
          <ArrowLeft className="mr-1 h-4 w-4" />
          返回
        </Button>
        <h1 className="text-lg font-heading font-semibold">
          {versionsData?.student_name ?? `学生 ${studentId}`} · {task?.title ?? ""}
        </h1>
        <div className="flex items-center gap-2 ml-auto">
          <Select
            value={versions.find((v) => v.id === effectiveSelectedId)?.version?.toString()}
            onValueChange={(ver) => {
              const found = versions.find((v) => v.version === Number(ver));
              if (found) setSelectedId(found.id);
            }}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {versions.map((v) => (
                <SelectItem key={v.id} value={String(v.version)}>
                  第 {v.version} 次提交
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          {versions.length > 1 && (
            <Button variant="outline" size="sm" onClick={enterCompare}>
              <GitCompareArrows className="mr-1 h-4 w-4" />
              版本对比
            </Button>
          )}
        </div>
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Left: document content */}
        <Card className="overflow-hidden">
          <CardHeader className="py-3">
            <CardTitle className="text-sm font-medium">学生提交内容</CardTitle>
          </CardHeader>
          <CardContent className="max-h-[70vh] overflow-y-auto">
            <ContentRenderer data={contentData} loading={contentLoading} />
          </CardContent>
        </Card>

        {/* Right: AI grading result */}
        <Card className="overflow-hidden">
          <CardHeader className="py-3">
            <CardTitle className="text-sm font-medium">批改结果</CardTitle>
          </CardHeader>
          <CardContent className="max-h-[70vh] overflow-y-auto">
            {currentVersion ? (
              <GradingPanel submission={currentVersion} />
            ) : (
              <Skeleton className="h-48 w-full" />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Footer: submission time */}
      {currentVersion && (
        <p className="text-xs text-muted-foreground">
          提交时间：{formatTime(currentVersion.submitted_at)}
        </p>
      )}
    </div>
  );
}
