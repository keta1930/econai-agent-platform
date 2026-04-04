import { Checkbox as CheckboxPrimitive } from "@base-ui/react/checkbox";
import { cn } from "@/lib/utils";
import { Check } from "lucide-react";

interface CheckboxProps {
  checked?: boolean;
  onCheckedChange?: (checked: boolean) => void;
  disabled?: boolean;
  className?: string;
}

function Checkbox({ checked, onCheckedChange, disabled, className }: CheckboxProps) {
  return (
    <CheckboxPrimitive.Root
      checked={checked}
      onCheckedChange={onCheckedChange}
      disabled={disabled}
      className={cn(
        // 明确尺寸 + 白底 + 深边框 — 在任何背景上都清晰可见
        "inline-flex items-center justify-center",
        "h-4 w-4 min-h-4 min-w-4 shrink-0",
        "rounded border border-[var(--ink-light)] bg-white",
        "transition-colors duration-150 cursor-pointer",
        // focus
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[var(--cyan-mid)]/20",
        // checked: 墨蓝底 + 金色 check
        "data-[checked]:bg-[var(--ink-deep)] data-[checked]:border-[var(--ink-deep)]",
        // disabled
        "disabled:cursor-not-allowed disabled:opacity-50",
        className,
      )}
    >
      <CheckboxPrimitive.Indicator className="flex items-center justify-center text-[var(--gold)]">
        <Check className="h-3 w-3" strokeWidth={3} />
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  );
}

export { Checkbox };
