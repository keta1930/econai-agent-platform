import type { ReactNode } from "react";
import { InboxIcon } from "lucide-react";

interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center animate-fade-in-up">
      <div className="mb-4 rounded-full bg-muted p-4 text-muted-foreground">
        {icon ?? <InboxIcon className="h-12 w-12" />}
      </div>
      <h3 className="font-heading text-lg font-medium text-foreground">{title}</h3>
      <p className="mt-1 text-sm text-muted-foreground">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
