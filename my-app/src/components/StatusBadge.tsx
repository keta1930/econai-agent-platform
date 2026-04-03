import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type Status = "pending" | "grading" | "completed" | "failed" | "manual_review" | "not_submitted";

const statusConfig: Record<Status, { label: string; className: string }> = {
  not_submitted: { label: "未提交", className: "bg-secondary text-muted-foreground hover:bg-secondary" },
  pending: { label: "待批改", className: "bg-secondary text-muted-foreground hover:bg-secondary" },
  grading: { label: "批改中", className: "bg-warning/10 text-warning hover:bg-warning/10" },
  completed: { label: "已完成", className: "bg-success/10 text-success hover:bg-success/10" },
  failed: { label: "批改失败", className: "bg-destructive/10 text-destructive hover:bg-destructive/10" },
  manual_review: { label: "待人工审核", className: "bg-info/10 text-info hover:bg-info/10" },
};

interface StatusBadgeProps {
  status: string;
}

export function StatusBadge({ status }: StatusBadgeProps) {
  const config = statusConfig[status as Status] ?? statusConfig.not_submitted;
  return (
    <Badge variant="secondary" className={cn("font-normal", config.className)}>
      {config.label}
    </Badge>
  );
}
