import { useState } from "react";
import { cn } from "@/lib/utils";
import { HelpCircle } from "lucide-react";

interface AskUserCardProps {
  question: string;
  options?: string[];
  onAnswer: (answer: string) => void;
  disabled: boolean;
}

export function AskUserCard({ question, options, onAnswer, disabled }: AskUserCardProps) {
  const [selected, setSelected] = useState<string | null>(null);

  function handleSelect(option: string) {
    if (disabled) return;
    setSelected(option);
    onAnswer(option);
  }

  return (
    <div className="rounded-lg border border-[var(--cyan-mid)]/20 bg-[var(--cyan-mid)]/[0.03] p-3 my-1">
      <div className="flex items-start gap-2 mb-2.5">
        <HelpCircle className="h-4 w-4 text-[var(--cyan-mid)] mt-0.5 shrink-0" />
        <p className="text-sm text-foreground">{question}</p>
      </div>

      {options && options.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2">
          {options.map((option) => {
            const isSelected = selected === option;
            return (
              <button
                key={option}
                type="button"
                disabled={disabled}
                onClick={() => handleSelect(option)}
                className={cn(
                  "px-3 py-1.5 text-sm rounded-md border transition-colors",
                  "focus-visible:border-[var(--cyan-mid)] focus-visible:ring-2 focus-visible:ring-[var(--cyan-mid)]/10",
                  isSelected
                    ? "border-[var(--cyan-mid)] bg-[var(--cyan-mid)]/10 text-[var(--cyan-deep)]"
                    : "border-[var(--paper-border)] bg-white text-foreground hover:border-[var(--cyan-light)] hover:bg-[var(--paper-warm)]",
                  disabled && !isSelected && "opacity-50 cursor-not-allowed",
                )}
              >
                {option}
              </button>
            );
          })}
        </div>
      )}

      {!disabled && (
        <p className="text-[11px] text-[var(--muted-foreground)]">
          或在输入框中输入其他内容
        </p>
      )}
    </div>
  );
}
