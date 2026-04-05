import * as React from "react"

import { cn } from "@/lib/utils"

interface ProgressProps extends React.ComponentProps<"div"> {
  value?: number;
}

function Progress({ className, value = 0, ...props }: ProgressProps) {
  return (
    <div
      data-slot="progress"
      className={cn(
        "relative h-2 w-full overflow-hidden rounded-full bg-[var(--paper-deep)]",
        className
      )}
      {...props}
    >
      <div
        data-slot="progress-indicator"
        className="h-full rounded-full transition-all duration-300 ease-out"
        style={{
          width: `${Math.max(0, Math.min(100, value))}%`,
          backgroundColor: "var(--progress-foreground, var(--cyan-mid))",
        }}
      />
    </div>
  )
}

export { Progress }
