import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { MarkdownContent } from "@/components/ui/markdown-content";
import { scoreColor } from "@/lib/format";
import { CheckCircle2, Sparkles } from "lucide-react";
import type { GradingFeedback as GradingFeedbackType } from "@/types/submission";

interface GradingFeedbackProps {
  feedback: GradingFeedbackType;
  score: number;
  gradedAt: string | null;
  version?: number;
}

function progressColor(score: number, maxScore: number): string {
  const pct = maxScore > 0 ? (score / maxScore) * 100 : 0;
  if (pct >= 80) return "var(--success)";
  if (pct >= 60) return "var(--warning)";
  return "var(--destructive)";
}

export function GradingFeedback({ feedback, score, gradedAt, version }: GradingFeedbackProps) {
  return (
    <Card className="animate-fade-in-up">
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-lg font-heading">
          <CheckCircle2 className="h-5 w-5 text-success" />
          批改结果
          {version != null && (
            <span className="text-sm font-normal text-muted-foreground">
              (第 {version} 次提交)
            </span>
          )}
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-0">
        {/* Score */}
        <div className="flex items-baseline gap-2">
          <span className={`text-4xl font-bold ${scoreColor(score)}`}>{score}</span>
          <span className="text-sm text-muted-foreground">分</span>
        </div>
        {gradedAt && (
          <p className="mt-1 text-xs text-muted-foreground">
            批改完成于 {new Date(gradedAt).toLocaleString("zh-CN")}
          </p>
        )}

        {/* Dimensions */}
        {feedback.dimensions.length > 0 && (
          <div className="mt-5 border-t border-[var(--paper-border)] pt-5">
            <h4 className="mb-3 text-sm font-medium text-muted-foreground">评分详情</h4>
            <div className="space-y-4">
              {feedback.dimensions.map((dim) => (
                <div key={dim.name}>
                  <div className="mb-1.5 flex items-center justify-between text-sm">
                    <span className="font-medium">{dim.name}</span>
                    <span className="text-muted-foreground">
                      {dim.score}/{dim.max_score}
                    </span>
                  </div>
                  <Progress
                    value={dim.max_score > 0 ? (dim.score / dim.max_score) * 100 : 0}
                    style={
                      { "--progress-foreground": progressColor(dim.score, dim.max_score) } as React.CSSProperties
                    }
                  />
                  {dim.comment && (
                    <p className="mt-1 text-sm text-muted-foreground">{dim.comment}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Overall comment */}
        {feedback.overall_comment && (
          <div className="mt-5 border-t border-[var(--paper-border)] pt-5">
            <h4 className="mb-3 text-sm font-medium text-muted-foreground">总体评价</h4>
            <MarkdownContent content={feedback.overall_comment} />
          </div>
        )}

        {/* Improvements */}
        {feedback.improvements.length > 0 && (
          <div className="mt-5 border-t border-[var(--paper-border)] pt-5">
            <h4 className="mb-3 text-sm font-medium text-muted-foreground">改进建议</h4>
            <ol className="list-decimal space-y-1.5 pl-5 text-sm">
              {feedback.improvements.map((item, i) => (
                <li key={i}>{item}</li>
              ))}
            </ol>
          </div>
        )}

        {/* Highlights */}
        {feedback.highlights.length > 0 && (
          <div className="mt-5 border-t border-[var(--paper-border)] pt-5">
            <h4 className="mb-3 text-sm font-medium text-muted-foreground">亮点</h4>
            <ul className="space-y-2">
              {feedback.highlights.map((item, i) => (
                <li key={i} className="flex items-start gap-2 text-sm">
                  <Sparkles className="mt-0.5 h-4 w-4 shrink-0 text-[var(--gold)]" />
                  <span>{item}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </CardContent>
    </Card>
  );
}
