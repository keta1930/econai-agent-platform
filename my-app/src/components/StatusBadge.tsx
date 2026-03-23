import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type Status = "pending" | "grading" | "completed" | "failed" | "not_submitted";

const statusConfig: Record<Status, { label: string; className: string }> = {
  not_submitted: { label: "未提交", className: "bg-gray-100 text-gray-600 hover:bg-gray-100" },
  pending: { label: "待批改", className: "bg-gray-100 text-gray-600 hover:bg-gray-100" },
  grading: { label: "批改中", className: "bg-amber-50 text-amber-700 hover:bg-amber-50" },
  completed: { label: "已完成", className: "bg-green-50 text-green-700 hover:bg-green-50" },
  failed: { label: "批改失败", className: "bg-red-50 text-red-700 hover:bg-red-50" },
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
